import threading
import asyncio
import queue
import time
import os
import sys
import signal
from ttkbootstrap import Style

from core import (
    reset_hackrf,
    add_silence,
    ResampleAndSend,
    generate_aprs_wav,
    list_hackrf_devices,
    start_receiver,
    Frequency,
    ThreadSafeVariable,
    Application  # Now imported from core
)

from core.udp_listener import udp_listener
from core.udp_transmitter import udp_transmitter

def start_receiver_thread(receiver_stop_event, received_message_queue, device_index, frequency):
    receiver_thread = threading.Thread(
        target=start_receiver,
        args=(receiver_stop_event, received_message_queue, device_index, frequency),
        daemon=True
    )
    receiver_thread.start()
    return receiver_thread

def stop_receiver(stop_event, receiver_thread):
    stop_event.set()

def main_loop(frequency_var, transmitting_var, message_queue, stop_event, gain_var, if_gain_var, 
              receiver_stop_event, receiver_thread, received_message_queue, gui_app):
    while not stop_event.is_set():
        try:
            message = message_queue.get_nowait()
            if isinstance(message, tuple) and len(message) == 4:
                aprs_message, flags_before, flags_after, device_index = message
            else:
                aprs_message = message
                flags_before = 10
                flags_after = 4
                device_index = 0

            print(f"Processing message: {aprs_message}")

            # Stop receiver
            reset_hackrf()
            receiver_stop_event.set()
            gui_app.receiver_status_var.set("Receiver Stopped")
            print("About to sleep for 1 seconds...")
            time.sleep(1)
            print("Sleep done, receiver fully stopped. Now proceeding to transmitter.")

            # Generate WAV
            raw_wav = "raw_output.wav"
            processed_wav = "processed_output.wav"
            silence_before = 0
            silence_after = 0

            source_callsign = gui_app.get_callsign_source()
            destination_callsign = gui_app.get_callsign_dest()

            aprs_line = f"{source_callsign}>{destination_callsign}:{aprs_message}"

            asyncio.run(generate_aprs_wav(aprs_line, raw_wav, flags_before, flags_after))
            add_silence(raw_wav, processed_wav, silence_before, silence_after)

            gain = gain_var.get()
            if_gain = if_gain_var.get()

            # Transmit
            reset_hackrf()
            print(device_index)
            tb = ResampleAndSend(processed_wav, 2205000, device_index=device_index_var.get())
            if tb.initialize_hackrf(gain, if_gain):
                current_frequency = frequency_var.get()
                tb.set_center_freq(current_frequency)
                transmitting_var.set()
                tb.start()
                time.sleep(2)
                tb.stop_and_wait()
                transmitting_var.clear()
            else:
                print("HackRF initialization failed.")

            # Restart receiver
            receiver_stop_event.clear()
            receiver_thread = start_receiver_thread(receiver_stop_event, received_message_queue, device_index_var.get(), frequency_var.get())
            gui_app.receiver_status_var.set("Receiver Running")

        except queue.Empty:
            time.sleep(0.1)
        except Exception as e:
            print(f"Unexpected error in main_loop: {e}")



def on_closing(app, stop_event, receiver_stop_event, receiver_thread, udp_thread):
    reset_hackrf()
    stop_event.set()
    receiver_stop_event.set()
    stop_receiver(receiver_stop_event, receiver_thread)
    time.sleep(1)
    udp_thread.join()
    app.master.destroy()
    sys.exit(0)

def handle_signal(signum, frame):
    reset_hackrf()
    stop_event.set()
    receiver_stop_event.set()
    stop_receiver(receiver_stop_event, receiver_thread)
    time.sleep(1)
    udp_thread.join()
    app.master.destroy()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    try:
        style = Style(theme='cosmo')

        stop_event = threading.Event()
        transmitting_var = threading.Event()
        message_queue = queue.SimpleQueue()
        frequency_var = Frequency(28.12e6)
        gain_var = ThreadSafeVariable(14)
        if_gain_var = ThreadSafeVariable(47)
        receiver_stop_event = threading.Event()
        received_message_queue = queue.Queue()
        device_index_var = ThreadSafeVariable(0)

        # Start receiver
        receiver_thread = start_receiver_thread(receiver_stop_event, received_message_queue, device_index_var.get(), frequency_var.get())

        # Start UDP listener
        udp_thread = threading.Thread(
            target=udp_listener, 
            args=("127.0.0.1", 14580, message_queue, stop_event), 
            daemon=True
        )
        udp_thread.start()

        root = style.master
        root.title("Envoi de paquets APRS")
        root.geometry("2000x1200")

        app = Application(
            root,
            frequency_var,
            transmitting_var,
            message_queue,
            stop_event,
            gain_var,
            if_gain_var,
            receiver_stop_event,
            receiver_thread,
            received_message_queue,
            udp_transmitter,
            device_index_var
        )

        gui_thread = threading.Thread(
            target=main_loop,
            args=(frequency_var, transmitting_var, message_queue, stop_event, gain_var, if_gain_var,
                  receiver_stop_event, receiver_thread, received_message_queue, app),
            daemon=True
        )
        gui_thread.start()

        root.protocol("WM_DELETE_WINDOW", lambda: on_closing(app, stop_event, receiver_stop_event, receiver_thread, udp_thread))
        app.mainloop()

    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Exiting gracefully.")
        reset_hackrf()
        stop_event.set()
        receiver_stop_event.set()
        stop_receiver(receiver_stop_event, receiver_thread)
        time.sleep(1)
        udp_thread.join()
        app.master.destroy()
        sys.exit(0)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        reset_hackrf()
        stop_event.set()
        receiver_stop_event.set()
        stop_receiver(receiver_stop_event, receiver_thread)
        time.sleep(1)
        udp_thread.join()
        app.master.destroy()
        sys.exit(0)
    finally:
        print("Application has been closed.")
