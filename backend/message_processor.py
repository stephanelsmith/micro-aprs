# backend/message_processor.py

import asyncio
import logging
import threading
import queue
from typing import Any, Dict

import time

from backend.config_manager import ConfigurationManager
from backend.receiver import Receiver
from backend.carrier_transmission import CarrierTransmission

from core import generate_aprs_wav, add_silence, reset_hackrf, ResampleAndSend
from core.udp_transmitter import udp_transmitter

logger = logging.getLogger(__name__)

class MessageProcessor:
    def __init__(
        self,
        config_manager: ConfigurationManager,
        queues: Dict[str, Any],
        vars: Dict[str, Any],
        backend: Any  # Reference to Backend for emitting events
    ):
        self.config_manager = config_manager
        self.queues = queues
        self.vars = vars
        self.backend = backend  # Reference to Backend for emitting events
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self._start_event_loop, daemon=True).start()

    def _start_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

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
                self.backend.socketio.emit('carrier_status', {'status': 'active'})
                
                # Stop receiver if it's running
                if self.queues['receiver']:
                    self.queues['receiver'].stop()
                    self.queues['receiver_stop_event'].set()  # Signal receiver thread to stop
                    self.queues['receiver'] = None
                    logger.info("Receiver stopped before carrier transmission.")
                    self.backend.socketio.emit('reception_status', {'status': 'idle'})
                
                if self.queues.get('receiver_done_event'):
                    logger.info("Waiting for receiver thread to stop...")
                    self.queues['receiver_done_event'].wait()

                time.sleep(1)

                # Start carrier-only transmission if not already running
                if not self.queues.get('carrier_transmission'):
                    carrier_stop_event = threading.Event()
                    carrier_transmission = CarrierTransmission(
                        config=self.config_manager.config,
                        vars=self.vars,
                        stop_event=carrier_stop_event,
                        backend=self.backend  # Pass reference to Backend for emitting events
                    )
                    carrier_transmission.start()
                    self.queues['carrier_transmission'] = carrier_transmission
                    self.backend.socketio.emit('carrier_status', {'status': 'active'})
                return

            # Handle normal APRS message processing
            logger.info("Processing message: %s", aprs_message)

            # Generate WAV
            silence_before = 0
            silence_after = 0

            source_callsign = self.config_manager.get("callsign_source", "VE2FPD")
            destination_callsign = self.config_manager.get("callsign_dest", "VE2FPD")

            aprs_line = f"{source_callsign}>{destination_callsign}:{aprs_message}"

            # Schedule asynchronous WAV generation
            asyncio.run_coroutine_threadsafe(
                self._handle_wav_generation(aprs_line, flags_before, flags_after),
                self.loop
            )

            gain = self.vars['gain_var'].get()
            if_gain = self.vars['if_gain_var'].get()

            # Transmit
            reset_hackrf()

            # Stop receiver before transmission if it's running
            if self.queues['receiver']:
                self.queues['receiver'].stop()
                self.queues['receiver_stop_event'].set()  # Signal receiver thread to stop
                self.queues['receiver'] = None
                logger.info("Receiver stopped before transmission.")
                self.backend.socketio.emit('reception_status', {'status': 'idle'})
            
            if self.queues.get('receiver_done_event'):
                logger.info("Waiting for receiver thread to stop...")
                self.queues['receiver_done_event'].wait()
            
            # Initialize transmission
            tb = ResampleAndSend("processed_output.wav", 2205000, device_index=device_index)
            if tb.initialize_hackrf(gain, if_gain):
                current_frequency = self.vars['frequency_var'].get()
                tb.set_center_freq(current_frequency)
                self.vars['transmitting_var'].set()
                self.backend.socketio.emit('transmission_status', {'status': 'active'})
                tb.start()
                logger.info("Transmission started.")
                tb.wait()  # Wait for transmission to complete
                logger.info("Transmission done")
                tb.stop_and_wait()
                self.vars['transmitting_var'].clear()
                self.backend.socketio.emit('transmission_status', {'status': 'idle'})
                logger.info("Transmission stopped.")
            else:
                logger.error("HackRF initialization failed.")
                self.backend.socketio.emit('system_error', {'message': 'HackRF initialization failed.'})

            # Restart receiver
            if not self.queues.get('receiver'):
                receiver_stop_event = threading.Event()  # Make sure the stop event is reset here
                receiver = Receiver(
                    stop_event=receiver_stop_event,
                    message_queue=self.queues['received_message_queue'],
                    device_index=device_index,
                    frequency=self.vars['frequency_var'].get(),
                    backend=self.backend  # Pass reference to Backend for emitting events
                )
                receiver.start()
                self.queues['receiver'] = receiver  # Store the new receiver instance
                logger.info("Receiver thread restarted.")
                self.backend.socketio.emit('reception_status', {'status': 'active'})
            else:
                logger.info("Receiver is already running, not restarting.")

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
                # Emit the received message to the frontend
                self.backend.socketio.emit('aprs_message', {'message': received_message})
        except Exception as e:
            logger.info("Error in processing message")

    async def _handle_wav_generation(self, aprs_line: str, flags_before: int, flags_after: int):
        """
        Asynchronous handler for WAV generation.
        """
        try:
            await generate_aprs_wav(aprs_line, "raw_output.wav", flags_before, flags_after)
            add_silence("raw_output.wav", "processed_output.wav", 0, 0)
            logger.info("WAV files generated successfully.")
            self.backend.socketio.emit('wav_generation', {'status': 'completed'})
        except Exception as e:
            logger.exception("Error generating WAV files: %s", e)
            self.backend.socketio.emit('system_error', {'message': f"Error generating WAV files: {e}"})

    def restart_receiver(self):
        """ Restart the receiver by stopping and then restarting it. """
        logger.info("Restarting receiver...")

        # Stop the receiver if it's currently running
        if self.queues.get('receiver'):
            receiver = self.queues['receiver']
            receiver.stop()  # Stop the receiver thread
            self.queues['receiver_stop_event'].set()
            self.queues['receiver'] = None  # Clear the reference
            logger.info("Receiver stopped.")
            self.backend.socketio.emit('reception_status', {'status': 'idle'})

        # Start a new receiver instance
        receiver_stop_event = threading.Event()
        receiver = Receiver(
            stop_event=receiver_stop_event,
            message_queue=self.queues['received_message_queue'],
            device_index=self.config_manager.get("device_index", 0),
            frequency=self.vars['frequency_var'].get(),
            backend=self.backend  # Pass reference to Backend for emitting events
        )
        receiver.start()
        self.queues['receiver'] = receiver  # Store the new receiver instance
        logger.info("Receiver restarted.")
        self.backend.socketio.emit('reception_status', {'status': 'active'})
