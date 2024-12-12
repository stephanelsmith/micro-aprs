import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog
import logging
import threading
from backend import Backend

import time
import queue  # Import the queue module

logger = logging.getLogger(__name__)

class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        # Create a canvas and place a frame inside it
        self.canvas = tk.Canvas(self, borderwidth=0)
        self.scrollbar_y = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar_x = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.scrollable_frame = tk.Frame(self.canvas)

        # Configure the scrollable frame
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        # Create window inside the canvas
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Configure the canvas to use the scrollbars
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)

        # Layout the widgets
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.scrollbar_x.grid(row=1, column=0, sticky="ew")

        # Make the grid expandable
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

class RadioTransmissionApp:
    MAX_MESSAGES = 1000  # Maximum number of messages to retain

    def __init__(self, root):
        self.root = root
        self.root.title("Radio Transmission Application")

        # Set the minimum size of the window
        self.root.minsize(600, 400)

        # Bind the X button (window close) to quit_app
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

        # Create the ScrollableFrame
        self.scrollable_container = ScrollableFrame(self.root)
        self.scrollable_container.pack(fill="both", expand=True)

        # Reference to the interior frame
        self.frame = self.scrollable_container.scrollable_frame

        # Set up the GUI components inside the scrollable frame
        self.label = tk.Label(self.frame, text="Radio Transmission Application", font=("Arial", 16))
        self.label.pack(pady=10)

        # Transmission and reception status
        self.transmission_status = tk.Label(self.frame, text="Transmission: Idle", font=("Arial", 12), fg="green")
        self.transmission_status.pack(pady=5)

        self.reception_status = tk.Label(self.frame, text="Reception: Idle", font=("Arial", 12), fg="green")
        self.reception_status.pack(pady=5)

        # Buttons
        self.restart_button = tk.Button(self.frame, text="Restart Reception", command=self.restart_reception)
        self.restart_button.pack(pady=5)

        # Frame for displaying and editing configuration
        self.config_frame = tk.LabelFrame(self.frame, text="Current Configuration", padx=10, pady=10)
        self.config_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Dictionary to hold configuration input widgets
        self.config_widgets = {}

        # Initialize Backend
        self.backend = Backend("config.json")

        # Initialize a queue to receive APRS messages from the backend
        self.aprs_queue = queue.Queue()

        # Pass the queue to the backend so it can enqueue messages
        self.backend.set_aprs_queue(self.aprs_queue)

        # Display the current configuration with editable widgets
        self.display_config()

        # Frame for displaying received APRS messages
        self.received_frame = tk.LabelFrame(self.frame, text="Received APRS Messages", padx=10, pady=10)
        self.received_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Create a Text widget with a vertical scrollbar
        self.received_text = tk.Text(self.received_frame, wrap="word", height=15, state="disabled")
        self.received_text.pack(side="left", fill="both", expand=True)

        self.received_scrollbar = tk.Scrollbar(self.received_frame, command=self.received_text.yview)
        self.received_scrollbar.pack(side="right", fill="y")

        self.received_text.config(yscrollcommand=self.received_scrollbar.set)

        # Start polling the APRS message queue
        self.root.after(1000, self.poll_aprs_queue)  # Poll every second

        # Start background monitoring of backend status using root.after
        self.poll_backend_status()

    def display_config(self):
        """Display the current configuration in the config_frame with editable widgets."""
        # Clear existing widgets
        for widget in self.config_frame.winfo_children():
            widget.destroy()

        config = self.backend.config_manager.config

        # Define the configuration parameters to display with their labels and widget types
        config_params = [
            ("Frequency (Hz)", "frequency_hz", "entry"),
            ("Gain", "gain", "entry"),
            ("IF Gain", "if_gain", "entry"),
            ("Source Callsign", "callsign_source", "entry"),
            ("Destination Callsign", "callsign_dest", "entry"),
            ("Flags Before", "flags_before", "entry"),
            ("Flags After", "flags_after", "entry"),
            ("Send IP", "send_ip", "entry"),
            ("Send Port", "send_port", "entry"),
            ("Carrier Only", "carrier_only", "checkbox"),
            ("Device Index", "device_index", "entry"),
        ]

        for idx, (label_text, key, widget_type) in enumerate(config_params):
            # Label for the configuration key
            label_key = tk.Label(self.config_frame, text=label_text + ":", anchor="w", width=20, font=("Arial", 10, "bold"))
            label_key.grid(row=idx, column=0, sticky="w", pady=2, padx=5)

            if widget_type == "entry":
                # Entry widget for text/numeric input
                entry = tk.Entry(self.config_frame, width=30)
                entry.grid(row=idx, column=1, sticky="w", pady=2, padx=5)
                entry.insert(0, str(config.get(key, "")))
                self.config_widgets[key] = entry

            elif widget_type == "checkbox":
                # Boolean input using Checkbutton
                var = tk.BooleanVar()
                var.set(bool(config.get(key, False)))
                checkbox = tk.Checkbutton(self.config_frame, variable=var)
                checkbox.grid(row=idx, column=1, sticky="w", pady=2, padx=5)
                self.config_widgets[key] = var

        # Add Save Configuration button
        self.save_config_button = tk.Button(self.config_frame, text="Save Configuration", command=self.save_config)
        self.save_config_button.grid(row=len(config_params), column=0, columnspan=2, pady=10)

    def save_config(self):
        """Save the edited configuration and update the backend."""
        new_config = {}
        try:
            # Retrieve and validate input values
            new_config['frequency_hz'] = float(self.config_widgets['frequency_hz'].get())
            new_config['gain'] = float(self.config_widgets['gain'].get())
            new_config['if_gain'] = float(self.config_widgets['if_gain'].get())
            new_config['callsign_source'] = self.config_widgets['callsign_source'].get().strip()
            new_config['callsign_dest'] = self.config_widgets['callsign_dest'].get().strip()
            new_config['flags_before'] = int(self.config_widgets['flags_before'].get())
            new_config['flags_after'] = int(self.config_widgets['flags_after'].get())
            new_config['send_ip'] = self.config_widgets['send_ip'].get().strip()
            new_config['send_port'] = int(self.config_widgets['send_port'].get())
            new_config['carrier_only'] = self.config_widgets['carrier_only'].get()
            new_config['device_index'] = int(self.config_widgets['device_index'].get())
        except ValueError as ve:
            messagebox.showerror("Invalid Input", f"Please enter valid values:\n{ve}")
            logger.error(f"Invalid input when saving configuration: {ve}")
            return

        # Check for mandatory fields
        mandatory_fields = ['callsign_source', 'callsign_dest', 'send_ip']
        for field in mandatory_fields:
            if not new_config[field]:
                messagebox.showerror("Missing Field", f"The field '{field}' cannot be empty.")
                logger.error(f"Missing mandatory field: {field}")
                return

        # Update the config manager
        for key, value in new_config.items():
            self.backend.config_manager.set(key, value)

        # Save the updated config to file
        try:
            self.backend.config_manager.save_config()
            messagebox.showinfo("Config Updated", "Configuration has been updated and saved.")
            logger.info("Configuration updated successfully.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save configuration:\n{e}")
            logger.error(f"Error saving configuration: {e}")
            return
        
        # Refresh the config display
        self.refresh_config_display()

        # Restart the backend after config change
        self.restart_backend()

    def refresh_config_display(self):
        """Refresh the configuration display with the latest config values."""
        config = self.backend.config_manager.config
        for key, widget in self.config_widgets.items():
            config_value = config.get(key, "")
            
            if isinstance(widget, tk.Entry):
                current_value = widget.get()
                new_value = str(config_value)
                if current_value != new_value:
                    widget.delete(0, tk.END)
                    widget.insert(0, new_value)
            
            elif isinstance(widget, tk.BooleanVar):
                new_value = bool(config_value)
                if widget.get() != new_value:
                    widget.set(new_value)

    def start_backend(self):
        # Run Backend in a separate thread
        try:
            self.backend.run()
            messagebox.showinfo("Info", "Backend started successfully!")
            logger.info("Backend started successfully.")
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received. Exiting gracefully.")
            self.backend.shutdown()
            messagebox.showinfo("Info", "Backend stopped.")
        except Exception as e:
            logger.error(f"Error starting backend: {e}")
            messagebox.showerror("Backend Error", f"Failed to start backend:\n{e}")

    def quit_app(self):
        # Gracefully shut down the application
        if messagebox.askokcancel("Quit", "Are you sure you want to quit?"):
            self.backend.shutdown()
            self.root.quit()

    def update_status(self, type_, state):
        """
        Updates the status indicators for transmission and reception.
        """
        if type_ == "transmission":
            if state == "active":
                self.transmission_status.config(text="Transmission: Active", fg="red")
            else:
                self.transmission_status.config(text="Transmission: Idle", fg="green")
        
        elif type_ == "reception":
            if state == "active":
                self.reception_status.config(text="Reception: Active", fg="blue")
            else:
                self.reception_status.config(text="Reception: Idle", fg="green")

    def poll_backend_status(self):
        """Periodically check the backend status and update the GUI indicators."""
        # Check if transmission is active (based on 'transmitting_var')
        if self.backend.vars.get('transmitting_var') and self.backend.vars['transmitting_var'].is_set():
            self.update_status("transmission", "active")
        else:
            self.update_status("transmission", "idle")

        # Check if reception is active (based on the receiver's is_receiving status)
        receiver = self.backend.queues.get('receiver')
        if receiver and hasattr(receiver, 'is_receiving') and receiver.is_receiving:
            self.update_status("reception", "active")
        else:
            self.update_status("reception", "idle")

        # Schedule the next poll
        self.root.after(1000, self.poll_backend_status)  # Poll every second

    def poll_aprs_queue(self):
        """Poll the APRS message queue and display new messages."""
        try:
            while True:
                # Non-blocking get from the queue
                aprs_message = self.aprs_queue.get_nowait()
                self.display_aprs_message(aprs_message)
        except queue.Empty:
            pass
        finally:
            # Schedule the next poll
            self.root.after(1000, self.poll_aprs_queue)  # Poll every second

    def display_aprs_message(self, message):
        """Display a single APRS message in the text widget."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"

        # Enable the text widget, insert the message, and disable it again
        self.received_text.config(state="normal")
        self.received_text.insert("end", formatted_message)
        self.received_text.see("end")  # Scroll to the end

        # Enforce maximum message limit
        current_line_count = int(self.received_text.index('end-1c').split('.')[0])
        if current_line_count > self.MAX_MESSAGES:
            # Delete the oldest 100 messages to free up space
            self.received_text.delete("1.0", f"{self.MAX_MESSAGES//10}.0")

        self.received_text.config(state="disabled")

    def restart_reception(self):
        """ Restart the reception by calling the restart_receiver method in the backend. """
        logger.info("Restarting reception...")
        try:
            # Call the restart_receiver method of MessageProcessor to restart the receiver
            message_processor = self.backend.message_processor
            message_processor.restart_receiver()  # Restart the receiver
            messagebox.showinfo("Info", "Reception restarted successfully.")
            logger.info("Reception restarted successfully.")
        except AttributeError as ae:
            messagebox.showerror("Error", f"Failed to restart reception:\n{ae}")
            logger.error(f"Error restarting reception: {ae}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")
            logger.error(f"Unexpected error restarting reception: {e}")

    def restart_backend(self):
        """ Restart the backend after configuration change """
        logger.info("Restarting backend with new configuration...")

        try:
            # Stop transmission if it's running
            if self.backend.vars.get('transmitting_var') and self.backend.vars['transmitting_var'].is_set():
                # Stop the current transmission
                logger.info("Stopping transmission...")
                current_transmitter = self.backend.vars.get('transmitter_instance')  # Get the current transmitter instance

                if current_transmitter:
                    current_transmitter.stop_and_wait()  # Stop and wait for transmission to complete
                    self.backend.vars['transmitting_var'].clear()  # Clear the transmitting flag
                    logger.info("Transmission stopped.")
                else:
                    logger.warning("No active transmission instance found.")

            # Stop carrier transmission if it's running
            if self.backend.queues.get('carrier_transmission'):
                logger.info("Stopping carrier transmission...")
                carrier_transmission = self.backend.queues.get('carrier_transmission')
                
                if carrier_transmission:
                    carrier_transmission.stop()  # Stop the carrier transmission
                    self.backend.queues['carrier_transmission'] = None  # Clear the reference
                    logger.info("Carrier transmission stopped.")
                else:
                    logger.warning("No active carrier transmission instance found.")

            # Stop the receiver if it's running
            if self.backend.queues.get('receiver'):
                receiver = self.backend.queues['receiver']
                if hasattr(receiver, 'stop'):
                    receiver.stop()  # Stop the receiver
                    self.backend.queues['receiver'] = None  # Clear the reference
                    logger.info("Receiver stopped.")
                else:
                    logger.warning("Receiver does not have a stop method.")

            # Stop UDP listener if it's running
            if self.backend.udp_listener:
                if hasattr(self.backend.udp_listener, 'stop'):
                    self.backend.udp_listener.stop()  # Stop the UDP listener
                    self.backend.udp_listener = None  # Clear the reference
                    logger.info("UDP listener stopped.")
                else:
                    logger.warning("UDP listener does not have a stop method.")

            # Now reinitialize the backend with the new configuration
            self.backend = Backend(self.backend.config_manager.config_file)

            # Pass the existing APRS queue to the new backend instance
            self.backend.set_aprs_queue(self.aprs_queue)

            # Restart the backend components (receiver, UDP listener, transmitter) in new threads
            backend_thread = threading.Thread(target=self.backend.run, daemon=True)
            backend_thread.start()

            logger.info("Backend restarted successfully.")
            messagebox.showinfo("Backend Restarted", "Backend has been restarted with the new configuration.")

        except Exception as e:
            logger.error(f"Error restarting backend: {e}")
            messagebox.showerror("Backend Restart Error", f"Failed to restart backend:\n{e}")

def main():
    # Configure logging to write to a file
    logging.basicConfig(
        filename='radio_transmission_app.log',
        level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(message)s'
    )

    root = tk.Tk()
    app = RadioTransmissionApp(root)

    # Start the backend in a separate thread to keep the GUI responsive
    backend_thread = threading.Thread(target=app.start_backend, daemon=True)
    backend_thread.start()

    # Run the GUI event loop
    root.mainloop()

if __name__ == "__main__":
    main()
