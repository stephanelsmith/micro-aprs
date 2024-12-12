# run_without_gui.py

import asyncio
import json
import os
import queue
import signal
import sys
import threading
import time
from typing import Any, Dict

from core import (
    ResampleAndSend,
    add_silence,
    generate_aprs_wav,
    list_hackrf_devices,
    reset_hackrf,
    start_receiver,
    ThreadSafeVariable,
)
from core.udp_listener import udp_listener
from core.udp_transmitter import udp_transmitter

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration file path
CONFIG_FILE = "config.json"

# Constants
DEFAULT_CONFIG = {
    "frequency_hz": 50.01e6,
    "gain": 14,
    "if_gain": 47,
    "callsign_source": "VE2FPD",
    "callsign_dest": "VE2FPD-2",
    "flags_before": 10,
    "flags_after": 4,
    "send_ip": "127.0.0.1",
    "send_port": 14581,
    "carrier_only": False,
    "device_index": 0
}

RAW_WAV = "raw_output.wav"
PROCESSED_WAV = "processed_output.wav"
SAMPLING_RATE = 2205000


def load_config(config_file: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file or return default configuration.
    """
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = json.load(f)
        logger.info("Configuration loaded from %s.", config_file)
        return config
    else:
        logger.warning("Config file not found. Using default configuration.")
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any], config_file: str) -> None:
    """
    Save configuration to a JSON file.
    """
    with open(config_file, "w") as f:
        json.dump(config, f, indent=4)
    logger.info("Configuration saved to %s.", config_file)


def start_receiver_thread(
    receiver_stop_event: threading.Event,
    received_message_queue: queue.Queue,
    device_index: int,
    frequency: float
) -> threading.Thread:
    """
    Start the receiver thread.
    """
    receiver_thread = threading.Thread(
        target=start_receiver,
        args=(receiver_stop_event, received_message_queue, device_index, frequency),
        daemon=True
    )
    receiver_thread.start()
    logger.info("Receiver thread started on device %d at %.2f Hz.", device_index, frequency)
    return receiver_thread


def start_udp_listener(
    stop_event: threading.Event,
    message_queue: queue.SimpleQueue,
    ip: str = "127.0.0.1",
    port: int = 14580
) -> threading.Thread:
    """
    Start the UDP listener thread.
    """
    udp_thread = threading.Thread(
        target=udp_listener,
        args=(ip, port, message_queue, stop_event),
        daemon=True
    )
    udp_thread.start()
    logger.info("UDP listener started on %s:%d.", ip, port)
    return udp_thread


def process_message(
    message: Any,
    config: Dict[str, Any],
    queues: Dict[str, Any],
    vars: Dict[str, Any]
) -> None:
    """
    Process and transmit the APRS message.
    """
    try:
        if isinstance(message, tuple) and len(message) == 5:
            aprs_message, flags_before, flags_after, device_index, carrier_only = message
        else:
            aprs_message = message
            flags_before = config.get("flags_before", 10)
            flags_after = config.get("flags_after", 4)
            device_index = config.get("device_index", 0)
            carrier_only = config.get("carrier_only", False)

        if carrier_only:
            # Initiate carrier-only transmission
            logger.info("Initiating carrier-only transmission.")
            # Stop receiver if it's running
            reset_hackrf()
            queues['receiver_stop_event'].set()
            if queues['receiver_thread'] and queues['receiver_thread'].is_alive():
                queues['receiver_thread'].join()
                logger.info("Receiver thread stopped before carrier transmission.")
            time.sleep(1)  # Ensure receiver has fully stopped

            # Start carrier-only transmission if not already running
            if not queues.get('carrier_thread') or not queues['carrier_thread'].is_alive():
                carrier_thread = threading.Thread(
                    target=start_carrier_transmission,
                    args=(config, vars, queues['carrier_stop_event']),
                    daemon=True
                )
                carrier_thread.start()
                queues['carrier_thread'] = carrier_thread
                logger.info("Carrier-only transmission thread started.")
            return

        # Handle normal APRS message processing
        logger.info("Processing message: %s", aprs_message)

        # Generate WAV
        silence_before = 0
        silence_after = 0

        source_callsign = config.get("callsign_source", "VE2FPD")
        destination_callsign = config.get("callsign_dest", "VE2FPD")

        aprs_line = f"{source_callsign}>{destination_callsign}:{aprs_message}"

        asyncio.run(generate_aprs_wav(aprs_line, RAW_WAV, flags_before, flags_after))
        add_silence(RAW_WAV, PROCESSED_WAV, silence_before, silence_after)

        gain = vars['gain_var'].get()
        if_gain = vars['if_gain_var'].get()

        # Transmit
        reset_hackrf()
        tb = ResampleAndSend(PROCESSED_WAV, SAMPLING_RATE, device_index=device_index)
        if tb.initialize_hackrf(gain, if_gain):
            current_frequency = vars['frequency_var'].get()
            tb.set_center_freq(current_frequency)
            vars['transmitting_var'].set()
            tb.start()
            logger.info("Transmission started.")
            time.sleep(5)
            tb.stop_and_wait()
            vars['transmitting_var'].clear()
            logger.info("Transmission stopped.")
        else:
            logger.error("HackRF initialization failed.")

        # Restart receiver
        queues['receiver_stop_event'].clear()
        queues['receiver_thread'] = start_receiver_thread(
            queues['receiver_stop_event'],
            queues['received_message_queue'],
            device_index,
            vars['frequency_var'].get()
        )
        logger.info("Receiver thread restarted.")

        # Handle received messages
        while not queues['received_message_queue'].empty():
            received_message = queues['received_message_queue'].get()
            udp_transmitter(config['send_ip'], config['send_port'], received_message)
            logger.info(
                "Received message transmitted to %s:%d: %s",
                config['send_ip'],
                config['send_port'],
                received_message
            )

    except Exception as e:
        logger.exception("Error processing message: %s", e)


def start_carrier_transmission(config: Dict[str, Any], vars: Dict[str, Any], carrier_stop_event: threading.Event) -> None:
    """
    Start carrier-only transmission.
    """
    try:
        gain = vars['gain_var'].get()
        if_gain = vars['if_gain_var'].get()
        current_frequency = vars['frequency_var'].get()

        carrier_top_block = ResampleAndSend(
            input_file=None,
            output_rate=SAMPLING_RATE,
            device_index=config.get('device_index', 0),
            carrier_only=True,
            carrier_freq=current_frequency
        )

        if carrier_top_block.initialize_hackrf(gain, if_gain):
            carrier_top_block.set_center_freq(current_frequency)
            carrier_top_block.start()
            vars['transmitting_var'].set()
            logger.info("Carrier-only transmission started.")

            # Wait until carrier_stop_event is set
            while not carrier_stop_event.is_set():
                time.sleep(1)

            # Stop transmission
            carrier_top_block.stop_and_wait()
            vars['transmitting_var'].clear()
            logger.info("Carrier-only transmission stopped.")
        else:
            logger.error("Failed to initialize HackRF for carrier-only mode.")
    except Exception as e:
        logger.exception("Error starting carrier-only mode: %s", e)


def handle_signal(
    signum: int,
    frame: Any,
    queues: Dict[str, Any],
    udp_thread: threading.Thread,
    config_file: str
) -> None:
    """
    Handle termination signals for graceful shutdown.
    """
    logger.info("Signal %d received. Initiating shutdown...", signum)
    queues['stop_event'].set()
    queues['receiver_stop_event'].set()
    queues['carrier_stop_event'].set()


def main() -> None:
    """
    Main function to run the application.
    """
    # Load configuration
    config = load_config(CONFIG_FILE)

    # Initialize variables
    stop_event = threading.Event()
    transmitting_var = threading.Event()
    message_queue = queue.SimpleQueue()
    frequency_var = ThreadSafeVariable(config.get("frequency_hz", 28.12e6))
    gain_var = ThreadSafeVariable(config.get("gain", 14))
    if_gain_var = ThreadSafeVariable(config.get("if_gain", 47))
    receiver_stop_event = threading.Event()
    received_message_queue = queue.Queue()
    device_index_var = ThreadSafeVariable(config.get("device_index", 0))
    carrier_only = config.get("carrier_only", False)

    # Additional events and threads for carrier-only mode
    carrier_stop_event = threading.Event()
    carrier_thread = None

    # Variables dictionary
    vars_dict = {
        'frequency_var': frequency_var,
        'gain_var': gain_var,
        'if_gain_var': if_gain_var,
        'transmitting_var': transmitting_var
    }

    # Queues dictionary
    queues = {
        'stop_event': stop_event,
        'transmitting_var': transmitting_var,
        'message_queue': message_queue,
        'frequency_var': frequency_var,
        'gain_var': gain_var,
        'if_gain_var': if_gain_var,
        'receiver_stop_event': receiver_stop_event,
        'receiver_thread': None,  # To be set after thread starts
        'received_message_queue': received_message_queue,
        'device_index_var': device_index_var,
        'vars': vars_dict,
        'carrier_stop_event': carrier_stop_event,
        'carrier_thread': carrier_thread
    }

    # Start receiver thread
    receiver_thread = start_receiver_thread(
        receiver_stop_event,
        received_message_queue,
        device_index_var.get(),
        frequency_var.get()
    )
    queues['receiver_thread'] = receiver_thread

    # Start UDP listener thread
    udp_thread = start_udp_listener(
        stop_event,
        message_queue,
        config.get('send_ip', "127.0.0.1"),
        config.get('send_port', 14581)
    )

    # Register signal handlers for graceful shutdown
    signal.signal(
        signal.SIGINT,
        lambda s, f: handle_signal(s, f, queues, udp_thread, CONFIG_FILE)
    )
    signal.signal(
        signal.SIGTERM,
        lambda s, f: handle_signal(s, f, queues, udp_thread, CONFIG_FILE)
    )

    # If carrier_only is True in config, queue a "CARRIER_ONLY" message
    if carrier_only:
        logger.info("Carrier-only mode enabled in configuration. Queuing CARRIER_ONLY message.")
        message_queue.put("CARRIER_ONLY")

    # Main processing loop
    try:
        while not stop_event.is_set():
            try:
                message = message_queue.get_nowait()
                process_message(message, config, queues, vars_dict)
            except queue.Empty:
                pass
            except Exception as e:
                logger.exception("Error in message processing: %s", e)
            time.sleep(0.1)  # Prevents CPU overuse
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Exiting gracefully.")
    finally:
        # Clean up resources
        logger.info("Shutting down...")
        reset_hackrf()
        stop_event.set()
        receiver_stop_event.set()
        carrier_stop_event.set()

        # Stop carrier-only transmission if running
        if queues.get('carrier_thread') and queues['carrier_thread'].is_alive():
            queues['carrier_thread'].join()

        # Stop receiver thread
        if queues['receiver_thread'] and queues['receiver_thread'].is_alive():
            queues['receiver_thread'].join()

        # Stop UDP listener thread
        if udp_thread.is_alive():
            udp_thread.join()

        # Save configuration
        save_config(config, CONFIG_FILE)
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    main()
