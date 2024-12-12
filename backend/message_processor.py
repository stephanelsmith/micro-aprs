# backend/message_processor.py

import asyncio
import logging
import threading  # Ensure threading is imported if used
import queue       # Import the queue module
from typing import Any, Dict

import time

from backend.config_manager import ConfigurationManager  # Import ConfigurationManager
from backend.receiver import Receiver                  # Import Receiver
from backend.carrier_transmission import CarrierTransmission  # Import CarrierTransmission

from core import generate_aprs_wav, add_silence, reset_hackrf, ResampleAndSend
from core.udp_transmitter import udp_transmitter

logger = logging.getLogger(__name__)

class MessageProcessor:
    def __init__(self, config_manager: ConfigurationManager, queues: Dict[str, Any], vars: Dict[str, Any]):
        self.config_manager = config_manager
        self.queues = queues
        self.vars = vars

    def process_message(self, message: Any) -> None:
        """
        Process and transmit the APRS message.
        """
        try:
            if isinstance(message, tuple) and len(message) == 5:
                aprs_message, flags_before, flags_after, device_index, carrier_only = message
            else:
                aprs_message = message
                flags_before = self.config_manager.get("flags_before", 10)
                flags_after = self.config_manager.get("flags_after", 4)
                device_index = self.config_manager.get("device_index", 0)
                carrier_only = self.config_manager.get("carrier_only", False)

            if carrier_only:
                # Initiate carrier-only transmission
                logger.info("Initiating carrier-only transmission.")
                # Stop receiver if it's running
                if self.queues['receiver']:
                    self.queues['receiver'].stop()
                    self.queues['receiver'] = None
                    logger.info("Receiver stopped before carrier transmission.")

                # Start carrier-only transmission if not already running
                if not self.queues.get('carrier_transmission'):
                    carrier_stop_event = threading.Event()
                    carrier_transmission = CarrierTransmission(
                        config=self.config_manager.config,
                        vars=self.vars,
                        stop_event=carrier_stop_event
                    )
                    carrier_transmission.start()
                    self.queues['carrier_transmission'] = carrier_transmission
                return

            # Handle normal APRS message processing
            logger.info("Processing message: %s", aprs_message)

            # Generate WAV
            silence_before = 0
            silence_after = 0

            source_callsign = self.config_manager.get("callsign_source", "VE2FPD")
            destination_callsign = self.config_manager.get("callsign_dest", "VE2FPD")

            aprs_line = f"{source_callsign}>{destination_callsign}:{aprs_message}"

            asyncio.run(generate_aprs_wav(aprs_line, "raw_output.wav", flags_before, flags_after))
            add_silence("raw_output.wav", "processed_output.wav", silence_before, silence_after)

            gain = self.vars['gain_var'].get()
            if_gain = self.vars['if_gain_var'].get()

            # Transmit
            reset_hackrf()
            if self.queues['receiver']:
                self.queues['receiver'].stop()
                self.queues['receiver'] = None
                logger.info("Receiver stopped before carrier transmission.")
            time.sleep(1)
            tb = ResampleAndSend("processed_output.wav", 2205000, device_index=device_index)
            if tb.initialize_hackrf(gain, if_gain):
                current_frequency = self.vars['frequency_var'].get()
                tb.set_center_freq(current_frequency)
                self.vars['transmitting_var'].set()
                tb.start()
                logger.info("Transmission started.")
                time.sleep(5)
                tb.stop_and_wait()
                self.vars['transmitting_var'].clear()
                logger.info("Transmission stopped.")
            else:
                logger.error("HackRF initialization failed.")

            # Restart receiver
            #if not self.queues.get('receiver'):
            receiver = Receiver(
                stop_event=self.queues['receiver_stop_event'],
                message_queue=self.queues['received_message_queue'],
                device_index=device_index,
                frequency=self.vars['frequency_var'].get()
            )
            receiver.start()
            self.queues['receiver'] = receiver
            logger.info("Receiver thread restarted.")

            # Handle received messages
            while not self.queues['received_message_queue'].empty():
                received_message = self.queues['received_message_queue'].get()
                udp_transmitter(
                    self.config_manager.get('send_ip'),
                    self.config_manager.get('send_port'),
                    received_message
                )
                logger.info(
                    "Received message transmitted to %s:%d: %s",
                    self.config_manager.get('send_ip'),
                    self.config_manager.get('send_port'),
                    received_message
                )

        except Exception as e:
            logger.exception("Error processing message: %s", e)
