# run_without_gui.py

import threading
import asyncio
import queue
import time
import os
import sys
import signal
import json
# Correct Import
from core.udp_listener import udp_listener
from core.udp_transmitter import udp_transmitter

from core import (
    reset_hackrf,
    add_silence,
    ResampleAndSend,
    generate_aprs_wav,
    list_hackrf_devices,
    start_receiver,
    Frequency,
    ThreadSafeVariable,
    udp_listener,
    udp_transmitter
)

# Configuration file path
CONFIG_FILE = "config.json"

def load_config(config_file):
    """Load configuration from a JSON file."""
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = json.load(f)
        return config
    else:
        # Default configuration
        return {
            "frequency_hz": 28.12e6,
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

def save_config(config, config_file):
    """Save configuration to a JSON file."""
    with open(config_file, "w") as f:
        json.dump(config, f, indent=4)
    print("Configuration saved.")

def start_receiver_thread(receiver_stop_event, received_message_queue, device_index, frequency):
    """Start the receiver thread."""
    receiver_thread = threading.Thread(
        target=start_receiver,
        args=(receiver_stop_event, received_message_queue, device_index, frequency),
        daemon=True
    )
    receiver_thread.start()
    return receiver_thread

def start_udp_listener(stop_event, message_queue, ip="127.0.0.1", port=14580):
    """Start the UDP listener thread."""
    udp_thread = threading.Thread(
        target=udp_listener, 
        args=(ip, port, message_queue, stop_event), 
        daemon=True
    )
    udp_thread.start()
    print(f"UDP listener started on {ip}:{port}.")
    return udp_thread

def process_message(message, config, queues, vars):
    """Process and transmit the APRS message."""
    try:
        if isinstance(message, tuple) and len(message) == 5:
            aprs_message, flags_before, flags_after, device_index, carrier_only = message
        else:
            aprs_message = message
            flags_before = config.get("flags_before", 10)
            flags_after = config.get("flags_after", 4)
            device_index = config.get("device_index", 0)
            carrier_only = config.get("carrier_only", False)

        print(f"Processing message: {aprs_message}")

        # Stop receiver
        reset_hackrf()
        queues['receiver_stop_event'].set()
        queues['receiver_thread'].join()
        time.sleep(1)

        # Handle Carrier Only Mode
        if carrier_only:
            start_carrier_transmission(config, vars)
            return

        # Generate WAV
        raw_wav = "raw_output.wav"
        processed_wav = "processed_output.wav"
        silence_before = 0
        silence_after = 0

        source_callsign = config.get("callsign_source", "VE2FPD")
        destination_callsign = config.get("callsign_dest", "VE2FPD-2")

        aprs_line = f"{source_callsign}>{destination_callsign}:{aprs_message}"

        asyncio.run(generate_aprs_wav(aprs_line, raw_wav, flags_before, flags_after))
        add_silence(raw_wav, processed_wav, silence_before, silence_after)

        gain = vars['gain_var'].get()
        if_gain = vars['if_gain_var'].get()

        # Transmit
        reset_hackrf()
        tb = ResampleAndSend(processed_wav, 2205000, device_index=device_index)
        if tb.initialize_hackrf(gain, if_gain):
            current_frequency = vars['frequency_var'].get()
            tb.set_center_freq(current_frequency)
            vars['transmitting_var'].set()
            tb.start()
            print("Transmission started.")
            time.sleep(2)
            tb.stop_and_wait()
            vars['transmitting_var'].clear()
            print("Transmission stopped.")
        else:
            print("HackRF initialization failed.")

        # Restart receiver
        queues['receiver_stop_event'].clear()
        queues['receiver_thread'] = start_receiver_thread(
            queues['receiver_stop_event'], 
            queues['received_message_queue'], 
            device_index, 
            vars['frequency_var'].get()
        )
        print("Receiver restarted.")

        # Handle received messages
        while not queues['received_message_queue'].empty():
            received_message = queues['received_message_queue'].get()
            udp_transmitter(config['send_ip'], config['send_port'], received_message)
            print(f"Received message transmitted to {config['send_ip']}:{config['send_port']}: {received_message}")

    except Exception as e:
        print(f"Error processing message: {e}")

def start_carrier_transmission(config, vars):
    """Start carrier only transmission."""
    try:
        gain = vars['gain_var'].get()
        if_gain = vars['if_gain_var'].get()
        current_frequency = vars['frequency_var'].get()

        carrier_top_block = ResampleAndSend(
            input_file=None,
            output_rate=2205000,
            device_index=config.get('device_index', 0),
            carrier_only=True,
            carrier_freq=current_frequency
        )

        if carrier_top_block.initialize_hackrf(gain, if_gain):
            carrier_top_block.set_center_freq(current_frequency)
            carrier_top_block.start()
            vars['transmitting_var'].set()
            print("Carrier only transmission started.")
        else:
            print("Failed to initialize HackRF for carrier only mode.")
    except Exception as e:
        print(f"Error starting carrier only mode: {e}")

def stop_carrier_transmission(vars):
    """Stop carrier only transmission."""
    # Implement this if you need to handle carrier only stop
    pass

def handle_signal(signum, frame, queues, udp_thread, config_file):
    """Handle termination signals."""
    print(f"Signal {signum} received. Shutting down...")
    reset_hackrf()
    queues['stop_event'].set()
    queues['receiver_stop_event'].set()
    queues['receiver_thread'].join()
    udp_thread.join()
    save_config({
        "frequency_hz": queues['vars']['frequency_var'].get(),
        "gain": queues['vars']['gain_var'].get(),
        "if_gain": queues['vars']['if_gain_var'].get(),
        "callsign_source": config.get("callsign_source", "VE2FPD"),
        "callsign_dest": config.get("callsign_dest", "VE2FPD-2"),
        "flags_before": config.get("flags_before", 10),
        "flags_after": config.get("flags_after", 4),
        "send_ip": config.get("send_ip", "127.0.0.1"),
        "send_port": config.get("send_port", 14581),
        "carrier_only": config.get("carrier_only", False),
        "device_index": config.get("device_index", 0)
    }, config_file)
    print("Shutdown complete.")
    sys.exit(0)

def main():
    # Load configuration
    config = load_config(CONFIG_FILE)

    # Initialize variables
    stop_event = threading.Event()
    transmitting_var = threading.Event()
    message_queue = queue.SimpleQueue()
    frequency_var = Frequency(config.get("frequency_hz", 28.12e6))
    gain_var = ThreadSafeVariable(config.get("gain", 14))
    if_gain_var = ThreadSafeVariable(config.get("if_gain", 47))
    receiver_stop_event = threading.Event()
    received_message_queue = queue.Queue()
    device_index_var = ThreadSafeVariable(config.get("device_index", 0))
    send_ip = config.get("send_ip", "127.0.0.1")
    send_port = config.get("send_port", 14581)

    # Queues and variables dictionary
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
        'vars': {
            'frequency_var': frequency_var,
            'gain_var': gain_var,
            'if_gain_var': if_gain_var,
            'transmitting_var': transmitting_var
        }
    }

    # Start receiver thread
    receiver_thread = start_receiver_thread(
        receiver_stop_event, 
        received_message_queue, 
        device_index_var.get(), 
        frequency_var.get()
    )
    queues['receiver_thread'] = receiver_thread
    print(f"Receiver started on device {device_index_var.get()} at frequency {frequency_var.get()} Hz.")

    # Start UDP listener thread
    udp_thread = start_udp_listener(stop_event, message_queue, config['send_ip'], config['send_port'])

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, lambda s, f: handle_signal(s, f, queues, udp_thread, CONFIG_FILE))
    signal.signal(signal.SIGTERM, lambda s, f: handle_signal(s, f, queues, udp_thread, CONFIG_FILE))

    # Main processing loop
    try:
        while not stop_event.is_set():
            try:
                message = message_queue.get_nowait()
                process_message(message, config, queues, queues['vars'])
            except queue.Empty:
                pass
            except Exception as e:
                print(f"Error in message processing: {e}")
            time.sleep(0.1)  # Prevents CPU overuse
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Exiting gracefully.")
    finally:
        # Clean up resources
        print("Shutting down...")
        reset_hackrf()
        stop_event.set()
        receiver_stop_event.set()
        if queues['receiver_thread'].is_alive():
            queues['receiver_thread'].join()
        if udp_thread.is_alive():
            udp_thread.join()
        save_config(config, CONFIG_FILE)
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
