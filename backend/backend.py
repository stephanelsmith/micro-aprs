# backend/backend.py

import threading
import logging
import sys
import queue
import time
from typing import Any, Dict

from backend.config_manager import ConfigurationManager
from backend.receiver import Receiver
from backend.udp_listener import UDPListenerThread
from backend.carrier_transmission import CarrierTransmission
from backend.message_processor import MessageProcessor

from core.thread_safe import ThreadSafeVariable

logger = logging.getLogger(__name__)

class Backend:
    def __init__(self, config_file: str, socketio):
        # Configuration Manager
        self.config_manager = ConfigurationManager(config_file)
        
        self.lock = threading.Lock()

        # SocketIO instance for emitting events
        self.socketio = socketio

        # Variables
        self.vars = {
            'frequency_var': ThreadSafeVariable(self.config_manager.get("frequency_hz", 28.12e6)),
            'gain_var': ThreadSafeVariable(self.config_manager.get("gain", 14)),
            'if_gain_var': ThreadSafeVariable(self.config_manager.get("if_gain", 47)),
            'device_index_var': ThreadSafeVariable(self.config_manager.get("device_index", 0)),  # Ensure this line is present
            'transmitting_var': threading.Event()
        }

        # Queues and Events
        self.queues = {
            'stop_event': threading.Event(),
            'transmitting_var': self.vars['transmitting_var'],
            'message_queue': queue.SimpleQueue(),
            'frequency_var': self.vars['frequency_var'],
            'gain_var': self.vars['gain_var'],
            'if_gain_var': self.vars['if_gain_var'],
            'receiver_stop_event': threading.Event(),
            'receiver': None,  # Receiver instance
            'received_message_queue': queue.Queue(),
            'device_index_var': ThreadSafeVariable(self.config_manager.get("device_index", 0)),
            'carrier_stop_event': threading.Event(),
            'carrier_transmission': None,  # CarrierTransmission instance
            'udp_listener_stop_event': threading.Event(),  # Added for UDP Listener
            'udp_listener': None  # UDPListenerThread instance
        }

        # Initialize Message Processor
        self.message_processor = MessageProcessor(
            config_manager=self.config_manager,
            queues=self.queues,
            vars=self.vars,
            backend=self  # Pass reference to Backend for emitting events
        )

        # Initialize Receiver
        if not hasattr(self, 'receiver') or self.queues['receiver'] is None:   
            self.receiver = Receiver(
                stop_event=self.queues['receiver_stop_event'],
                message_queue=self.queues['received_message_queue'],
                device_index=self.queues['device_index_var'].get(),
                frequency=self.vars['frequency_var'].get(),
                backend=self  # Pass reference to Backend for emitting events
            )
            self.receiver.start()
            self.queues['receiver'] = self.receiver

        # Initialize UDP Listener
        if not hasattr(self, 'udp_listener') or self.queues['udp_listener'] is None:
            self.udp_listener = UDPListenerThread(
                stop_event=self.queues['udp_listener_stop_event'],
                message_queue=self.queues['message_queue'],
                ip=self.config_manager.get('send_ip', "127.0.0.1"),
                port=self.config_manager.get('send_port', 14581),
                backend=self  # Pass reference to Backend for emitting events
            )
            self.udp_listener.start()

        # Initialize Carrier Transmission if enabled in config
        if self.config_manager.get("carrier_only", False):
            logger.info("Carrier-only mode enabled in configuration. Queuing CARRIER_ONLY message.")
            self.queues['message_queue'].put("CARRIER_ONLY")

    def set_aprs_queue(self, aprs_queue: queue.Queue):
        """
        Set the queue to which received APRS messages will be sent.
        """
        self.queues['received_message_queue'] = aprs_queue
        logger.info("APRS message queue has been set.")

    def handle_signal(self, signum: int, frame: Any):
        """
        Handle termination signals for graceful shutdown.
        """
        logger.info("Signal %d received. Initiating shutdown...", signum)
        self.shutdown()

    def start_reception(self):
        """ Start the receiver thread. """
        if self.queues['receiver'] is None or not self.queues['receiver'].is_alive():
            self.receiver = Receiver(
                stop_event=self.queues['receiver_stop_event'],
                message_queue=self.queues['received_message_queue'],
                device_index=self.vars['device_index_var'].get(),
                frequency=self.vars['frequency_var'].get(),
                backend=self  # Pass reference to Backend for emitting events
            )
            self.receiver.start()
            self.queues['receiver'] = self.receiver
            logger.info("Reception started.")
            self.socketio.emit('reception_status', {'status': 'active'})
        else:
            logger.info("Receiver is already running.")

    def stop_reception(self):
        """ Stop the receiver thread. """
        if self.queues.get('receiver') is not None:
            self.queues['receiver'].stop()
            self.queues['receiver_stop_event'].set()  # Signal receiver thread to stop
            self.queues['receiver'] = None
            logger.info("Reception stopped.")
            self.socketio.emit('reception_status', {'status': 'idle'})
        else:
            logger.info("Receiver is not running.")
                
    def shutdown(self):
        """
        Perform a graceful shutdown of all components.
        """
        logger.info("Shutting down...")

        # Stop carrier transmission if running
        if self.queues.get('carrier_transmission'):
            self.queues['carrier_transmission'].stop()
            self.queues['carrier_transmission'] = None
            self.socketio.emit('carrier_status', {'status': 'stopped'})

        # Stop UDP listener
        if self.queues.get('udp_listener'):
            self.queues['udp_listener'].stop()
            self.queues['udp_listener'] = None
            self.socketio.emit('udp_listener_status', {'status': 'stopped'})

        # Stop UDP listener events
        if self.queues.get('udp_listener_stop_event'):
            self.queues['udp_listener_stop_event'].set()

        # Stop receiver
        if self.queues.get('receiver'):
            self.queues['receiver'].stop()
            self.queues['receiver_stop_event'].set()
            self.queues['receiver'] = None
            self.socketio.emit('reception_status', {'status': 'stopped'})

        # Save configuration
        self.config_manager.save_config()

        logger.info("Shutdown complete.")
        sys.exit(0)

    def apply_new_config(self, new_config: Dict[str, Any]) -> None:
        """
        Apply new configuration by updating variables and restarting components if necessary.

        Args:
            new_config (Dict[str, Any]): A dictionary containing the new configuration parameters.
        """
        # Acquire the lock to ensure thread safety
        with self.lock:
            # Make a copy of the current configuration to compare later
            old_config = self.config_manager.config.copy()

            # Update the configuration manager with the new configuration
            self.config_manager.update_config(new_config)
            self.config_manager.save_config()

            # === Handle Frequency Change ===
            if 'frequency_hz' in new_config and new_config['frequency_hz'] != old_config.get('frequency_hz'):
                new_freq = new_config['frequency_hz']
                self.vars['frequency_var'].set(new_freq)
                logger.info("Frequency updated to %s Hz.", new_freq)

                # Restart Receiver to apply the new frequency
                if self.queues['receiver']:
                    # Stop the receiver if it's currently running
                    if self.queues.get('receiver'):
                        receiver = self.queues['receiver']
                        receiver.stop()  # Stop the receiver thread
                        self.queues['receiver_stop_event'].set()
                        self.queues['receiver'] = None  # Clear the reference
                        logger.info("Receiver stopped.")

                    # Start a new receiver instance
                    receiver_stop_event = threading.Event()
                    receiver = Receiver(
                        stop_event=receiver_stop_event,
                        message_queue=self.queues['received_message_queue'],
                        device_index=self.config_manager.get("device_index", 0),
                        frequency=self.vars['frequency_var'].get(),
                        backend=self  # Pass reference to Backend for emitting events
                    )
                    receiver.start()
                    self.queues['receiver'] = receiver  # Store the new receiver instance
                    logger.info("Receiver restarted.")

            # === Handle Device Index Change ===
            if 'device_index' in new_config and new_config['device_index'] != old_config.get('device_index'):
                new_device_index = new_config['device_index']
                self.vars['device_index_var'].set(new_device_index)
                logger.info("Device index updated to %s.", new_device_index)


                # Restart Receiver to apply the new frequency
                if self.queues['receiver']:
                    # Stop the receiver if it's currently running
                    if self.queues.get('receiver'):
                        receiver = self.queues['receiver']
                        receiver.stop()  # Stop the receiver thread
                        self.queues['receiver_stop_event'].set()
                        self.queues['receiver'] = None  # Clear the reference
                        logger.info("Receiver stopped.")

                    # Start a new receiver instance
                    receiver_stop_event = threading.Event()
                    receiver = Receiver(
                        stop_event=receiver_stop_event,
                        message_queue=self.queues['received_message_queue'],
                        device_index=self.config_manager.get("device_index", 0),
                        frequency=self.vars['frequency_var'].get(),
                        backend=self  # Pass reference to Backend for emitting events
                    )
                    receiver.start()
                    self.queues['receiver'] = receiver  # Store the new receiver instance
                    logger.info("Receiver restarted.")

            # === Handle Send IP or Send Port Change ===
            send_ip_changed = 'send_ip' in new_config and new_config['send_ip'] != old_config.get('send_ip')
            send_port_changed = 'send_port' in new_config and new_config['send_port'] != old_config.get('send_port')
            
            if send_ip_changed or send_port_changed:
                new_ip = new_config.get('send_ip', self.config_manager.get('send_ip'))
                new_port = new_config.get('send_port', self.config_manager.get('send_port'))
                logger.info("Send IP or Port changed. New IP: %s, New Port: %s.", new_ip, new_port)

                # Restart UDP Listener with new IP and/or Port
                if self.queues['udp_listener']:
                    self.queues['udp_listener'].stop()
                    self.queues['udp_listener_stop_event'].set()
                    logger.info("UDP Listener stopped.")

                # Create and start a new UDP Listener instance
                self.queues['udp_listener'] = UDPListenerThread(
                    stop_event=self.queues['udp_listener_stop_event'],
                    message_queue=self.queues['message_queue'],
                    ip=new_ip,
                    port=new_port,
                    backend=self  # Pass reference to Backend for emitting events
                )
                self.queues['udp_listener'].start()
                logger.info("UDP Listener restarted with IP: %s and Port: %s.", new_ip, new_port)
                self.socketio.emit('udp_listener_status', {'status': 'active'})

            # === Handle Gain Change ===
            if 'gain' in new_config and new_config['gain'] != old_config.get('gain'):
                new_gain = new_config['gain']
                self.vars['gain_var'].set(new_gain)
                logger.info("Gain updated to %s.", new_gain)
                # If gain affects other components dynamically, update them here

            # === Handle IF Gain Change ===
            if 'if_gain' in new_config and new_config['if_gain'] != old_config.get('if_gain'):
                new_if_gain = new_config['if_gain']
                self.vars['if_gain_var'].set(new_if_gain)
                logger.info("IF Gain updated to %s.", new_if_gain)
                # If IF Gain affects other components dynamically, update them here

            # === Handle Carrier Only Change ===
            if 'carrier_only' in new_config and new_config['carrier_only'] != old_config.get('carrier_only'):
                carrier_only = new_config['carrier_only']
                logger.info("Carrier Only setting changed to %s.", carrier_only)

                if carrier_only:
                    # Start Carrier Transmission if not already running
                    if not self.queues.get('carrier_transmission'):
                        carrier_stop_event = threading.Event()
                        self.queues['carrier_transmission'] = CarrierTransmission(
                            config=self.config_manager.config,
                            vars=self.vars,
                            stop_event=carrier_stop_event,
                            backend=self
                        )
                        self.queues['carrier_transmission'].start()
                        logger.info("Carrier Transmission started.")
                        self.socketio.emit('carrier_status', {'status': 'active'})
                else:
                    # Stop Carrier Transmission if it's running
                    if self.queues.get('carrier_transmission'):
                        self.queues['carrier_transmission'].stop()
                        self.queues['carrier_transmission'] = None
                        logger.info("Carrier Transmission stopped.")
                        self.socketio.emit('carrier_status', {'status': 'stopped'})

            # === Handle Other Configuration Parameters (e.g., Callsigns, Flags) ===
            # These typically don't require restarting backend components
            # They are already updated in config_manager, so ensure components use the updated config as needed

            # === Final Logging ===
            logger.info("Configuration applied successfully.")



    def run(self):
        """
        Run the main processing loop.
        """
        try:
            self.socketio.emit('system_status', {'status': 'running'})
            while not self.queues['stop_event'].is_set():
                try:
                    message = self.queues['message_queue'].get_nowait()
                    self.message_processor.process_message(message)
                except queue.Empty:
                    pass
                except Exception as e:
                    logger.exception("Error in message processing: %s", e)
                    self.socketio.emit('system_error', {'message': f"Message processing error: {e}"})
                time.sleep(0.1)  # Prevents CPU overuse
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received. Exiting gracefully.")
            self.shutdown()
