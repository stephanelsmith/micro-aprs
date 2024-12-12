# backend/backend.py

import threading
import logging
import sys
import queue  # Import the queue module
from typing import Any, Dict
import time

from backend.config_manager import ConfigurationManager
from backend.receiver import Receiver
from backend.udp_listener import UDPListenerThread
from backend.carrier_transmission import CarrierTransmission
from backend.message_processor import MessageProcessor

from core.thread_safe import ThreadSafeVariable  # Import ThreadSafeVariable

logger = logging.getLogger(__name__)

class Backend:
    def __init__(self, config_file: str):
        # Configuration Manager
        self.config_manager = ConfigurationManager(config_file)

        # Variables
        self.vars = {
            'frequency_var': ThreadSafeVariable(self.config_manager.get("frequency_hz", 28.12e6)),
            'gain_var': ThreadSafeVariable(self.config_manager.get("gain", 14)),
            'if_gain_var': ThreadSafeVariable(self.config_manager.get("if_gain", 47)),
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
            'carrier_transmission': None  # CarrierTransmission instance
        }

        # Initialize Message Processor
        self.message_processor = MessageProcessor(
            config_manager=self.config_manager,
            queues=self.queues,
            vars=self.vars
        )

        # Initialize Receiver
        if not hasattr(self, 'receiver') or self.queues['receiver'] is None:   
            self.receiver = Receiver(
                stop_event=self.queues['receiver_stop_event'],
                message_queue=self.queues['received_message_queue'],
                device_index=self.queues['device_index_var'].get(),
                frequency=self.vars['frequency_var'].get()
            )
            self.receiver.start()
            self.queues['receiver'] = self.receiver

        # Initialize UDP Listener
        if not hasattr(self, 'udp_listener') or self.udp_listener is None:
            self.udp_listener = UDPListenerThread(
                stop_event=self.queues['stop_event'],
                message_queue=self.queues['message_queue'],
                ip=self.config_manager.get('send_ip', "127.0.0.1"),
                port=self.config_manager.get('send_port', 14581)
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
                device_index=self.queues['device_index_var'].get(),
                frequency=self.vars['frequency_var'].get()
            )
            self.receiver.start()
            self.queues['receiver'] = self.receiver
            logger.info("Reception started.")
        else:
            logger.info("Receiver is already running.")

    def stop_reception(self):
        """ Stop the receiver thread. """
        if self.queues.get('receiver') is not None:
            self.queues['receiver'].stop()
            self.queues['receiver'] = None
            logger.info("Reception stopped.")
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

        # Stop UDP listener
        if self.udp_listener:
            self.udp_listener.stop()
            self.udp_listener = None

        # Stop receiver
        if self.queues.get('receiver'):
            self.queues['receiver'].stop()
            self.queues['receiver'] = None

        # Save configuration
        self.config_manager.save_config()

        logger.info("Shutdown complete.")
        sys.exit(0)

    def run(self):
        """
        Run the main processing loop.
        """
        try:
            while not self.queues['stop_event'].is_set():
                try:
                    message = self.queues['message_queue'].get_nowait()
                    self.message_processor.process_message(message)
                except queue.Empty:
                    pass
                except Exception as e:
                    logger.exception("Error in message processing: %s", e)
                time.sleep(0.1)  # Prevents CPU overuse
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received. Exiting gracefully.")
            self.shutdown()
