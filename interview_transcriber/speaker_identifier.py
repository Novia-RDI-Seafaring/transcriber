from pyannote.audio import Pipeline
import torchaudio
from pydub import AudioSegment
from pyannote.core import Segment
from interview_transcriber.file_utils import ensure_path_exists
import os

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


def create_diarization_path(audio_path):
    diarization_path = audio_path.replace("/audio/", "/diarization/").replace(" ", "-").replace(".mp3", ".rttm")
    ensure_path_exists(diarization_path)
    return diarization_path

def identify_speakers(audio_path):
    output_file = create_diarization_path(audio_path)
    wav_path = get_wav_path(audio_path) # sine mp3 is not supported

    # instantiate the pipeline
    pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=os.environ["HUGGINGFACE_ACCESS_TOKEN"])
    
    waveform, sample_rate = torchaudio.load(wav_path)

    # run the pipeline on an audio file
    diarization = pipeline(wav_path)

    speaker_clips = generate_speaker_clips(diarization, audio_path);

    # dump the diarization output to disk using RTTM format
    with open(output_file, "w") as rttm:
        diarization.write_rttm(rttm)

    return diarization, output_file, speaker_clips

# Minimum duration threshold for a segment to be considered
MIN_SEGMENT_DURATION = 1  # Adjust as needed
MAX_SEGMENT_DURATION = 3  # Adjust as needed
MAX_SEGMENTS_PER_SPEAKER = 3  # Adjust as needed

def generate_speaker_clips(diarization_output, audio_path):
    # Load the original audio file
    audio = AudioSegment.from_file(audio_path)
    
    # Dictionary to store speaker clips paths
    speaker_clips = {}

    # Iterate through each annotation in the diarization output
    for i, (segment, track, label) in enumerate(diarization_output.itertracks(yield_label=True)):
        # Calculate segment duration
        segment_duration = segment.duration

        # Extract speaker tag (label) as string
        speaker_tag = str(label)

        # If the segment duration is below the threshold, skip
        if segment_duration < MIN_SEGMENT_DURATION:
            continue

        # Calculate the new end time based on the maximum duration allowed
        new_end_time = min(segment.end * 1000, segment.start * 1000 + MAX_SEGMENT_DURATION * 1000)

        # Extract the segment based on the calculated start and end times
        speaker_clip = audio[segment.start * 1000:new_end_time]

        # Generate output file name
        output_file = f"{os.path.splitext(os.path.basename(audio_path))[0]}__{speaker_tag}.mp3"

        # Save the clip to the same folder as the original file
        output_path = os.path.join(os.path.dirname(audio_path), output_file)

        # If speaker already exists in the dictionary, append the segment to the existing list
        if speaker_tag not in speaker_clips:
            speaker_clips[speaker_tag] = []

        # Append the segment to the speaker's list of clips
        clip_index = len(speaker_clips[speaker_tag])
        output_path = output_path.replace('.mp3', f'__{clip_index}.mp3')
        speaker_clips[speaker_tag].append(output_path)

        # Export the segment as a clip
        speaker_clip.export(output_path, format="mp3")

    print("Speaker clips generated successfully.")
    return speaker_clips


def generate_transcript_with_speakers(vtt_file_path, diarization_results, output_file_path):
    # Load diarization results
    # Assuming diarization_results is a dictionary where keys are speaker labels and values are lists of segments
    # If diarization_results is in a different format, adjust this part accordingly

    # Open VTT file
    with open(vtt_file_path, 'r') as vtt_file:
        vtt_content = vtt_file.read()

    # Open output file for writing
    with open(output_file_path, 'w') as f:
        # Iterate over each speaker in the diarization results
        #for speaker, segments in diarization_results.items():
        for i, (segment, track, speaker) in enumerate(diarization_results.itertracks(yield_label=True)):

            # Iterate over each segment for the current speaker
            #for segment in segments:
            # Find the corresponding subtitle for the segment
            subtitle = find_subtitle_for_segment(vtt_content, segment)
            if subtitle:
                # Write speaker label and subtitle text to the output file
                f.write(f"{speaker}: {subtitle.text}\n")
            else:
                # If no corresponding subtitle found, write only the speaker label
                f.write(f"{speaker}:\n")

def find_subtitle_for_segment(vtt_content, segment):
    # Split VTT content into individual subtitle blocks
    subtitles = vtt_content.split('\n\n')

    # Iterate over each subtitle block
    for subtitle_block in subtitles:
        # Check if the subtitle block contains the segment's start and end time
        if segment_to_vtt_time(segment.start) in subtitle_block and segment_to_vtt_time(segment.end) in subtitle_block:
            # Extract the subtitle text
            subtitle_lines = subtitle_block.split('\n')
            text = ' '.join(subtitle_lines[2:])  # Exclude timing information
            return Subtitle(text)
    return None

def segment_to_vtt_time(ms):
    # Convert milliseconds to VTT time format (00:00:00.000)
    seconds, milliseconds = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"

class Subtitle:
    def __init__(self, text):
        self.text = text