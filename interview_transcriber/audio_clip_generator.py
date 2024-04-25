import os
import subprocess

def generate_audio_clips(subtitle_data, audio_file, output_dir):
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Iterate over each subtitle chunk
    for i, subtitle in enumerate(subtitle_data):
        start_time = subtitle['start']
        end_time = subtitle['end']
        segment_duration = subtitle['duration']

        # Generate the output audio file name
        output_file = os.path.join(output_dir, f"clip_{i}.wav")
        
        # Extract the segment of audio from the input audio file, padding with silence if necessary
        extract_audio_segment(audio_file, output_file, start_time, segment_duration)
       
        subtitle_data[i]['clip'] = output_file

        #print(f"Generated audio clip for subtitle: '{text}'")
    return subtitle_data

def parse_subtitle_content(subtitle_content):
    # Implement parsing logic here
    pass

def extract_audio_segment(input_file, output_file, start_time, segment_duration):
    
    # Build the ffmpeg command to extract the segment and pad it with silence if necessary
    ffmpeg_command = [
        'ffmpeg',
        '-y',  # Overwrite output file if it exists
        '-ss', str(start_time),  # Start time
        '-i', input_file,  # Input audio file
        '-t', str(segment_duration),  # Duration of the segment
        '-c', 'copy',  # Copy audio codec
        output_file,  # Output file path
    ]
    print(ffmpeg_command)

    # Run ffmpeg command
    subprocess.run(ffmpeg_command, capture_output=True)
    
def remove_silence_from_beginning(input_file, output_file, start_silence_threshold=0.02):
    # Build the ffmpeg command to remove silence from the beginning
    ffmpeg_command = [
        'ffmpeg',
        '-y',  # Overwrite output file if it exists
        '-i', input_file,  # Input audio file
        '-af', f'silenceremove=start_periods=1:start_silence=0:start_threshold={start_silence_threshold}',  # Audio filter
        output_file  # Output file path
    ]
    
    # Run ffmpeg command
    subprocess.run(ffmpeg_command, capture_output=True)

import subprocess

def adjust_audio_duration(input_file, output_file, max_duration):
    # Get the duration of the input audio
    ffprobe_command = [
        'ffprobe',
        '-i', input_file,
        '-show_entries', 'format=duration',
        '-v', 'quiet',
        '-of', 'csv=p=0'
    ]
    duration = float(subprocess.check_output(ffprobe_command).decode().strip())

    # If the duration is within the max duration, just copy the input to output
    if duration <= max_duration:
        subprocess.run(['cp', input_file, output_file])
        return

    # Otherwise, trim or pad the audio to match max_duration
    if duration < max_duration:
        # Pad the audio with silence at the end to match max_duration
        ffmpeg_command = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-i', input_file,  # Input audio file
            '-af', f'adelay={int((max_duration - duration) * 1000)}|{int((max_duration - duration) * 1000)}',  # Audio filter to add silence
            output_file  # Output file path
        ]
    else:
        # Trim the audio to match max_duration
        ffmpeg_command = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-i', input_file,  # Input audio file
            '-t', str(max_duration),  # Maximum duration of the output audio
            output_file  # Output file path
        ]

    # Run ffmpeg command
    subprocess.run(ffmpeg_command, capture_output=True)