import os
from interview_transcriber.file_utils import file_has_content
from interview_transcriber.audio_transcriber import combine_subtitle_lines

current_directory = os.path.dirname(os.path.abspath(__file__))
project_directory = os.path.dirname(current_directory)

audio_file_path = os.path.join(project_directory, "data", "audio", "sample", "clipped_sample.mp3")
subtitle_file_path = os.path.join(project_directory, "data", "vtt", "sample", "clipped_sample.vtt")
diarization_file_path = os.path.join(project_directory, "data", "diarization", "sample", "clipped_sample.rttm")


def test_combine_subtitle_lines(capsys):
    with capsys.disabled():
        #assert file_has_content(audio_file_path)
        assert file_has_content(subtitle_file_path)
        assert file_has_content(diarization_file_path)

        print("---------------")
        combined_subs = combine_subtitle_lines(subtitle_file_path)
        print("---------------")
        print("abcabc")
        print(combined_subs)
        print("123123")
        assert False, combined_subs