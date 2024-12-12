# backend/udp_listener.py

import threading
import logging
import queue  # Import the queue module

from core.udp_listener import udp_listener  # Assuming this is defined in core

logger = logging.getLogger(__name__)

class UDPListenerThread:
    def __init__(self, stop_event: threading.Event, message_queue: queue.Queue, ip: str, port: int):
        self.stop_event = stop_event
        self.message_queue = message_queue
        self.ip = ip
        self.port = port
        self.thread = threading.Thread(
            target=udp_listener,
            args=(self.ip, self.port, self.message_queue, self.stop_event),
            daemon=True
        )

    def start(self):
        self.thread.start()
        logger.info("UDP listener started on %s:%d.", self.ip, self.port)

    def stop(self):
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join()
            logger.info("UDP listener thread stopped.")
