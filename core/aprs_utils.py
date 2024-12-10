import wave
import struct
import asyncio

# Try importing AFSK/AX.25
try:
    from afsk.mod import AFSKModulator
    from ax25.ax25 import AX25
except ImportError as e:
    print(f"Warning: Could not import AFSK or AX.25 modules: {e}")
    AFSKModulator = None
    AX25 = None

async def generate_aprs_wav(aprs_message, output_wav, flags_before=10, flags_after=4):
    """Generate a WAV file from an APRS message."""
    if AFSKModulator is None or AX25 is None:
        print("AFSKModulator or AX25 not available. Cannot generate APRS WAV.")
        return

    rate = 22050
    print(f"Generating APRS WAV for message: {aprs_message}")
    try:
        async with AFSKModulator(sampling_rate=rate, verbose=False) as afsk_mod:
            ax25_frame = AX25(aprs=aprs_message.encode())
            afsk, stop_bit = ax25_frame.to_afsk()
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
