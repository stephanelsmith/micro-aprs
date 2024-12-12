# backend/udp_listener.py

import threading
import logging
import queue  # Import the queue module

from core.udp_listener import udp_listener  # Assuming this is defined in core

logger = logging.getLogger(__name__)

class UDPListenerThread:
    def __init__(
        self, 
        stop_event: threading.Event, 
        message_queue: queue.Queue, 
        ip: str, 
        port: int,
        backend: any  # Reference to Backend for emitting events
    ):
        """
        Initialize the UDPListenerThread.

        Args:
            stop_event (threading.Event): Event to signal the thread to stop.
            message_queue (queue.Queue): Queue to store received messages.
            ip (str): IP address to listen on.
            port (int): Port number to listen on.
            backend (Any): Reference to Backend for emitting events via socketio.
        """
        self.stop_event = stop_event
        self.message_queue = message_queue
        self.ip = ip
        self.port = port
        self.backend = backend  # Reference to Backend for emitting events
        self.thread = threading.Thread(
            target=self.udp_listener_thread,
            args=(self.ip, self.port, self.message_queue, self.stop_event),
            daemon=True
        )

    def udp_listener_thread(self, ip, port, message_queue, stop_event):
        """
        The thread function that handles listening to UDP messages.

        Args:
            ip (str): IP address to listen on.
            port (int): Port number to listen on.
            message_queue (queue.Queue): Queue to store received messages.
            stop_event (threading.Event): Event to signal the thread to stop.
        """
        logger.info(f"UDP Listener started on {ip}:{port}.")
        self.backend.socketio.emit('udp_listener_status', {'status': 'active'})
        try:
            udp_listener(ip, port, message_queue, stop_event)  # Assuming this function blocks and listens
        except Exception as e:
            logger.exception("UDP Listener encountered an error: %s", e)
            self.backend.socketio.emit('system_error', {'message': f"UDP Listener error: {e}"})
        finally:
            self.backend.socketio.emit('udp_listener_status', {'status': 'stopped'})
            logger.info(f"UDP Listener stopped on {ip}:{port}.")

    def start(self):
        """
        Start the UDP listener thread.
        """
        self.thread.start()
        logger.info("UDP listener thread started on %s:%d.", self.ip, self.port)
        self.backend.socketio.emit('udp_listener_status', {'status': 'active'})

    def stop(self):
        """
        Stop the UDP listener thread.
        """
        logger.info("Stopping UDP listener thread...")
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join()
            logger.info("UDP listener thread stopped successfully.")
            self.backend.socketio.emit('udp_listener_status', {'status': 'stopped'})
        else:
            logger.info("UDP listener thread was not running.")
