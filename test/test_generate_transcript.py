from interview_transcriber.transcript_generator import generate_transcript
import os

def test_generate_transcript(capsys):
    subtitle_data = [
        {'start': 0.0, 'speaker':'Lex', 'end': 12.76, 'duration': 12.76, 'text': 'What advice would you give to them about, if they want to try to do something big in this world, they want to really have a big positive impact, what advice would you give them about their career, maybe about life in general?', 'vtt': '00:00:00.000 --> 00:00:12.760\nWhat advice would you give to them about, if they want to try to do something big in this world, they want to really have a big positive impact, what advice would you give them about their career, maybe about life in general?', 'clip': '/Users/toffe/dev/ai/novia/transcriptions/data/audio/sample/clips/clip_0.wav'},
        {'start': 14.44, 'speaker':'Elon', 'end': 15.76, 'duration': 1.3200000000000003, 'text': 'Try to be useful.', 'vtt': '00:00:14.440 --> 00:00:15.760\nTry to be useful.', 'clip': '/Users/toffe/dev/ai/novia/transcriptions/data/audio/sample/clips/clip_1.wav'},
        {'start': 17.2, 'speaker':'Elon', 'end': 21.48, 'duration': 4.280000000000001, 'text': 'Do things that are useful to your fellow human beings, to the world.', 'vtt': '00:00:17.200 --> 00:00:21.480\nDo things that are useful to your fellow human beings, to the world.', 'clip': '/Users/toffe/dev/ai/novia/transcriptions/data/audio/sample/clips/clip_2.wav'},
        {'start': 21.48, 'speaker':'Elon', 'end': 23.04, 'duration': 1.5599999999999987, 'text': "It's very hard to be useful.", 'vtt': "00:00:21.480 --> 00:00:23.040\nIt's very hard to be useful.", 'clip': '/Users/toffe/dev/ai/novia/transcriptions/data/audio/sample/clips/clip_3.wav'}
    ]
    with capsys.disabled():
        transcript = generate_transcript(subtitle_data)
        print(transcript)
        assert transcript is not None


def test_generate_transcript_and_save(capsys):
    subtitle_data = [
        {'start': 0.0, 'speaker':'Lex', 'end': 12.76, 'duration': 12.76, 'text': 'What advice would you give to them about, if they want to try to do something big in this world, they want to really have a big positive impact, what advice would you give them about their career, maybe about life in general?', 'vtt': '00:00:00.000 --> 00:00:12.760\nWhat advice would you give to them about, if they want to try to do something big in this world, they want to really have a big positive impact, what advice would you give them about their career, maybe about life in general?', 'clip': '/Users/toffe/dev/ai/novia/transcriptions/data/audio/sample/clips/clip_0.wav'},
        {'start': 14.44, 'speaker':'Elon', 'end': 15.76, 'duration': 1.3200000000000003, 'text': 'Try to be useful.', 'vtt': '00:00:14.440 --> 00:00:15.760\nTry to be useful.', 'clip': '/Users/toffe/dev/ai/novia/transcriptions/data/audio/sample/clips/clip_1.wav'},
        {'start': 17.2, 'speaker':'Elon', 'end': 21.48, 'duration': 4.280000000000001, 'text': 'Do things that are useful to your fellow human beings, to the world.', 'vtt': '00:00:17.200 --> 00:00:21.480\nDo things that are useful to your fellow human beings, to the world.', 'clip': '/Users/toffe/dev/ai/novia/transcriptions/data/audio/sample/clips/clip_2.wav'},
        {'start': 21.48, 'speaker':'Elon', 'end': 23.04, 'duration': 1.5599999999999987, 'text': "It's very hard to be useful.", 'vtt': "00:00:21.480 --> 00:00:23.040\nIt's very hard to be useful.", 'clip': '/Users/toffe/dev/ai/novia/transcriptions/data/audio/sample/clips/clip_3.wav'}
    ]
    with capsys.disabled():
        output_file_path = "transcript.txt"
        transcript = generate_transcript(subtitle_data, output_file_path)
        print(transcript)
        assert os.path.exists(output_file_path)
