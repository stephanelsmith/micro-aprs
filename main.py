import tkinter as tk
from ttkbootstrap import Style, ttk
from ttkbootstrap.constants import *
import threading
import asyncio
import queue
import time
import os
import sys
import signal

# Import from core.py
from core import (
    reset_hackrf,
    add_silence,
    ResampleAndSend,
    generate_aprs_wav,
    udp_listener,
    Frequency,
    ThreadSafeVariable,
    start_receiver,
)

class Application(ttk.Frame):
    def __init__(
        self, 
        master, 
        frequency_var, 
        transmitting_var, 
        message_queue, 
        stop_event, 
        gain_var, 
        if_gain_var,
        device_index_var,
        received_message_queue,
        *args, 
        **kwargs
    ):
        super().__init__(master, *args, **kwargs)
        self.gain_var = gain_var
        self.if_gain_var = if_gain_var
        self.device_index_var = device_index_var
        self.master = master
        self.frequency_var = frequency_var
        self.transmitting_var = transmitting_var
        self.message_queue = message_queue
        self.num_flags_before = tk.IntVar(value=10)  # Default value
        self.num_flags_after = tk.IntVar(value=4)    # Default value
        self.stop_event = stop_event
        self.received_message_queue = received_message_queue

        self.pack(fill=BOTH, expand=True, padx=20, pady=20)

        # Initialize GUI components first to set up status_var
        self.create_widgets()

        # Then load icons
        self.load_icons()

        # Start checking transmission status
        self.check_transmission_status()

        # Start checking for received messages
        self.check_received_messages()

    def load_icons(self):
        # Ensure the assets directory exists
        assets_path = os.path.join(os.path.dirname(__file__), 'assets')
        if not os.path.isdir(assets_path):
            os.makedirs(assets_path)
            # Notify the user within the GUI
            self.status_var.set(f"'assets' directory created at {assets_path}. Please add required icon files.")
            self.send_icon = None
            self.transmitting_icon = None
            self.idle_icon = None
            return

        try:
            self.send_icon = tk.PhotoImage(file=os.path.join(assets_path, 'send_icon.png'))
            self.transmitting_icon = tk.PhotoImage(file=os.path.join(assets_path, 'transmitting_icon.png'))
            self.idle_icon = tk.PhotoImage(file=os.path.join(assets_path, 'idle_icon.png'))
        except Exception as e:
            self.status_var.set(f"Error loading icons: {e}")
            self.send_icon = None
            self.transmitting_icon = None
            self.idle_icon = None

    def create_widgets(self):
        # Header
        header = ttk.Label(self, text="APRS Transmission Control", font=("Helvetica", 18, "bold"))
        header.grid(row=0, column=0, columnspan=4, pady=(0, 20))

        # HackRF Settings Frame
        hackrf_frame = ttk.Labelframe(self, text="HackRF Settings", padding=20)
        hackrf_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=(0,10), pady=(0, 20))
        hackrf_frame.columnconfigure(1, weight=1)

        ttk.Label(hackrf_frame, text="Device Index:").grid(row=0, column=0, sticky="w")
        self.device_index_entry = ttk.Entry(hackrf_frame, width=10)
        self.device_index_entry.grid(row=0, column=1, pady=5, padx=10, sticky="w")
        self.device_index_entry.insert(0, str(self.device_index_var.get()))

        ttk.Label(hackrf_frame, text="Gain:").grid(row=1, column=0, sticky="w")
        self.gain_entry = ttk.Entry(hackrf_frame, width=20)
        self.gain_entry.grid(row=1, column=1, pady=5, padx=10, sticky="ew")
        self.gain_entry.insert(0, str(self.gain_var.get()))

        ttk.Label(hackrf_frame, text="IF Gain:").grid(row=2, column=0, sticky="w")
        self.if_gain_entry = ttk.Entry(hackrf_frame, width=20)
        self.if_gain_entry.grid(row=2, column=1, pady=5, padx=10, sticky="ew")
        self.if_gain_entry.insert(0, str(self.if_gain_var.get()))

        self.apply_hackrf_button = ttk.Button(hackrf_frame, text="Apply", command=self.update_hackrf_settings, bootstyle=PRIMARY)
        self.apply_hackrf_button.grid(row=3, column=0, columnspan=2, pady=(10,0))

        # Frequency Settings Frame
        freq_frame = ttk.Labelframe(self, text="Frequency Settings", padding=20)
        freq_frame.grid(row=1, column=0, sticky="ew", padx=(0,10), pady=(0, 20))
        freq_frame.columnconfigure(1, weight=1)

        ttk.Label(freq_frame, text="Frequency (MHz):").grid(row=0, column=0, sticky="w")
        self.frequency_entry = ttk.Entry(freq_frame, width=20)
        self.frequency_entry.grid(row=0, column=1, pady=5, padx=10, sticky="ew")
        self.frequency_entry.insert(0, "144.39")

        self.freq_notification = ttk.Label(freq_frame, text="", foreground="red")
        self.freq_notification.grid(row=1, column=0, columnspan=2, sticky="w")

        self.apply_button = ttk.Button(freq_frame, text="Apply", command=self.update_frequency, bootstyle=PRIMARY)
        self.apply_button.grid(row=2, column=0, columnspan=2, pady=(10,0))

        # Callsign Settings Frame
        callsign_frame = ttk.Labelframe(self, text="Callsign Settings", padding=20)
        callsign_frame.grid(row=1, column=1, sticky="ew", padx=(10,0), pady=(0, 20))
        callsign_frame.columnconfigure(1, weight=1)

        ttk.Label(callsign_frame, text="Callsign:").grid(row=0, column=0, sticky="w")
        self.callsign_entry = ttk.Entry(callsign_frame, width=25)
        self.callsign_entry.grid(row=0, column=1, pady=5, padx=10, sticky="ew")
        self.callsign_entry.insert(0, "VE2FPD")  # Default callsign

        ttk.Label(callsign_frame, text="Preamble length:").grid(row=1, column=0, sticky="w")
        self.flags_before_entry = ttk.Entry(callsign_frame, width=10)
        self.flags_before_entry.grid(row=1, column=1, pady=5, padx=10, sticky="ew")
        self.flags_before_entry.insert(0, str(self.num_flags_before.get()))

        ttk.Label(callsign_frame, text="Postamble length:").grid(row=2, column=0, sticky="w")
        self.flags_after_entry = ttk.Entry(callsign_frame, width=10)
        self.flags_after_entry.grid(row=2, column=1, pady=5, padx=10, sticky="ew")
        self.flags_after_entry.insert(0, str(self.num_flags_after.get()))


        self.callsign_notification = ttk.Label(callsign_frame, text="", foreground="red")
        self.callsign_notification.grid(row=3, column=0, columnspan=2, sticky="w")

        # Test Message Button
        self.test_button = ttk.Button(
            self, 
            text="Send Test APRS Message", 
            command=self.queue_test_message, 
            bootstyle=SUCCESS, 
            image=None,  # Placeholder until icons are loaded
            compound=LEFT
        )
        self.test_button.grid(row=3, column=0, columnspan=4, pady=(0, 20), ipadx=10, ipady=5)

        # Transmission Status Frame
        status_frame = ttk.Frame(self)
        status_frame.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)

        ttk.Label(status_frame, text="Status:", font=("Helvetica", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.transmission_label = ttk.Label(status_frame, text="Idle", font=("Helvetica", 12), background="#6c757d", foreground="white", padding=5)
        self.transmission_label.grid(row=0, column=1, sticky="w", padx=10)
        self.transmission_icon_label = None  # Will be set after icons are loaded

        # Progress Bar
        self.progress = ttk.Progressbar(self, mode='indeterminate')
        self.progress.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        self.progress.stop()

        # Received Messages Frame
        messages_frame = ttk.Labelframe(self, text="Received Messages", padding=20)
        messages_frame.grid(row=6, column=0, columnspan=4, sticky="nsew", pady=(0, 10))
        messages_frame.columnconfigure(0, weight=1)
        messages_frame.rowconfigure(0, weight=1)

        self.messages_text = tk.Text(messages_frame, wrap='word', height=10)
        self.messages_text.grid(row=0, column=0, sticky="nsew")

        # Add a scrollbar
        scrollbar = ttk.Scrollbar(messages_frame, orient='vertical', command=self.messages_text.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.messages_text['yscrollcommand'] = scrollbar.set

        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=SUNKEN, anchor='w')
        status_bar.grid(row=7, column=0, columnspan=4, sticky="ew")

        # Receiver Status Bar
        self.receiver_status_var = tk.StringVar()
        self.receiver_status_var.set("Receiver Running")
        receiver_status_bar = ttk.Label(self, textvariable=self.receiver_status_var, relief=SUNKEN, anchor='w')
        receiver_status_bar.grid(row=8, column=0, columnspan=4, sticky="ew")

    def update_hackrf_settings(self):
        try:
            device_index = int(self.device_index_entry.get())
            gain = float(self.gain_entry.get())
            if_gain = float(self.if_gain_entry.get())
            # Optional: Validate gain values (e.g., within acceptable ranges)
            self.device_index_var.set(device_index)
            self.gain_var.set(gain)
            self.if_gain_var.set(if_gain)
            self.status_var.set(f"HackRF settings updated: Device Index={device_index}, Gain={gain}, IF Gain={if_gain}")
            print(f"HackRF settings updated: Device Index={device_index}, Gain={gain}, IF Gain={if_gain}")
        except ValueError as ve:
            self.status_var.set(f"Invalid input values: {ve}")
            print(f"Invalid input values: {ve}")

    def update_frequency(self):
        try:
            frequency_mhz = float(self.frequency_entry.get())
            if not (0 < frequency_mhz < 3000):
                raise ValueError("Frequency out of valid range.")
            self.frequency_var.set(frequency_mhz * 1e6)
            self.freq_notification.config(text="Frequency updated successfully.", foreground="green")
            self.status_var.set(f"Frequency set to {frequency_mhz} MHz.")
            print(f"Frequency updated to {frequency_mhz} MHz")
        except ValueError as ve:
            self.freq_notification.config(text=f"Error: {ve}")
            self.status_var.set("Failed to update frequency.")
            print("Invalid frequency input.")

    def queue_test_message(self):
        callsign = self.callsign_entry.get().strip()
        if not self.validate_callsign(callsign):
            self.callsign_notification.config(text="Callsign must be 3-6 alphanumeric characters.", foreground="red")
            self.status_var.set("Invalid callsign input.")
            print("Invalid callsign input.")
            return

        # Get number of flags before and after
        try:
            flags_before = int(self.flags_before_entry.get())
            flags_after = int(self.flags_after_entry.get())
            if flags_before < 0 or flags_after < 0:
                raise ValueError("Flags must be non-negative integers.")
        except ValueError as ve:
            self.callsign_notification.config(text=f"Error: {ve}", foreground="red")
            self.status_var.set("Invalid flags input.")
            print("Invalid flags input.")
            return

        # Construct the APRS message with the provided callsign
        aprs_message = f"{callsign}>APRS:TEST 123!"
        self.message_queue.put((aprs_message, flags_before, flags_after))

        self.callsign_notification.config(text="Test message queued.", foreground="green")
        self.status_var.set(f"Test message queued with callsign: {aprs_message}")
        print(f"Test message queued with callsign: {aprs_message} and flags_before: {flags_before}, flags_after: {flags_after}")

    def validate_callsign(self, callsign):
        # Simple validation: length and alphanumeric
        return 3 <= len(callsign) <= 6 and callsign.isalnum()

    def check_transmission_status(self):
        if self.transmitting_var.is_set():
            self.transmission_label.config(text="Transmitting", background="#28a745")
            if hasattr(self, 'transmitting_icon') and self.transmitting_icon:
                if not self.transmission_icon_label:
                    self.transmission_icon_label = ttk.Label(self, image=self.transmitting_icon)
                    self.transmission_icon_label.grid(row=3, column=4, sticky="w")
                else:
                    self.transmission_icon_label.config(image=self.transmitting_icon)
            self.progress.start(10)
            self.status_var.set("Transmitting...")
        else:
            self.transmission_label.config(text="Idle", background="#6c757d")
            if hasattr(self, 'idle_icon') and self.idle_icon:
                if not self.transmission_icon_label:
                    self.transmission_icon_label = ttk.Label(self, image=self.idle_icon)
                    self.transmission_icon_label.grid(row=3, column=4, sticky="w")
                else:
                    self.transmission_icon_label.config(image=self.idle_icon)
            self.progress.stop()
            self.status_var.set("Idle.")
        self.after(500, self.check_transmission_status)

    def check_received_messages(self):
        try:
            while True:
                message = self.received_message_queue.get_nowait()
                self.messages_text.insert('end', message + '\n')
                self.messages_text.see('end')  # Scroll to the end
        except queue.Empty:
            pass
        self.after(500, self.check_received_messages)

def start_receiver_thread(receiver_stop_event, received_message_queue, device_index):
    receiver_thread = threading.Thread(
        target=start_receiver, 
        args=(receiver_stop_event, received_message_queue, device_index),
        daemon=True
    )
    receiver_thread.start()
    return receiver_thread

def stop_receiver(stop_event, receiver_thread):
    stop_event.set()
    receiver_thread.join()

def main_loop(frequency_var, transmitting_var, message_queue, stop_event, gain_var, if_gain_var, 
              device_index_var, receiver_stop_event, receiver_thread, received_message_queue, gui_app):
    while not stop_event.is_set():
        try:
            message = message_queue.get_nowait()
            print(f"Processing message: {message}")

            if isinstance(message, tuple):
                aprs_message, flags_before, flags_after = message
            else:
                # For messages received via UDP listener without flags
                aprs_message = message
                flags_before = 10  # Default number of flags before
                flags_after = 4    # Default number of flags after

            print(f"Processing message: {aprs_message}, flags_before: {flags_before}, flags_after: {flags_after}")
            
            # Stop the receiver before transmission
            print("Stopping receiver before transmission...")
            receiver_stop_event.set()  # Signal the AFSK Receiver to stop
            receiver_thread.join()      # Wait for the AFSK Receiver to stop
            time.sleep(1)
            print("Receiver stopped.")
            gui_app.receiver_status_var.set("Receiver Stopped")

            # Generate WAV file
            raw_wav = "raw_output.wav"
            processed_wav = "processed_output.wav"
            silence_before = 0
            silence_after = 0
            try:
                asyncio.run(generate_aprs_wav(aprs_message, raw_wav, flags_before, flags_after))
                print(f"Generated WAV: {raw_wav}")
                add_silence(raw_wav, processed_wav, silence_before, silence_after)
                print(f"Processed WAV: {processed_wav}")
            except Exception as e:
                print(f"Error in generating WAV or processing: {e}")
                continue

            gain = gain_var.get()
            if_gain = if_gain_var.get()
            device_index = device_index_var.get()

            # Reset and Initialize HackRF
            reset_hackrf()
            tb = ResampleAndSend(processed_wav, 2205000, device_index=device_index)
            if tb.initialize_hackrf(gain, if_gain):
                current_frequency = frequency_var.get()
                tb.set_center_freq(current_frequency)
                print(f"Frequency set to {current_frequency / 1e6} MHz. Starting transmission...")
                transmitting_var.set()
                tb.start()
                try:
                    time.sleep(2)  # Transmit for 2 seconds
                finally:
                    tb.stop_and_wait()
                    transmitting_var.clear()
                    print("Transmission completed.")
            else:
                print("HackRF initialization failed.")

            # Restart the receiver after transmission
            print("Restarting receiver after transmission...")
            receiver_stop_event.clear()
            receiver_thread = start_receiver_thread(
                receiver_stop_event, 
                received_message_queue, 
                device_index
            )
            gui_app.receiver_status_var.set("Receiver Running")
            print("Receiver restarted.")

        except queue.Empty:
            time.sleep(0.1)  # Prevent tight loop when queue is empty
        except Exception as e:
            print(f"Unexpected error in main_loop: {e}")

def on_closing(app, stop_event, receiver_stop_event, receiver_thread, udp_thread):
    stop_event.set()
    receiver_stop_event.set()
    stop_receiver(receiver_stop_event, receiver_thread)
    udp_thread.join()
    app.master.destroy()

def handle_signal(signum, frame):
    # Handle termination signals to ensure graceful shutdown
    print(f"Received signal {signum}, shutting down gracefully.")
    sys.exit(0)

if __name__ == "__main__":
    # Handle termination signals for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)   # Handle Ctrl+C
    signal.signal(signal.SIGTERM, handle_signal)  # Handle termination signals

    try:
        style = Style(theme='cosmo')  # Choose a modern theme like 'cosmo', 'flatly', 'journal', etc.

        stop_event = threading.Event()
        transmitting_var = threading.Event()
        message_queue = queue.SimpleQueue()

        frequency_var = Frequency(144.39e6)  # Default frequency in Hz
        gain_var = ThreadSafeVariable(14)     # Default gain
        if_gain_var = ThreadSafeVariable(47)  # Default IF gain
        device_index_var = ThreadSafeVariable(0)  # Default HackRF device index

        # Create stop event and received message queue for receiver
        receiver_stop_event = threading.Event()
        received_message_queue = queue.Queue()

        # Start the AFSK Receiver
        receiver_thread = start_receiver_thread(
            receiver_stop_event, 
            received_message_queue, 
            device_index_var.get()
        )

        # Start the UDP Listener
        udp_thread = threading.Thread(
            target=udp_listener, 
            args=("127.0.0.1", 14580, message_queue, stop_event), 
            daemon=True
        )
        udp_thread.start()

        root = style.master
        root.title("APRS Transmission Control")
        root.geometry("800x800")
        root.resizable(True, True)

        app = Application(
            root, 
            frequency_var, 
            transmitting_var, 
            message_queue, 
            stop_event, 
            gain_var, 
            if_gain_var,
            device_index_var,
            received_message_queue
        )

        gui_thread = threading.Thread(
            target=main_loop, 
            args=(
                frequency_var, 
                transmitting_var, 
                message_queue, 
                stop_event, 
                gain_var, 
                if_gain_var, 
                device_index_var,
                receiver_stop_event, 
                receiver_thread, 
                received_message_queue,
                app  # Pass the GUI application instance for status updates
            ), 
            daemon=True
        )
        gui_thread.start()

        root.protocol("WM_DELETE_WINDOW", lambda: on_closing(app, stop_event, receiver_stop_event, receiver_thread, udp_thread))
        app.mainloop()

    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Exiting gracefully.")
        stop_event.set()
        sys.exit(0)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        stop_event.set()
        sys.exit(1)
    finally:
        print("Application has been closed.")
