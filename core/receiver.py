import asyncio
import threading
import queue
import socket
import numpy as np

from gnuradio import gr, blocks, filter, analog, audio
from gnuradio.filter import firdes
import osmosdr

# Assuming AFSKDemodulator and AX25FromAFSK are available
try:
    from afsk.demod import AFSKDemodulator
    from ax25.from_afsk import AX25FromAFSK
except ImportError as e:
    AFSKDemodulator = None
    AX25FromAFSK = None
    print("Warning: AFSKDemodulator or AX25FromAFSK not available.")

class QueueSink(gr.sync_block):
    """
    A GNU Radio block that puts samples into an asyncio queue using run_coroutine_threadsafe().
    It detects audio presence by a threshold and only forwards samples if energy is above it.
    """
    def __init__(self, samples_q, threshold=500):
        gr.sync_block.__init__(
            self,
            name='QueueSink',
            in_sig=[np.int16],
            out_sig=None
        )
        self.samples_q = samples_q
        # We assume the event loop is the one set by start_receiver in the same thread
        # If you are running in a different thread, ensure self.loop references the correct loop.
        # If needed, store the loop reference explicitly when creating the block.
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            # In case no loop is set for this thread, you must ensure a loop is running.
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        self.set_output_multiple(480)
        self.threshold = threshold

    def work(self, input_items, output_items):
        in0 = input_items[0]
        # Compute energy and conditionally enqueue samples
        energy = np.mean(np.abs(in0))
        if energy > self.threshold:
            samples = in0.copy()
            idx = len(samples)
            # Schedule the coroutine to put samples into the queue
            # without awaiting directly here
            future = asyncio.run_coroutine_threadsafe(self.samples_q.put((samples, idx)), self.loop)
            # future.result() if you need to catch exceptions, but generally not required here.

        return len(in0)

class AFSKReceiver(gr.top_block):
    def __init__(self, samples_q, device_index=0, frequency=50.01e6):
        super(AFSKReceiver, self).__init__()
        ##################################################
        # Variables
        #################
        #################################
        self.freq = frequency           # Frequency in Hz
        self.vol = 8                  # Volume multiplier
        self.sql = 52                 # Squelch threshold
        self.samp_rate = 48e3 * 100   # Sample rate (4.8e6 Hz)
        self.nbfm_bandwidth = 12e3    # Narrowband FM bandwidth
        self.ifg = 32                 # IF Gain
        self.center_freq = self.freq + 500e3  # Center frequency (28.62e6 Hz)
        self.bbg = 32                 # BB Gain

        ##################################################
        # Blocks
        ##################################################

        # SDR Source Block
        self.osmosdr_source = osmosdr.source(
            args=f"numchan={1} hackrf={device_index}"
        )
        self.osmosdr_source.set_time_unknown_pps(osmosdr.time_spec_t())
        self.osmosdr_source.set_sample_rate(self.samp_rate)
        self.osmosdr_source.set_center_freq(self.center_freq, 0)
        self.osmosdr_source.set_freq_corr(0, 0)
        self.osmosdr_source.set_dc_offset_mode(0, 0)
        self.osmosdr_source.set_iq_balance_mode(0, 0)
        self.osmosdr_source.set_gain_mode(False, 0)
        self.osmosdr_source.set_gain(0, 0)
        self.osmosdr_source.set_if_gain(self.ifg, 0)
        self.osmosdr_source.set_bb_gain(self.bbg, 0)
        self.osmosdr_source.set_antenna('', 0)
        self.osmosdr_source.set_bandwidth(0, 0)

        # Low Pass Filter
        self.low_pass_filter = filter.fir_filter_ccf(
            int(self.samp_rate / self.nbfm_bandwidth),
            firdes.low_pass(
                1,
                self.samp_rate,
                self.nbfm_bandwidth,
                1e3,
                0,
                6.76
            )
        )

        # Rational Resampler
        self.rational_resampler = filter.rational_resampler_ccc(
            interpolation=4,
            decimation=1,
            taps=[],
            fractional_bw=0
        )

        # Narrowband FM Receiver
        self.nbfm_rx = analog.nbfm_rx(
            audio_rate=48000,
            quad_rate=48000,
            tau=75e-6,
            max_dev=5e3,
        )

        # Power Squelch
        self.pwr_squelch = analog.pwr_squelch_cc(self.sql, 75e-6, 10, True)

        # Automatic Gain Control
        self.agc = analog.agc3_cc(1e-3, 100e-6, 1.0, 1, 1, 65536)

        # Signal Source for Multiplication
        self.sig_source = analog.sig_source_c(
            self.samp_rate,
            analog.GR_COS_WAVE,
            (self.center_freq - self.freq),
            1,
            0,
            0
        )

        # Multiply Blocks
        self.multiply = blocks.multiply_vcc(1)
        self.multiply_const = blocks.multiply_const_ff(0.05)
        self.multiply_vol = blocks.multiply_const_ff(self.vol)

        # Moving Average for Squelch
        self.moving_average = blocks.moving_average_cc(1000, 30, 1000, 1)

        # Audio Sink
        self.audio_sink = audio.sink(48000, '', True)

        self.blocks_float_to_short_0 = blocks.float_to_short(1, 32767)

        self.queue_sink_0 = QueueSink(samples_q)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.agc, 0), (self.low_pass_filter, 0))
        self.connect((self.nbfm_rx, 0), (self.multiply_const, 0))
        self.connect((self.pwr_squelch, 0), (self.agc, 0))
        self.connect((self.sig_source, 0), (self.multiply, 1))
        self.connect((self.moving_average, 0), (self.pwr_squelch, 0))
        self.connect((self.multiply_const, 0), (self.multiply_vol, 0))
        self.connect((self.multiply_vol, 0), (self.audio_sink, 0))
        self.connect((self.multiply, 0), (self.moving_average, 0))
        self.connect((self.low_pass_filter, 0), (self.rational_resampler, 0))
        self.connect((self.osmosdr_source, 0), (self.multiply, 0))
        self.connect((self.rational_resampler, 0), (self.nbfm_rx, 0))
        self.connect((self.blocks_float_to_short_0, 0), (self.queue_sink_0, 0))
        self.connect((self.multiply_vol, 0), (self.blocks_float_to_short_0, 0))

    def stop_and_wait(self):
        """Gracefully stop the flowgraph."""
        try:
            self.disconnect((self.agc, 0), (self.low_pass_filter, 0))
            self.disconnect((self.low_pass_filter, 0), (self.rational_resampler, 0))
            self.disconnect((self.rational_resampler, 0), (self.nbfm_rx, 0))
            self.disconnect((self.nbfm_rx, 0), (self.multiply_const, 0))
            self.disconnect((self.multiply_const, 0), (self.multiply_vol, 0))
            self.disconnect((self.multiply_vol, 0), (self.audio_sink, 0))
            self.disconnect((self.multiply_vol, 0), (self.blocks_float_to_short_0, 0))
            self.disconnect((self.blocks_float_to_short_0, 0), (self.queue_sink_0, 0))
            self.disconnect((self.pwr_squelch, 0), (self.agc, 0))
            # IMPORTANT: Use exact ports for sig_source and multiply:
            self.disconnect((self.sig_source, 0), (self.multiply, 1))
            self.disconnect((self.multiply, 0), (self.moving_average, 0))
            self.disconnect((self.moving_average, 0), (self.pwr_squelch, 0))
            self.disconnect((self.osmosdr_source, 0), (self.multiply, 0))
        except Exception as e:
            print(f"Error during disconnect: {e}")
        self.stop()
        try:
            self.wait()  # Ensure the flowgraph completes any remaining processing
            print("Receiver Flowgraph stopped and resources released.")
        except Exception as e:
            print(f"Error while waiting for flowgraph stop: {e}")


