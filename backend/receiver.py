# backend/receiver.py

import threading
import logging
from typing import Any, Dict
import queue  # Import the queue module

from core.udp_listener import udp_listener  # Assuming this is defined in core
from core import reset_hackrf, start_receiver

logger = logging.getLogger(__name__)

class Receiver:
    def __init__(self, stop_event: threading.Event, message_queue: queue.Queue, device_index: int, frequency: float):
        self.stop_event = stop_event
        self.message_queue = message_queue
        self.device_index = device_index
        self.frequency = frequency
        self.thread = threading.Thread(
            target=start_receiver,
            args=(self.stop_event, self.message_queue, self.device_index, self.frequency),
            daemon=True
        )

    def start(self):
        self.thread.start()
        logger.info("Receiver thread started on device %d at %.2f Hz.", self.device_index, self.frequency)

    def stop(self):
        logger.info("Stopping receiver thread...")
        self.stop_event.set()
        reset_hackrf()  # Ensure HackRF is reset before joining the thread
        if self.thread.is_alive():
            self.thread.join(timeout=5)  # Wait up to 5 seconds for the thread to finish
            if self.thread.is_alive():
                logger.warning("Receiver thread did not terminate within timeout.")
            else:
                logger.info("Receiver thread stopped successfully.")
        else:
            logger.info("Receiver thread was not running.")

