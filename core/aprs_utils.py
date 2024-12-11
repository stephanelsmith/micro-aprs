import wave
import struct
import asyncio
import logging
import numpy as np

# Try importing AFSK/AX.25
try:
    from afsk.mod import AFSKModulator
    from ax25.ax25 import AX25
except ImportError as e:
    print(f"Warning: Could not import AFSK or AX.25 modules: {e}")
    AFSKModulator = None
    AX25 = None


logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG level for detailed output
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("aprs_wav_generation.log"),
        logging.StreamHandler()
    ]
)

async def generate_aprs_wav(aprs_message, output_wav, flags_before=10, flags_after=4):
    """Generate a WAV file from an APRS message."""
    if AFSKModulator is None or AX25 is None:
        logging.error("AFSKModulator or AX25 not available. Cannot generate APRS WAV.")
        return

    rate = 22050  # Sample rate in Hz
    logging.info(f"Generating APRS WAV for message: {aprs_message}")
    try:
        async with AFSKModulator(sampling_rate=rate, verbose=False) as afsk_mod:

            ax25_frame = AX25(aprs=aprs_message.encode())
            afsk, stop_bit = ax25_frame.to_afsk()
            
            await afsk_mod.send_flags(flags_before)
            await afsk_mod.to_samples(afsk=afsk, stop_bit=stop_bit)
            await afsk_mod.send_flags(flags_after)
            arr, s = await afsk_mod.flush()

            # Convert arr to a NumPy array for efficient processing
            arr = np.array(arr, dtype=np.float32)

            # Log the data type and range of audio samples before processing
            logging.debug(f"Audio data type before processing: {arr.dtype}")
            logging.debug(f"Audio sample range before processing: {arr.min()} to {arr.max()}")

            # Check for NaNs or Infs in the audio data
            if np.isnan(arr).any() or np.isinf(arr).any():
                logging.error("Audio samples contain NaN or Inf values.")
                raise ValueError("Invalid audio samples detected.")

            # Normalize the audio signal if necessary
            max_val = np.max(np.abs(arr))
            if max_val == 0:
                logging.warning("Maximum audio value is 0. Skipping normalization.")
                audio_normalized = arr
            elif max_val > 32767:
                scaling_factor = 32767 / max_val
                audio_normalized = arr * scaling_factor
                logging.debug(f"Audio normalized by scaling factor: {scaling_factor}")
            else:
                audio_normalized = arr
                logging.debug("Audio normalization not required.")

            # Clip the audio samples to the int16 range
            audio_clipped = np.clip(audio_normalized, -32768, 32767)

            # Log the range after normalization and clipping
            logging.debug(f"Audio sample range after normalization and clipping: {audio_clipped.min()} to {audio_clipped.max()}")

            # Convert to int16
            audio_int16 = audio_clipped.astype(np.int16)

            # Final check to ensure no overflow
            if np.any(audio_int16 > 32767) or np.any(audio_int16 < -32768):
                logging.error("Audio samples exceed int16 range after processing.")
                raise ValueError("Audio samples exceed int16 range after processing.")

            # Write to WAV file in bulk
            with wave.open(output_wav, 'wb') as wav_out:
                wav_out.setnchannels(1)        # Mono
                wav_out.setsampwidth(2)        # 2 bytes per sample (int16)
                wav_out.setframerate(rate)     # Sample rate
                wav_out.writeframes(audio_int16.tobytes())

            logging.info(f"WAV file successfully generated: {output_wav}")
    except Exception as e:
        logging.error(f"Error generating APRS WAV: {e}")


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