async def consume_ax25(ax25_q, received_message_queue):
    print("allo")
    try:
        while True:
            
            ax25_msg = await ax25_q.get()
            ax25_q.task_done()
            if ax25_msg is None:
                break
            print("AX.25 message received:", ax25_msg)  # Debugging message
            received_message_queue.put(str(ax25_msg))
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        pass
    except Exception as err:
        print(f"Error in consume_ax25: {err}")

async def demod_core(samples_q, bits_q, ax25_q):
    if AFSKDemodulator is None or AX25FromAFSK is None:
        print("Demodulator not available.")
        return
    try:
        async with AFSKDemodulator(sampling_rate=48000, samples_in_q=samples_q, bits_out_q=bits_q, verbose=False) as afsk_demod:
            async with AX25FromAFSK(bits_in_q=bits_q, ax25_q=ax25_q, verbose=False) as bits2ax25:
                while True:
                    await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    except Exception as err:
        print(f"Error in demod_core: {err}")

def start_receiver(stop_event, received_message_queue, device_index=0, frequency=50.01e6):
    def run_receiver():
        # Create a new event loop for the receiver thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create async queues for samples, bits, and AX.25 frames
        samples_q = asyncio.Queue()
        bits_q = asyncio.Queue()
        ax25_q = asyncio.Queue()

        # Start the AFSK Receiver
        tb = AFSKReceiver(samples_q, device_index=device_index, frequency=frequency)
        tb.start()

        # Create tasks for demodulation pipelines
        tasks = [
            loop.create_task(consume_ax25(ax25_q, received_message_queue)),
            loop.create_task(demod_core(samples_q, bits_q, ax25_q))
        ]

        try:
            print("Running the event loop...")
            loop.run_forever()
        except asyncio.CancelledError:
            print("Event loop cancelled.")
        finally:
            # Cancel tasks and stop the flowgraph gracefully
            for t in tasks:
                t.cancel()
            tb.stop_and_wait()  # Ensure the flowgraph is properly stopped
            tb.wait()  # Ensure we wait for the flowgraph to fully stop
            print("Receiver flowgraph stopped and cleaned up.")

            # Clean up the event loop
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            loop.stop()
            loop.close()
            print("Receiver thread stopped.")

    # Start the receiver thread
    receiver_thread = threading.Thread(target=run_receiver, daemon=True)
    receiver_thread.start()
    return receiver_thread

