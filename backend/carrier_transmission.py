# backend/carrier_transmission.py

import threading
import time
import logging
from typing import Any, Dict  # Import Dict and Any from typing

from core import ResampleAndSend, reset_hackrf

logger = logging.getLogger(__name__)

class CarrierTransmission:
    def __init__(self, config: Dict[str, Any], vars: Dict[str, Any], stop_event: threading.Event, backend: Any):
        self.config = config
        self.vars = vars
        self.stop_event = stop_event
        self.backend = backend  # Store the backend reference
        self.thread = threading.Thread(target=self.start_carrier_transmission, daemon=True)

    def start(self):
        self.thread.start()
        logger.info("Carrier-only transmission thread started.")

    def start_carrier_transmission(self):
        try:
            gain = self.vars['gain_var'].get()
            if_gain = self.vars['if_gain_var'].get()
            current_frequency = self.vars['frequency_var'].get()

            carrier_top_block = ResampleAndSend(
                input_file=None,
                output_rate=2205000,
                device_index=self.config.get('device_index', 0),
                carrier_only=True,
                carrier_freq=current_frequency
            )

            if carrier_top_block.initialize_hackrf(gain, if_gain):
                carrier_top_block.set_center_freq(current_frequency)
                carrier_top_block.start()
                self.vars['transmitting_var'].set()
                logger.info("Carrier-only transmission started.")
                self.backend.socketio.emit('carrier_status', {'status': 'active'})

                # Wait until stop_event is set
                while not self.stop_event.is_set():
                    time.sleep(1)

                # Stop transmission
                carrier_top_block.stop_and_wait()
                self.vars['transmitting_var'].clear()
                logger.info("Carrier-only transmission stopped.")
                self.backend.socketio.emit('carrier_status', {'status': 'stopped'})
            else:
                logger.error("Failed to initialize HackRF for carrier-only mode.")
                self.backend.socketio.emit('system_error', {'message': "Failed to initialize HackRF for carrier-only mode."})
        except Exception as e:
            logger.exception("Error starting carrier-only mode: %s", e)
            self.backend.socketio.emit('system_error', {'message': f"Carrier Transmission error: {e}"})

    def stop(self):
        logger.info("Stopping Carrier Transmission...")
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join()
            logger.info("Carrier-only transmission thread stopped.")
