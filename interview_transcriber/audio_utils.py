from pydub import AudioSegment


def get_wav_path(audio_path):
    _, ext = os.path.splitext(audio_path)
    ext = ext.lower()

    if ext == ".wav":
        # If the file is already in WAV format, return the original path
        return audio_path
    elif ext == ".mp3":
        # If the file is in MP3 format, create a temporary WAV file
        # Convert MP3 to WAV using pydub
        wav_path = audio_path.replace(".mp3", ".wav")
        sound = AudioSegment.from_mp3(audio_path)
        sound.export(wav_path, format="wav")
        return wav_path
    else:
        raise ValueError("Unsupported audio format. Supported formats are WAV and MP3.")
