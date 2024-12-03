#!/usr/bin/env python

import sys
import asyncio
import struct
import logging
from array import array
import argparse
import time
import functools
import numpy as np

from gnuradio import audio
from gnuradio import blocks
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import analog
from gnuradio import gr
import osmosdr

# Define the sentinel at the top of your script
SENTINEL = object()

# Set up logging with timestamps
logging.basicConfig(
    level=logging.INFO,  # Adjust as needed (DEBUG, INFO, WARNING, ERROR)
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Switch to SelectorEventLoop for better compatibility on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Micropython/Python compatibility
from lib.compat import Queue
from lib.compat import print_exc

from afsk.demod import AFSKDemodulator
from ax25.from_afsk import AX25FromAFSK
from afsk.func import afsk_detector

import lib.defs as defs

AX25_FLAG      = 0x7e
AX25_ADDR_LEN  = 7

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
        self.loop = asyncio.get_event_loop()
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

            # Print statement to indicate samples are being queued
            #print(f"Queueing samples with energy {energy:.2f}")

            # Since GNU Radio runs in a separate thread, use thread-safe method
            asyncio.run_coroutine_threadsafe(
                self.samples_q.put((samples, idx)),
                self.loop
            )
        #else:
            # Print statement to indicate samples are being ignored
            #print(f"Ignoring silent samples with energy {energy:.2f}")

        return len(in0)




class AFSKReceiver(gr.top_block):
    def __init__(self, samples_q, center_freq=143.890e6, offset_freq=500e3,
                 sample_rate=960000, audio_rate=48000,
                 rf_gain=0, if_gain=40, bb_gain=14,
                 demod_gain=5.0, squelch_threshold=-40):
        super(AFSKReceiver, self).__init__()

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = sample_rate
        self.audio_rate = audio_rate

        ##################################################
        # Blocks
        ##################################################
        
        # Source SDR
        self.osmosdr_source_0 = osmosdr.source(
            args="numchan=" + str(1) + " " + 'hackrf=0'
        )
        self.osmosdr_source_0.set_time_unknown_pps(osmosdr.time_spec_t())
        self.osmosdr_source_0.set_sample_rate(samp_rate)
        self.osmosdr_source_0.set_center_freq(center_freq, 0)
        self.osmosdr_source_0.set_freq_corr(0, 0)
        self.osmosdr_source_0.set_dc_offset_mode(0, 0)
        self.osmosdr_source_0.set_iq_balance_mode(0, 0)
        self.osmosdr_source_0.set_gain_mode(False, 0)
        self.osmosdr_source_0.set_gain(rf_gain, 0)
        self.osmosdr_source_0.set_if_gain(if_gain, 0)
        self.osmosdr_source_0.set_bb_gain(bb_gain, 0)
        self.osmosdr_source_0.set_antenna('', 0)
        self.osmosdr_source_0.set_bandwidth(0, 0)

        # Décalage fréquentiel
        self.freq_xlating_fir_filter_xxx_0 = filter.freq_xlating_fir_filter_ccc(
            1,
            firdes.low_pass(1.0, samp_rate, 10e3, 5e3, 6),
            offset_freq,
            samp_rate
        )

        # Filtrage audio
        self.fir_filter_xxx_0 = filter.fir_filter_fff(
            int(samp_rate / audio_rate),
            firdes.low_pass(1.0, samp_rate, 3.5e3, 500, 6)
        )
        self.fir_filter_xxx_0.declare_sample_delay(0)

        # Démodulation et amplification
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_ff(demod_gain)
        self.blocks_float_to_short_0 = blocks.float_to_short(1, 32767)

        # Sortie audio
        self.audio_sink_1 = audio.sink(int(audio_rate), '', True)

        # Squelch
        self.analog_simple_squelch_cc_0 = analog.simple_squelch_cc(squelch_threshold, 1)

        # Démodulation quadrature
        self.analog_quadrature_demod_cf_0 = analog.quadrature_demod_cf(1)

        # Utilisation d'une QueueSink pour les données
        self.queue_sink_0 = QueueSink(samples_q)

        ##################################################
        # Connexions
        ##################################################
        self.connect((self.osmosdr_source_0, 0), (self.freq_xlating_fir_filter_xxx_0, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_0, 0), (self.analog_simple_squelch_cc_0, 0))
        self.connect((self.analog_simple_squelch_cc_0, 0), (self.analog_quadrature_demod_cf_0, 0))
        self.connect((self.analog_quadrature_demod_cf_0, 0), (self.fir_filter_xxx_0, 0))
        self.connect((self.fir_filter_xxx_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.audio_sink_1, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_float_to_short_0, 0))
        self.connect((self.blocks_float_to_short_0, 0), (self.queue_sink_0, 0))

        ##################################################
        # Optimisations de latence
        ##################################################
        self.set_max_noutput_items(480)  # Correspond à 10 ms à 48 kHz

        # Réduction des tailles de buffers pour minimiser la latence
        for blk in [self.osmosdr_source_0, self.freq_xlating_fir_filter_xxx_0,
                    self.fir_filter_xxx_0, self.blocks_multiply_const_vxx_0,
                    self.blocks_float_to_short_0]:
            blk.set_max_output_buffer(480)

        print(f"AFSK Receiver is configured and running.")


async def read_samples_from_file(samples_q, file):
    try:
        logging.info(f"Reading samples from file: {file}")
        logging.debug(f"Opening file: {file}")
        arr = array('i', [0] * defs.SAMPLES_SIZE)
        idx = 0

        with open(file, 'rb') as f:
            while True:
                a = f.read(2)
                if not a:
                    break
                if len(a) < 2:
                    logging.warning(f"Incomplete sample data: {a}")
                    continue
                arr[idx] = struct.unpack('<h', a)[0]
                idx += 1
                if idx >= defs.SAMPLES_SIZE:
                    start_process = time.time()
                    if afsk_detector(arr, idx):
                        logging.debug(f"AFSK detected at index {idx}")
                        await samples_q.put((arr[:], idx))  # Use slicing to copy the array
                    end_process = time.time()
                    logging.debug(f"Processed buffer of {idx} samples in {end_process - start_process:.4f} seconds.")
                    arr = array('i', [0] * defs.SAMPLES_SIZE)
                    idx = 0
            if idx > 0:
                start_remaining = time.time()
                await samples_q.put((arr[:idx], idx))  # Use slicing to copy the array
                end_remaining = time.time()
                logging.debug(f"Remaining samples put into queue: {idx} in {end_remaining - start_remaining:.4f} seconds.")
        logging.info("Finished reading samples from file.")
    except FileNotFoundError:
        logging.error(f"File not found: {file}")
        print_exc(sys.exc_info()[1])
    except Exception as err:
        logging.error(f"Error reading samples from file: {err}")
        print_exc(err)
    except asyncio.CancelledError:
        logging.warning("Asyncio task was cancelled.")
    finally:
        await samples_q.put(SENTINEL)

async def consume_ax25(ax25_q, write_func):
    try:
        count = 1
        while True:
            ax25 = await ax25_q.get()
            ax25_q.task_done()
            if ax25 is SENTINEL:
                break
            start_consume = time.time()
            write_func(f'[{count}] {ax25}\n')
            end_consume = time.time()
            logging.debug(f"Consumed AX25 packet #{count} in {end_consume - start_consume:.4f} seconds.")
            count += 1
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        logging.warning("Asyncio task was cancelled.")
        raise
    except Exception as err:
        logging.error(f"Error in consume_ax25: {err}")
        print_exc(err)

async def demod_core(samples_q, bits_q, ax25_q, args):
    try:
        logging.info("Starting AFSK Demodulation...")
        async with AFSKDemodulator(
            sampling_rate=args.rate,
            samples_in_q=samples_q,
            bits_out_q=bits_q,
            verbose=args.verbose,
        ) as afsk_demod:
            async with AX25FromAFSK(
                bits_in_q=bits_q,
                ax25_q=ax25_q,
                verbose=args.verbose
            ) as bits2ax25:
                # Keep the coroutine alive indefinitely
                while True:
                    await asyncio.sleep(1)
    except asyncio.CancelledError:
        logging.warning("Asyncio task was cancelled.")
        raise
    except Exception as err:
        logging.error(f"Error in demod_core: {err}")
        print_exc(err)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="APRS DEMOD",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '-r', '--rate',
        type=int,
        default=48000,
        help='Sampling rate (default: 48000)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose intermediate output to stderr'
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        nargs='+',  # Accepts one or more arguments
        metavar='INPUT',
        default=['hackrf'],
        help=(
            "Input type and parameters:\n"
            "  raw <filename.raw> : 16-bit signed samples\n"
            "  hackrf : input from HackRF"
        )
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        nargs=2,
        metavar=('outtype', 'outfile'),
        default=['aprs', '-'],
        help=(
            "Output type and file:\n"
            "  aprs <outfile.aprs> : APRS strings\n"
            "  - : stdout (default)"
        )
    )
    args = parser.parse_args()
    
    # Validate input arguments based on input type
    if args.input[0] == 'hackrf':
        if len(args.input) != 1:
            parser.error("HackRF input does not require additional parameters. Usage: -i hackrf")
    elif args.input[0] == 'raw':
        if len(args.input) != 2:
            parser.error(f"'raw' input requires one parameter. Usage: -i raw <filename.raw>")
    else:
        parser.error(f"Unsupported input type: {args.input[0]}")
        
    return args

