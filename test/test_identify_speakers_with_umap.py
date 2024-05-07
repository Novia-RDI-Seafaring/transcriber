import os
from interview_transcriber.speaker_identifier_with_embeddings import identify_speakers
import nemo.collections.asr as nemo_asr
import pytest
import torchaudio 


#from pyannote.audio import Model, Inference
"""
def test_create_umap2_for_file(capsys):
    with capsys.disabled():
        file_path = "/Users/toffe/dev/ai/novia/transcriptions/data/audio/sample/clips/clip_0_trimmed.wav"
        model = Model.from_pretrained("pyannote/embedding", 
                              use_auth_token=os.environ["HUGGINGFACE_ACCESS_TOKEN"])

        inference = Inference(model, window="whole")
        embedding = inference(file_path)
        print(embedding)
        assert False, embedding
"""
@pytest.mark.skip(reason="Save time in testing. Temporarily")
def test_create_umap_for_file(capsys):
    with capsys.disabled():
        file_path = "/Users/toffe/dev/ai/novia/transcriptions/data/audio/sample/clips/clip_0_trimmed_mono.wav"
        speaker_model = nemo_asr.models.EncDecSpeakerLabelModel.from_pretrained("nvidia/speakerverification_en_titanet_large")

        # Directly pass the file path to get_embedding
        embedding = speaker_model.get_embedding(file_path)

        print(embedding)
        assert embedding is not None

@pytest.mark.skip(reason="Save time in testing. Temporarily")
def test_identify_speakers_with_umap(capsys):
    with capsys.disabled():
        current_directory = os.path.dirname(os.path.abspath(__file__))
        project_directory = os.path.dirname(current_directory)
        audio_file_path = os.path.join(project_directory, "data", "audio", "sample", "clipped_sample.mp3")

        speaker_data = identify_speakers(audio_file_path)
        print(speaker_data)
        assert speaker_data is not None

