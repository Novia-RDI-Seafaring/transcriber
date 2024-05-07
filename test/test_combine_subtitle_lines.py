import os
from interview_transcriber.file_utils import file_has_content
from interview_transcriber.audio_transcriber import combine_subtitle_lines, transcribe

from interview_transcriber.file_utils import get_content
from faster_whisper import WhisperModel

current_directory = os.path.dirname(os.path.abspath(__file__))
project_directory = os.path.dirname(current_directory)

audio_file_path = os.path.join(project_directory, "data", "audio", "sample", "clipped_sample.mp3")
subtitle_file_path = os.path.join(project_directory, "data", "vtt", "sample", "clipped_sample.vtt")
diarization_file_path = os.path.join(project_directory, "data", "diarization", "sample", "clipped_sample.rttm")

def test_word_level_transcript_fns(capsys):
    with capsys.disabled():

        #transcript = transcribe(audio_file_path, use_local=True)
        #assert transcript is not None, transcript
        #print(transcript)
        
        transcript = transcribe(audio_file_path, use_local=False)
        assert transcript is not None, transcript
        print(transcript)
        assert False        



def t_est_word_level_transcript(capsys):
    with capsys.disabled():

        model_size = "large-v3"
        model = WhisperModel(model_size, device="auto")

        _segments, info = model.transcribe(audio_file_path, word_timestamps=True, beam_size=5, condition_on_previous_text=False, initial_prompt=None, language="en")
        segments = get_sentences_by_words(_segments)
        print(segments, info)
        for segment in segments:
            print(segment.text)


        #subtitle_data, embeddings, speaker_labels, k, kluster_labels, EMBEDDINGS_UMAP = identify_speakers(audio_file_path)

def t_est_combine_subtitle_lines(capsys):
    with capsys.disabled():
        #assert file_has_content(audio_file_path)
        assert file_has_content(subtitle_file_path)
        assert file_has_content(diarization_file_path)
        combined_subtitle_text, combined_subtitle_lines = combine_subtitle_lines(subtitle_file_path)

        assert combined_subtitle_text is not None
        assert combined_subtitle_text.startswith("WEBVTT")

        assert combined_subtitle_lines is not None
        assert len(combined_subtitle_lines) > 0
        assert combined_subtitle_lines[0]["start"] is not None
        assert combined_subtitle_lines[0]["text"] is not None