def get_output_handler(output_type, output_file):
    if output_type != 'aprs':
        logging.error(f"Unsupported output type: {output_type}")
        raise Exception(f"unsupported output type: {output_type}")

    if output_file == '-':
        # Output to stdout
        return functools.partial(sys.stdout.write), None
    else:
        # Output to specified file
        try:
            f = open(output_file, 'w')
            return f.write, f  # Return both write function and file object
        except Exception as e:
            logging.error(f"Failed to open output file {output_file}: {e}")
            raise

async def main():
    output_file_handle = None
    try:
        # Parse command-line arguments
        args = parse_arguments()
        logging.debug(f"Parsed arguments: {args}")

        logging.info(f"Starting APRS DEMOD with RATE {args.rate}")
        logging.info(f"Input type: {args.input[0]}")
        if args.input[0] == 'raw':
            logging.info(f"Input file: {args.input[1]}")
        logging.info(f"Output type: {args.output[0]}")
        logging.info(f"Output file: {args.output[1]}")

        # Initialize queues for processing
        samples_q = asyncio.Queue()
        bits_q = asyncio.Queue()
        ax25_q = asyncio.Queue()

        # Determine output handler
        write_func, file_obj = get_output_handler(args.output[0], args.output[1])
        if file_obj:
            output_file_handle = file_obj  # Keep a reference to close later

        # Create asyncio tasks
        tasks = []
        tasks.append(asyncio.create_task(consume_ax25(ax25_q=ax25_q, write_func=write_func)))
        tasks.append(asyncio.create_task(demod_core(samples_q, bits_q, ax25_q, args)))

        # Determine input source and create corresponding task
        if args.input[0] == 'hackrf':
            tb = AFSKReceiver(samples_q=samples_q)
            tb.start()
            logging.info("AFSK Receiver is running. Press Ctrl+C to stop.")
            # Run the GNU Radio flowgraph in a separate thread
            def run_tb():
                try:
                    tb.wait()
                except Exception as e:
                    logging.error(f"Error running GNU Radio flowgraph: {e}")
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, run_tb)
            # Keep the main coroutine running
            await asyncio.Event().wait()
        elif args.input[0] == 'raw':
            logging.info(f"Reading from file {args.input[1]}...")
            tasks.append(asyncio.create_task(read_samples_from_file(samples_q=samples_q, file=args.input[1])))
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
        else:
            logging.error(f"Unsupported input type: {args.input[0]}")
            raise Exception(f"unsupported input type: {args.input[0]}")
    except KeyboardInterrupt:
        logging.info("Program interrupted by user.")
        if 'tb' in locals():
            tb.stop()
            tb.wait()
    except Exception as err:
        logging.error(f"Error in main: {err}")
        print_exc(err)
    finally:
        # Cancel only the tasks we created to avoid RecursionError
        if 'tasks' in locals():
            for task in tasks:
                task.cancel()
            # Wait for all tasks to be cancelled
            await asyncio.gather(*tasks, return_exceptions=True)
            logging.info("All tasks have been cancelled.")

        # Stop the GNU Radio flowgraph if it's running
        if 'tb' in locals():
            tb.stop()
            tb.wait()
            logging.info("GNU Radio flowgraph stopped.")

        # Close the output file if it's not stdout
        if output_file_handle:
            try:
                output_file_handle.close()
                logging.debug(f"Closed output file: {args.output[1]}")
            except Exception as e:
                logging.error(f"Error closing output file: {e}")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Program interrupted by user.")
