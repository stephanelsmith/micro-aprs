from gnuradio import gr, blocks, filter, analog
from gnuradio.filter import firdes
import osmosdr

class ResampleAndSend(gr.top_block):
    def __init__(self, input_file, output_rate, device_index=0, carrier_only=False, carrier_freq=28.12e6):
        gr.top_block.__init__(self, "Resample and Send")

        self.output_rate = output_rate
        self.device_index = device_index
        self.carrier_only = carrier_only
        self.carrier_freq = carrier_freq
        self.sink = None

        # Source: Read from WAV file or generate carrier signal
        if not self.carrier_only:
            # Mode standard: Lecture du fichier WAV
            self.file_source = blocks.wavfile_source(input_file, repeat=False)
            # Resample from 22050 Hz to output_rate (e.g., 2.205 MHz)
            self.resampler = filter.rational_resampler_fff(
                interpolation=int(output_rate), 
                decimation=22050
            )
            # Scale amplitude down to avoid overdriving the transmitter
            self.amplitude_scaling = blocks.multiply_const_ff(0.05)
            # Convert float samples to complex for HackRF sink
            self.float_to_complex = blocks.float_to_complex()

            # Connect the flowgraph
            self.connect(self.file_source, self.resampler)
            self.connect(self.resampler, self.amplitude_scaling)
            self.connect(self.amplitude_scaling, self.float_to_complex)
        else:
            # Mode "Carrier Only": Génération d'un signal porteur pur
            self.constant_source = analog.sig_source_f(0, analog.GR_CONST_WAVE, 0, 0, 1)
            # Convert float samples to complex for HackRF sink
            self.float_to_complex = blocks.float_to_complex()

            # Connect the carrier signal to float to complex
            self.connect(self.constant_source, self.float_to_complex)

    def initialize_hackrf(self, gain, if_gain):
        try:
            print(f"Initializing HackRF device {self.device_index}...")
            self.sink = osmosdr.sink(args=f"hackrf={self.device_index}")
            self.sink.set_sample_rate(self.output_rate)
            self.sink.set_center_freq(28.12e6, 0)  # Adjust frequency as needed
            self.sink.set_gain(gain, 0)
            self.sink.set_if_gain(if_gain, 0)
            self.sink.set_bb_gain(20, 0)
            self.sink.set_antenna("TX/RX", 0)
            print("HackRF initialized successfully.")

            # Connect the flowgraph to HackRF sink
            self.connect(self.float_to_complex, self.sink)
            return True
        except RuntimeError as e:
            print(f"Error initializing HackRF: {e}")
            return False

    def set_center_freq(self, freq_hz):
        if self.sink:
            self.sink.set_center_freq(freq_hz, 0)
            print(f"Center frequency set to {freq_hz / 1e6} MHz.")

    def stop_and_wait(self):
        try:
            # Only disconnect what we know is connected:
            if self.sink:
                print("Disconnecting HackRF sink...")
                self.disconnect(self.float_to_complex, self.sink)
                self.sink = None

            print("Stopping the flowgraph...")
            self.stop()
            print("Waiting for the flowgraph to terminate...")
            self.wait()
            print("Flowgraph stopped and resources released.")
        except Exception as e:
            print(f"Error during stop and wait: {e}")