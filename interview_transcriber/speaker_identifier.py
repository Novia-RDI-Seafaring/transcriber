from pyannote.audio import Pipeline
import torchaudio
from pydub import AudioSegment
from pyannote.core import Segment
from interview_transcriber.file_utils import ensure_path_exists
from interview_transcriber.audio_transcriber import combine_subtitle_lines
import os, re

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
    ## Try Titannet https://huggingface.co/nvidia/speakerverification_en_titanet_large
    # Umap => embeddings till 2d
    # Plotly / dash => markera...
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

    # Open VTT file
    with open(vtt_file_path, 'r') as vtt_file:
        vtt_content = vtt_file.read()

    # Combine subtitle lines
    combined_subtitles = combine_subtitle_lines(vtt_content)
    subtitle_blocks = combined_subtitles.split("\n\n")
    # Initialize list to store transcript with speaker information
    transcript_with_speakers = []

    # Iterate over each combined subtitle block
    for subtitle_block in subtitle_blocks:
        # Find the corresponding diarization speaker for the subtitle block
        speaker = find_speaker_for_segment(diarization_results, subtitle_block)
        subtitle_info = extract_subtitle_info(subtitle_block)
        if subtitle_info is not None:
            subtitle_info["speaker"] = speaker

            # Append the subtitle info to the transcript
            transcript_with_speakers.append(subtitle_info)

    # Write transcript with speaker information to the output file
    with open(output_file_path, 'w') as f:
        for subtitle_info in transcript_with_speakers:
            f.write(f"{subtitle_info['speaker']}: ")
            #f.write(f"{subtitle_info['start']} --> {subtitle_info['end']}\n")
            f.write(f"{subtitle_info['text']}\n\n")

import logging

def find_speaker_for_segment(diarization_results, subtitle_block):
    # Extract start time string from the subtitle block
    start_time_str = subtitle_block.split("\n")[0].strip()
    
    try:
        # Convert start time string to seconds
        center_time = find_center_time(start_time_str)
    except ValueError:
        # Log a warning for invalid time format
        print(f"Invalid VTT time format--->: {start_time_str}")
        return None

    # If start_time is None, return None
    if center_time is None:
        print(f"Center time is None--->: {start_time_str}")
        return None

    # Iterate over diarization results to find the speaker for the subtitle block
    for segment, track, speaker in diarization_results.itertracks(yield_label=True):
        if segment is not None and segment.start <= center_time < segment.end:
            return speaker
    
def vtt_time_to_seconds(time_str):
    try:
        # Define a regular expression pattern to match the time components
        pattern = r'(\d{2}):(\d{2}):(\d{2})\.(\d{3})'

        # Search for the pattern in the time string
        match = re.search(pattern, time_str)

        if match:
            # Extract the matched groups for hours, minutes, seconds, and milliseconds
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            milliseconds = int(match.group(4))

            # Calculate the total number of seconds, including milliseconds
            total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000

            return total_seconds
        else:
            print(f"Error: Invalid VTT time format: {time_str}")
            return None
    except (ValueError, IndexError):
        # Handle the case where the time string is not in the expected format
        print("Error: Invalid VTT time format2")
        return None

def extract_subtitle_info(subtitle_block):
    # Split the subtitle block by '\n'
    lines = subtitle_block.strip().split('\n')

    # Check if the subtitle block contains at least one line
    if not lines:
        return None

    # Extract start and end times
    timestamps = lines[0].split('-->')
    if len(timestamps) != 2:
        return None

    start_time = timestamps[0].strip()
    end_time = timestamps[1].strip()

    # Extract text
    text = ' '.join(lines[1:]).strip()

    # Create and return a dictionary with the subtitle information
    return {
        'start': start_time,
        'end': end_time,
        'text': text
    }

def find_center_time(time_range_str):
    # Extract start and end times from the time range string
    start_time_str, end_time_str = time_range_str.split(" --> ")

    # Convert start and end times to seconds
    start_time_seconds = vtt_time_to_seconds(start_time_str)
    end_time_seconds = vtt_time_to_seconds(end_time_str)

    # Calculate the center time in seconds
    center_time_seconds = (start_time_seconds + end_time_seconds) / 2

    return center_time_seconds