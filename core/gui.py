import tkinter as tk
from ttkbootstrap import Style, ttk
from ttkbootstrap.constants import *
import os
import queue
import time
import asyncio
import threading

# We assume that all imports like Frequency, ThreadSafeVariable, generate_aprs_wav, etc.
# are available from core's __init__.py if needed. If not, adjust imports accordingly.

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
        receiver_stop_event,
        receiver_thread,
        received_message_queue,
        device_index_var,
        *args,
        **kwargs
    ):
        super().__init__(master, *args, **kwargs)

        # Store references to shared state
        self.master = master
        self.frequency_var = frequency_var
        self.transmitting_var = transmitting_var
        self.message_queue = message_queue
        self.stop_event = stop_event
        self.gain_var = gain_var
        self.if_gain_var = if_gain_var
        self.receiver_stop_event = receiver_stop_event
        self.receiver_thread = receiver_thread
        self.received_message_queue = received_message_queue
        self.device_index_var = device_index_var

        # State variables for GUI
        self.num_flags_before = tk.IntVar(value=10)  # Default value
        self.num_flags_after = tk.IntVar(value=4)    # Default value
        self.status_var = tk.StringVar(value="Ready")
        self.receiver_status_var = tk.StringVar(value="Receiver Running")

        # Ensure 'assets' directory for icons
        self.send_icon = None
        self.transmitting_icon = None
        self.idle_icon = None

        # Main container
        self.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Create a scrollable frame
        self.canvas = tk.Canvas(self, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Load icons
        self.load_icons()

        # Build GUI widgets
        self.create_widgets()

        # Periodically check transmission status and received messages
        self.after(500, self.check_transmission_status)
        self.after(500, self.check_received_messages)

    def load_icons(self):
        # Adjust asset path as needed
        assets_path = os.path.join(os.path.dirname(__file__), 'assets')
        if not os.path.isdir(assets_path):
            os.makedirs(assets_path)
            self.status_var.set(f"'assets' directory created at {assets_path}. Please add required icon files.")
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
        header = ttk.Label(
            self.scrollable_frame,
            text="APRS Transmission Control",
            font=("Helvetica", 18, "bold")
        )
        header.grid(row=0, column=0, columnspan=4, pady=(0, 20), sticky="w")

        # HackRF Device Selection
        device_frame = ttk.Labelframe(self.scrollable_frame, text="HackRF Device Selection", padding=20)
        device_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=0, pady=(0, 20))
        device_frame.columnconfigure(1, weight=1)

        ttk.Label(device_frame, text="Select HackRF Device:").grid(row=0, column=0, sticky="w")
        self.device_combobox = ttk.Combobox(device_frame, state="readonly")
        self.device_combobox.grid(row=0, column=1, pady=5, padx=10, sticky="ew")
        self.populate_device_combobox()

        # HackRF Settings
        hackrf_frame = ttk.Labelframe(self.scrollable_frame, text="HackRF Settings", padding=20)
        hackrf_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=(0,10), pady=(0, 20))
        hackrf_frame.columnconfigure(1, weight=1)

        ttk.Label(hackrf_frame, text="Gain:").grid(row=0, column=0, sticky="w")
        self.gain_entry = ttk.Entry(hackrf_frame, width=20)
        self.gain_entry.grid(row=0, column=1, pady=5, padx=10, sticky="ew")
        self.gain_entry.insert(0, str(self.gain_var.get()))

        ttk.Label(hackrf_frame, text="IF Gain:").grid(row=1, column=0, sticky="w")
        self.if_gain_entry = ttk.Entry(hackrf_frame, width=20)
        self.if_gain_entry.grid(row=1, column=1, pady=5, padx=10, sticky="ew")
        self.if_gain_entry.insert(0, str(self.if_gain_var.get()))

        self.apply_hackrf_button = ttk.Button(hackrf_frame, text="Apply", command=self.update_hackrf_settings)
        self.apply_hackrf_button.grid(row=2, column=0, columnspan=2, pady=(10,0))

        # Frequency Settings
        freq_frame = ttk.Labelframe(self.scrollable_frame, text="Frequency Settings", padding=20)
        freq_frame.grid(row=2, column=2, columnspan=2, sticky="ew", padx=(10,0), pady=(0, 20))
        freq_frame.columnconfigure(1, weight=1)

        ttk.Label(freq_frame, text="Frequency (MHz):").grid(row=0, column=0, sticky="w")
        self.frequency_entry = ttk.Entry(freq_frame, width=20)
        self.frequency_entry.grid(row=0, column=1, pady=5, padx=10, sticky="ew")
        self.frequency_entry.insert(0, "28.12")

        self.freq_notification = ttk.Label(freq_frame, text="", foreground="red")
        self.freq_notification.grid(row=1, column=0, columnspan=2, sticky="w")

        self.apply_button = ttk.Button(freq_frame, text="Apply", command=self.update_frequency)
        self.apply_button.grid(row=2, column=0, columnspan=2, pady=(10,0))

        # Callsign Settings
        callsign_frame = ttk.Labelframe(self.scrollable_frame, text="Callsign Settings", padding=20)
        callsign_frame.grid(row=3, column=0, columnspan=4, sticky="ew", padx=0, pady=(0, 20))
        callsign_frame.columnconfigure(1, weight=1)

        ttk.Label(callsign_frame, text="Callsign:").grid(row=0, column=0, sticky="w")
        self.callsign_entry = ttk.Entry(callsign_frame, width=25)
        self.callsign_entry.grid(row=0, column=1, pady=5, padx=10, sticky="ew")
        self.callsign_entry.insert(0, "VE2FPD")

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
            self.scrollable_frame,
            text="Send Test APRS Message",
            command=self.queue_test_message
        )
        self.test_button.grid(row=4, column=0, columnspan=4, pady=(0, 20), ipadx=10, ipady=5, sticky="ew")

        # Transmission Status Frame
        status_frame = ttk.Frame(self.scrollable_frame)
        status_frame.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)

        ttk.Label(status_frame, text="Status:", font=("Helvetica", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.transmission_label = ttk.Label(
            status_frame,
            text="Idle",
            font=("Helvetica", 12),
            background="#6c757d",
            foreground="white",
            padding=5
        )
        self.transmission_label.grid(row=0, column=1, sticky="w", padx=10)
        self.transmission_icon_label = None

        # Progress Bar
        self.progress = ttk.Progressbar(self.scrollable_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        self.progress.stop()

        # Received Messages Frame
        messages_frame = ttk.Labelframe(self.scrollable_frame, text="Received Messages", padding=20)
        messages_frame.grid(row=7, column=0, columnspan=4, sticky="nsew", pady=(0, 10))
        messages_frame.columnconfigure(0, weight=1)
        messages_frame.rowconfigure(0, weight=1)

        self.messages_text = tk.Text(messages_frame, wrap='word', height=10)
        self.messages_text.grid(row=0, column=0, sticky="nsew")

        msg_scrollbar = ttk.Scrollbar(messages_frame, orient='vertical', command=self.messages_text.yview)
        msg_scrollbar.grid(row=0, column=1, sticky='ns')
        self.messages_text['yscrollcommand'] = msg_scrollbar.set

        # Status Bar
        status_bar = ttk.Label(
            self.scrollable_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor='w'
        )
        status_bar.grid(row=8, column=0, columnspan=4, sticky="ew")

        # Receiver Status Bar
        receiver_status_bar = ttk.Label(
            self.scrollable_frame,
            textvariable=self.receiver_status_var,
            relief=tk.SUNKEN,
            anchor='w'
        )
        receiver_status_bar.grid(row=9, column=0, columnspan=4, sticky="ew")

        # Grid configuration for resizing
        self.scrollable_frame.grid_rowconfigure(7, weight=1)
        self.scrollable_frame.grid_columnconfigure(3, weight=1)

    def populate_device_combobox(self):
        from core import list_hackrf_devices
        devices = list_hackrf_devices()
        if not devices:
            self.device_combobox['values'] = ["No HackRF devices found"]
            self.device_combobox.current(0)
            self.device_combobox.config(state="disabled")
            self.status_var.set("No HackRF devices detected. Please connect a device.")
        else:
            device_list = [f"HackRF {dev['index']}" for dev in devices]
            self.device_combobox['values'] = device_list
            self.device_combobox.current(0)
            self.device_combobox.bind("<<ComboboxSelected>>", self.on_device_selected)
            # Set initial device index
            self.device_index_var.set(devices[0]['index'])
            self.status_var.set(f"Detected {len(devices)} HackRF device(s).")

    def on_device_selected(self, event):
        from core import list_hackrf_devices, start_receiver
        selection = self.device_combobox.current()
        devices = list_hackrf_devices()
        if devices:
            if selection < len(devices):
                selected_device = devices[selection]
                self.device_index_var.set(selected_device['index'])
                self.status_var.set(f"Selected HackRF Device {selected_device['index']} - Serial: {selected_device['serial']}")
                print(f"Selected HackRF Device {selected_device['index']} - Serial: {selected_device['serial']}")

                # Restart the receiver with the new device index
                self.receiver_stop_event.set()
                self.receiver_thread.join()
                time.sleep(1)

                self.receiver_stop_event.clear()
                from core import start_receiver as sr
                self.receiver_thread = threading.Thread(
                    target=sr,
                    args=(self.receiver_stop_event, self.received_message_queue, self.device_index_var.get()),
                    daemon=True
                )
                self.receiver_thread.start()

                self.receiver_status_var.set("Receiver Running")
                self.status_var.set(f"Receiver restarted for device {selected_device['index']}.")
                print(f"Receiver restarted for device {selected_device['index']}.")
            else:
                self.status_var.set("Selected device index out of range.")
                print("Selected device index out of range.")
        else:
            self.device_index_var.set(0)
            self.status_var.set("No HackRF devices detected.")

    def update_hackrf_settings(self):
        try:
            gain = float(self.gain_entry.get())
            if_gain = float(self.if_gain_entry.get())
            self.gain_var.set(gain)
            self.if_gain_var.set(if_gain)
            self.status_var.set(f"HackRF settings updated: Gain={gain}, IF Gain={if_gain}")
            print(f"HackRF settings updated: Gain={gain}, IF Gain={if_gain}")
        except ValueError as ve:
            self.status_var.set(f"Invalid gain values: {ve}")
            print(f"Invalid gain values: {ve}")

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

        device_index = self.device_index_var.get()

        aprs_message = f"{callsign}>APRS:TEST 123!"
        self.message_queue.put((aprs_message, flags_before, flags_after, device_index))

        self.callsign_notification.config(text="Test message queued.", foreground="green")
        self.status_var.set(f"Test message queued with callsign: {aprs_message}")
        print(f"Test message queued with callsign: {aprs_message}, flags_before: {flags_before}, flags_after: {flags_after}, device_index: {device_index}")

    def validate_callsign(self, callsign):
        return 3 <= len(callsign) <= 6 and callsign.isalnum()

    def check_transmission_status(self):
        if self.transmitting_var.is_set():
            self.transmission_label.config(text="Transmitting", background="#28a745")
            if self.transmitting_icon:
                if not self.transmission_icon_label:
                    self.transmission_icon_label = ttk.Label(self.scrollable_frame, image=self.transmitting_icon)
                    self.transmission_icon_label.grid(row=5, column=4, sticky="w", padx=(10,0))
                else:
                    self.transmission_icon_label.config(image=self.transmitting_icon)
            self.progress.start(10)
            self.status_var.set("Transmitting...")
        else:
            self.transmission_label.config(text="Idle", background="#6c757d")
            if self.idle_icon:
                if not self.transmission_icon_label:
                    self.transmission_icon_label = ttk.Label(self.scrollable_frame, image=self.idle_icon)
                    self.transmission_icon_label.grid(row=5, column=4, sticky="w", padx=(10,0))
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
                self.messages_text.see('end')  # scroll to the end
        except queue.Empty:
            pass
        self.after(500, self.check_received_messages)
