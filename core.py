import threading
import asyncio
import socket
import queue
import wave
import struct
import subprocess

# Try to import external dependencies, handle ImportError gracefully
try:
    from gnuradio import gr, blocks, filter
    from osmosdr import sink
except ImportError as e:
    print(f"Warning: Could not import GNU Radio modules. Some functionality may be limited. {e}")
    gr = None  # Set to None to prevent errors if used
    blocks = None
    filter = None
    sink = None

try:
    from afsk.mod import AFSKModulator
    from ax25.ax25 import AX25
except ImportError as e:
    print(f"Warning: Could not import AFSK or AX.25 modules. Some functionality may be limited. {e}")
    AFSKModulator = None
    AX25 = None

# Reset HackRF
def reset_hackrf():
    """Reset the HackRF device."""
    subprocess.run(["hackrf_transfer", "-r", "/dev/null"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["hackrf_transfer", "-t", "/dev/null"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("HackRF reset completed.")

# Add silence to WAV
def add_silence(input_wav, output_wav, silence_duration_before, silence_duration_after):
    """Add silence before and after a WAV file."""
    with wave.open(input_wav, 'rb') as wav_in:
        params = wav_in.getparams()
        sample_rate = wav_in.getframerate()
        num_channels = wav_in.getnchannels()
        sampwidth = wav_in.getsampwidth()

        audio_frames = wav_in.readframes(wav_in.getnframes())

    num_silence_frames_before = int(silence_duration_before * sample_rate)
    num_silence_frames_after = int(silence_duration_after * sample_rate)

    silence_before = (b'\x00' * sampwidth * num_channels) * num_silence_frames_before
    silence_after = (b'\x00' * sampwidth * num_channels) * num_silence_frames_after

    new_frames = silence_before + audio_frames + silence_after

    with wave.open(output_wav, 'wb') as wav_out:
        wav_out.setparams(params)
        wav_out.writeframes(new_frames)

# GNU Radio class
if gr is not None:
    class ResampleAndSend(gr.top_block):
        def __init__(self, input_file, output_rate):
            gr.top_block.__init__(self, "Resample and Send")

            self.file_source = blocks.wavfile_source(input_file, repeat=False)
            self.resampler = filter.rational_resampler_fff(interpolation=int(output_rate), decimation=22050)
            self.amplitude_scaling = blocks.multiply_const_ff(0.05)
            self.float_to_complex = blocks.float_to_complex()
            self.sink = None
            self.output_rate = output_rate

            self.connect(self.file_source, self.resampler)
            self.connect(self.resampler, self.amplitude_scaling)
            self.connect(self.amplitude_scaling, self.float_to_complex)

        def initialize_hackrf(self, gain, if_gain):
            """Initialize HackRF sink."""
            try:
                print("Initializing HackRF...")
                self.sink = sink(args="hackrf=1")
                self.sink.set_sample_rate(self.output_rate)
                self.sink.set_center_freq(144.39e6)  # Will be set later in main_loop
                self.sink.set_gain(gain)
                self.sink.set_if_gain(if_gain)
                self.sink.set_bb_gain(20)
                self.sink.set_antenna("TX/RX")
                print("HackRF initialized successfully.")
                self.connect(self.float_to_complex, self.sink)
                return True
            except RuntimeError as e:
                print(f"Error initializing HackRF: {e}")
                return False

        def stop_and_wait(self):
            """Gracefully stop the flowgraph."""
            try:
                self.disconnect_all()
            except Exception as e:
                print(f"Error during disconnect: {e}")
            self.stop()
            self.wait()
else:
    # Provide a dummy class if gr is not available
    class ResampleAndSend:
        def __init__(self, input_file, output_rate):
            print("Warning: GNU Radio is not available. ResampleAndSend functionality is disabled.")

        def initialize_hackrf(self):
            print("Warning: Cannot initialize HackRF without GNU Radio.")
            return False

        def stop_and_wait(self):
            pass

# Generate APRS WAV
async def generate_aprs_wav(aprs_message, output_wav, flags_before=10, flags_after=4):
    """Generate a WAV file from an APRS message."""
    if AFSKModulator is None or AX25 is None:
        print("Warning: AFSKModulator or AX25 is not available. Cannot generate APRS WAV.")
        return

    print(f"Generating APRS WAV for message: {aprs_message}")
    rate = 22050
    try:
        async with AFSKModulator(sampling_rate=rate, verbose=False) as afsk_mod:
            ax25 = AX25(aprs=aprs_message.encode())
            afsk, stop_bit = ax25.to_afsk()
            await afsk_mod.send_flags(flags_before)
            await afsk_mod.to_samples(afsk=afsk, stop_bit=stop_bit)
            await afsk_mod.send_flags(flags_after)
            arr, s = await afsk_mod.flush()

            with wave.open(output_wav, 'wb') as wav_out:
                wav_out.setnchannels(1)
                wav_out.setsampwidth(2)
                wav_out.setframerate(rate)
                for i in range(s):
                    samp = struct.pack('<h', arr[i])
                    wav_out.writeframesraw(samp)
        print(f"WAV file successfully generated: {output_wav}")
    except Exception as e:
        print(f"Error generating APRS WAV: {e}")


# UDP Listener
def udp_listener(host, port, message_queue, stop_event):
    """Listen for APRS messages over UDP and add them to the message queue."""
    print(f"Starting UDP listener on {host}:{port}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((host, port))
            sock.settimeout(0.5)
            while not stop_event.is_set():
                try:
                    data, addr = sock.recvfrom(1024)
                    aprs_message = data.decode().strip()
                    print(f"Received UDP message from {addr}: {aprs_message}")
                    message_queue.put(aprs_message)
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error in UDP listener: {e}")
    except Exception as e:
        print(f"UDP listener error: {e}")

# Frequency Wrapper
class Frequency:
    """A thread-safe wrapper for the frequency variable."""
    def __init__(self, initial_value):
        self._value = initial_value
        self._lock = threading.Lock()

    def get(self):
        with self._lock:
            return self._value

    def set(self, value):
        with self._lock:
            self._value = value

class ThreadSafeVariable:
    """A thread-safe wrapper for any variable."""
    def __init__(self, initial_value):
        self._value = initial_value
        self._lock = threading.Lock()
    
    def get(self):
        with self._lock:
            return self._value
    
    def set(self, value):
        with self._lock:
            self._value = value
