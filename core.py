# core.py

import threading
import asyncio
import socket
import queue
import wave
import struct
import subprocess
import numpy as np
import re
import sys

# Try to import external dependencies, handle ImportError gracefully
try:
    from gnuradio import gr, blocks, filter, analog, audio
    from gnuradio.filter import firdes
    import osmosdr
except ImportError as e:
    print(f"Warning: Could not import GNU Radio modules. Some functionality may be limited. {e}")
    gr = None  # Set to None to prevent errors if used
    blocks = None
    filter = None
    analog = None
    audio = None
    firdes = None
    osmosdr = None

try:
    from afsk.mod import AFSKModulator
    from afsk.demod import AFSKDemodulator
    from afsk.func import afsk_detector
    from ax25.ax25 import AX25
    from ax25.from_afsk import AX25FromAFSK
except ImportError as e:
    print(f"Warning: Could not import AFSK or AX.25 modules. Some functionality may be limited. {e}")
    AFSKModulator = None
    AFSKDemodulator = None
    afsk_detector = None
    AX25 = None
    AX25FromAFSK = None

# Reset HackRF
def reset_hackrf():
    """Reset the HackRF device."""
    subprocess.run(["hackrf_transfer", "-r", "/dev/null"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["hackrf_transfer", "-t", "/dev/null"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("HackRF reset completed.")

# Add silence to WAV
def add_silence(input_wav, output_wav, silence_duration_before, silence_duration_after):
    """Add silence before and after a WAV file."""
    with wave.open(input_wav, 'rb') as wav_in:
        params = wav_in.getparams()
        sample_rate = wav_in.getframerate()
        num_channels = wav_in.getnchannels()
        sampwidth = wav_in.getsampwidth()

        audio_frames = wav_in.readframes(wav_in.getnframes())

    num_silence_frames_before = int(silence_duration_before * sample_rate)
    num_silence_frames_after = int(silence_duration_after * sample_rate)

    silence_before = (b'\x00' * sampwidth * num_channels) * num_silence_frames_before
    silence_after = (b'\x00' * sampwidth * num_channels) * num_silence_frames_after

    new_frames = silence_before + audio_frames + silence_after

    with wave.open(output_wav, 'wb') as wav_out:
        wav_out.setparams(params)
        wav_out.writeframes(new_frames)

def list_hackrf_devices():
    """
    List all connected HackRF devices using hackrf_info.
    Returns a list of dictionaries with 'serial' and 'index'.
    """
    try:
        # Run hackrf_info command
        result = subprocess.run(['hackrf_info', '-s'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"hackrf_info error: {result.stderr}")
            return []
        
        devices = []
        # Split output into lines
        lines = result.stdout.splitlines()
        current_device = None
        
        # Parse each line to extract relevant details
        for line in lines:
            # Match for "Index: <number>"
            index_match = re.match(r'Index:\s+(\d+)', line)
            if index_match:
                # Start a new device entry
                current_device = {'index': int(index_match.group(1)), 'serial': None}
                devices.append(current_device)
            
            # Match for "Serial number: <serial>"
            serial_match = re.match(r'Serial number:\s+([0-9a-fA-F]+)', line)
            if serial_match and current_device:
                # Add serial to the current device
                current_device['serial'] = serial_match.group(1)
        
        print(f"Detected HackRF devices: {devices}")
        return devices
    
    except FileNotFoundError:
        print("hackrf_info not found. Ensure HackRF tools are installed.")
        return []
    except Exception as e:
        print(f"Error listing HackRF devices: {e}")
        return []

# GNU Radio class
if gr is not None:
    class ResampleAndSend(gr.top_block):
        def __init__(self, input_file, output_rate, device_index=0):
            gr.top_block.__init__(self, "Resample and Send")

            self.file_source = blocks.wavfile_source(input_file, repeat=False)
            self.resampler = filter.rational_resampler_fff(interpolation=int(output_rate), decimation=22050)
            self.amplitude_scaling = blocks.multiply_const_ff(0.05)
            self.float_to_complex = blocks.float_to_complex()
            self.sink = None
            self.output_rate = output_rate
            self.device_index = device_index
            self.blocks_add_xx_0 = blocks.add_vff(1)
            self.analog_noise_source_x_0 = analog.noise_source_f(analog.GR_GAUSSIAN, 1, 0)
            self.high_pass_filter_0 = filter.interp_fir_filter_fff(
                1,
                firdes.high_pass(
                    1,
                    22050,
                    8e3,
                    1e3,
                    1,
                    6.76))

            #self.connect((self.analog_noise_source_x_0, 0), (self.high_pass_filter_0, 0))
            #self.connect((self.blocks_add_xx_0, 0), self.resampler)
            self.connect(self.resampler, self.amplitude_scaling)
            self.connect(self.amplitude_scaling, self.float_to_complex)
            #self.connect(self.file_source, (self.blocks_add_xx_0, 0))
            self.connect(self.file_source, self.resampler)
            #self.connect((self.high_pass_filter_0, 0), (self.blocks_add_xx_0, 1))

        def initialize_hackrf(self, gain, if_gain):
            """Initialize HackRF sink."""
            try:
                print(f"Initializing HackRF device {self.device_index}...")
                self.sink = osmosdr.sink(args=f"hackrf={self.device_index}")
                self.sink.set_sample_rate(self.output_rate)
                # Center frequency will be set externally after initialization
                self.sink.set_center_freq(28.12e6, 0)  # Default; can be changed later
                self.sink.set_gain(gain, 0)
                self.sink.set_if_gain(if_gain, 0)
                self.sink.set_bb_gain(20, 0)
                self.sink.set_antenna("TX/RX", 0)
                print("HackRF initialized successfully.")
                self.connect(self.float_to_complex, self.sink)
                return True
            except RuntimeError as e:
                print(f"Error initializing HackRF: {e}")
                return False

        def set_center_freq(self, freq_hz):
            """Set the center frequency of the HackRF."""
            if self.sink:
                self.sink.set_center_freq(freq_hz, 0)
                print(f"HackRF center frequency set to {freq_hz / 1e6} MHz.")

        def stop_and_wait(self):
            """Gracefully stop the flowgraph and release resources."""
            try:
                # Disconnect blocks in the reverse order of connections
                if self.sink:
                    print("Disconnecting HackRF sink...")
                    self.disconnect(self.float_to_complex, self.sink)
                    self.sink = None  # Explicitly release the sink resource

                print("Stopping the flowgraph...")
                self.stop()
                print("Waiting for the flowgraph to terminate...")
                self.wait()
                print("Flowgraph stopped and resources released.")
            except Exception as e:
                print(f"Error during stop and wait: {e}")

else:
    # Provide a dummy class if gr is not available
    class ResampleAndSend:
        def __init__(self, input_file, output_rate, device_index=0):
            print("Warning: GNU Radio is not available. ResampleAndSend functionality is disabled.")

        def initialize_hackrf(self, gain, if_gain):
            print("Warning: Cannot initialize HackRF without GNU Radio.")
            return False

        def set_center_freq(self, freq_hz):
            pass

        def stop_and_wait(self):
            pass

# Generate APRS WAV
async def generate_aprs_wav(aprs_message, output_wav, flags_before=10, flags_after=4):
    """Generate a WAV file from an APRS message."""
    if AFSKModulator is None or AX25 is None:
        print("Warning: AFSKModulator or AX25 is not available. Cannot generate APRS WAV.")
        return

    print(f"Generating APRS WAV for message: {aprs_message}")
    rate = 22050
    try:
        async with AFSKModulator(sampling_rate=rate, verbose=False) as afsk_mod:
            ax25 = AX25(aprs=aprs_message.encode())
            afsk, stop_bit = ax25.to_afsk()
            await afsk_mod.send_flags(flags_before)
            await afsk_mod.to_samples(afsk=afsk, stop_bit=stop_bit)
            await afsk_mod.send_flags(flags_after)
            arr, s = await afsk_mod.flush()

            with wave.open(output_wav, 'wb') as wav_out:
                wav_out.setnchannels(1)
                wav_out.setsampwidth(2)
                wav_out.setframerate(rate)
                for i in range(s):
                    samp = struct.pack('<h', arr[i])
                    wav_out.writeframesraw(samp)
        print(f"WAV file successfully generated: {output_wav}")
    except Exception as e:
        print(f"Error generating APRS WAV: {e}")

# UDP Listener
def udp_listener(host, port, message_queue, stop_event):
    """Listen for APRS messages over UDP and add them to the message queue."""
    print(f"Starting UDP listener on {host}:{port}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((host, port))
            sock.settimeout(0.5)
            while not stop_event.is_set():
                try:
                    data, addr = sock.recvfrom(1024)
                    aprs_message = data.decode().strip()
                    print(f"Received UDP message from {addr}: {aprs_message}")
                    message_queue.put(aprs_message)
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error in UDP listener: {e}")
    except Exception as e:
        print(f"UDP listener error: {e}")

# Frequency Wrapper
class Frequency:
    """A thread-safe wrapper for the frequency variable."""
    def __init__(self, initial_value):
        self._value = initial_value
        self._lock = threading.Lock()

    def get(self):
        with self._lock:
            return self._value

    def set(self, value):
        with self._lock:
            self._value = value

class ThreadSafeVariable:
    """A thread-safe wrapper for any variable."""
    def __init__(self, initial_value):
        self._value = initial_value
        self._lock = threading.Lock()
    
    def get(self):
        with self._lock:
            return self._value
    
    def set(self, value):
        with self._lock:
            self._value = value

# Receiver Classes and Functions
if gr is not None and osmosdr is not None:
    import logging
    import asyncio

    class QueueSink(gr.sync_block):
        """
        A custom GNU Radio block that puts samples into an asyncio queue.
        Includes signal detection to process samples only when audio is present.
        """
        def __init__(self, samples_q, threshold=500):
            gr.sync_block.__init__(
                self,
                name='QueueSink',
                in_sig=[np.int16],
                out_sig=None
            )
            self.samples_q = samples_q
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
            self.set_output_multiple(480)  # Process smaller chunks to reduce latency
            self.threshold = threshold  # Threshold for detecting audio signal

        def work(self, input_items, output_items):
            in0 = input_items[0]
            # Calculate the mean absolute value of the samples
            energy = np.mean(np.abs(in0))
            if energy > self.threshold:
                # Copy the samples to avoid issues with memory management
                samples = in0.copy()
                idx = len(samples)
                asyncio.run_coroutine_threadsafe(
                    self.samples_q.put((samples, idx)),
                    self.loop
                )
            return len(in0)

    class AFSKReceiver(gr.top_block):
        def __init__(self, samples_q, device_index=0):
            super(AFSKReceiver, self).__init__()
            ##################################################
            # Variables
            ##################################################
            self.freq = 28.12e6           # Frequency in Hz
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
                self.disconnect(self.agc, self.low_pass_filter)
                self.disconnect(self.low_pass_filter, self.rational_resampler)
                self.disconnect(self.rational_resampler, self.nbfm_rx)
                self.disconnect(self.nbfm_rx, self.multiply_const)
                self.disconnect(self.multiply_const, self.multiply_vol)
                self.disconnect(self.multiply_vol, self.audio_sink)
                self.disconnect(self.multiply_vol, self.blocks_float_to_short_0)
                self.disconnect(self.blocks_float_to_short_0, self.queue_sink_0)
                self.disconnect(self.pwr_squelch, self.agc)
                self.disconnect(self.sig_source, self.multiply)
                self.disconnect(self.multiply, self.moving_average)
                self.disconnect(self.moving_average, self.pwr_squelch)
                self.disconnect(self.osmosdr_source, self.multiply)
            except Exception as e:
                print(f"Error during disconnect: {e}")
            self.stop()
            self.wait()

    async def consume_ax25(ax25_q, received_message_queue):
        try:
            while True:
                ax25 = await ax25_q.get()
                ax25_q.task_done()
                if ax25 is None:
                    break
                received_message_queue.put(str(ax25))
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            pass
        except Exception as err:
            print(f"Error in consume_ax25: {err}")

    async def demod_core(samples_q, bits_q, ax25_q):
        try:
            if AFSKDemodulator is None or AX25FromAFSK is None:
                print("Warning: AFSKDemodulator or AX25FromAFSK is not available.")
                return
            async with AFSKDemodulator(
                sampling_rate=48000,
                samples_in_q=samples_q,
                bits_out_q=bits_q,
                verbose=False,
            ) as afsk_demod:
                async with AX25FromAFSK(
                    bits_in_q=bits_q,
                    ax25_q=ax25_q,
                    verbose=False
                ) as bits2ax25:
                    # Keep the coroutine alive indefinitely
                    while True:
                        await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        except Exception as err:
            print(f"Error in demod_core: {err}")

    def start_receiver(stop_event, received_message_queue, device_index=0):
        """Start the AFSK Receiver in a separate thread."""
        if gr is None or osmosdr is None:
            print("GNU Radio or osmosdr is not available. Cannot start receiver.")
            return None

        import asyncio

        def run_receiver():
            # This function will run in a separate thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            samples_q = asyncio.Queue()
            bits_q = asyncio.Queue()
            ax25_q = asyncio.Queue()

            print(f"Starting receiver")

            # Initialize the AFSK Receiver with the provided frequency and gains
            tb = AFSKReceiver(samples_q=samples_q, device_index=device_index)
            tb.start()

            # Create asyncio tasks
            tasks = []
            tasks.append(loop.create_task(consume_ax25(ax25_q=ax25_q, received_message_queue=received_message_queue)))
            tasks.append(loop.create_task(demod_core(samples_q, bits_q, ax25_q)))

            try:
                while not stop_event.is_set():
                    loop.run_until_complete(asyncio.sleep(1))
            except Exception as e:
                print(f"Receiver encountered an exception: {e}")
            finally:
                for task in tasks:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                tb.stop_and_wait()
                loop.stop()
                loop.close()
                print("Receiver thread has been stopped.") 

        # Start the receiver in a separate thread
        receiver_thread = threading.Thread(target=run_receiver, daemon=True)
        receiver_thread.start()
        print("Receiver thread started.")
        return receiver_thread

# Expose start_receiver function and other necessary components
__all__ = [
    'ResampleAndSend',
    'generate_aprs_wav',
    'udp_listener',
    'Frequency',
    'ThreadSafeVariable',
    'start_receiver',
    'list_hackrf_devices'
]