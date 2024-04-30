from interview_transcriber.speaker_identifier_diarization import identify_speakers_with_diarization
from interview_transcriber import transcribe_audio
from interview_transcriber.speaker_identifier_diarization import generate_transcript_with_speakers
from interview_transcriber.audio_transcriber import combine_subtitle_lines

import os
import warnings
import pytest

current_directory = os.path.dirname(os.path.abspath(__file__))
project_directory = os.path.dirname(current_directory)
audio_file_path = os.path.join(project_directory, "data", "audio", "sample", "clipped_sample.mp3")

@pytest.mark.skip(reason="Save time in testing. Temporarily")
def test_generate_transcript_with_speakers(capsys):
    global audio_file_path
    with capsys.disabled():
 
        subtitle_file = transcribe_audio(audio_file_path, save_output=True)
        output_file_path = subtitle_file.replace(".vtt", "_transcript.txt")
        assert subtitle_file is not None
        print(subtitle_file)

        diarization, output_file, speaker_clips = identify_speakers_with_diarization(audio_file_path)

        generate_transcript_with_speakers(subtitle_file, diarization, output_file_path)
        assert os.path.exists(output_file_path)

        with open(output_file_path, 'r') as file:
            content = file.read()
        
        # Check if the content is not empty
        assert content.strip(), f"File '{output_file_path}' is empty."

        combined_subs = combine_subtitle_lines(subtitle_file)