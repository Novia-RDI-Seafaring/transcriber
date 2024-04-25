from interview_transcriber.video_downloader import download_youtube_video, video_folder_exists
from interview_transcriber.video_converter import convert_video_to_mp3, there_is_a_converted_audio_file, create_audiofilepath
from interview_transcriber.speaker_identifier import identify_speakers
import os
import warnings
import pytest

from pyannote.audio import Pipeline


video_url="https://www.youtube.com/watch?v=dFbAqcPzoUY&ab_channel=FoilArmsandHog"
video_path = None
audio_path = None

SKIP_CONVERTING = True

@pytest.mark.skip(reason="Not needed in all tests")
def test_there_is_a_huggingface_api_key():
    assert os.environ["HUGGINGFACE_ACCESS_TOKEN"] is not None

@pytest.mark.skip(reason="Not needed in all tests")
def test_that_an_mp3_file_is_created(capsys):
    global video_path, audio_path, SKIP_CONVERTING
    if SKIP_CONVERTING:
        video_path = "data/video/youtube/dFbAqcPzoUY/Everything Thats Wrong with Content Creators.mp4"
        audio_path = "data/audio/youtube/dFbAqcPzoUY/Everything Thats Wrong with Content Creators.mp3"
        assert SKIP_CONVERTING
        return
    
    with capsys.disabled():
        video_path, title, id = download_youtube_video(video_url)
        assert(video_folder_exists(video_url))
        audio_path = convert_video_to_mp3(video_path)
        assert(there_is_a_converted_audio_file(video_path))

@pytest.mark.skip(reason="Not needed in all tests")
def test_that_you_have_accepted_terms():
    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
        use_auth_token=os.environ["HUGGINGFACE_ACCESS_TOKEN"])
        result = identify_speakers("data/audio/sample.mp3")

        assert True
    except:
        print("Make sure you have acreed to  https://huggingface.co/pyannote/speaker-diarization-3.1 and https://huggingface.co/pyannote/segmentation-3.0 and " )

@pytest.mark.skip(reason="Not needed in all tests")
def test_video_path_is_not_none(capsys):
    with capsys.disabled():
        global video_path, audio_path
        assert video_path is not None
        assert audio_path is not None

@pytest.mark.skip(reason="Save time in testing. Temporarily")
def test_identify_speakers(capsys):
    with capsys.disabled():
        current_directory = os.path.dirname(os.path.abspath(__file__))
        project_directory = os.path.dirname(current_directory)
        audio_file_path = os.path.join(project_directory, "data", "audio", "sample", "clipped_sample.mp3")

        result, output_file, speaker_clips = identify_speakers(audio_file_path)

        print(speaker_clips)

        #result = identify_speakers(audio_path)
        assert result is not None
        assert output_file is not None
        assert speaker_clips is not None
