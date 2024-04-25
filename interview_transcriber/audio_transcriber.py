from openai import OpenAI
from pydub import AudioSegment
from pydub.silence import split_on_silence
from interview_transcriber.file_utils import ensure_path_exists
from interview_transcriber.subtitle_time_shifter import shift_time_in_subtitle

import math, os, re

def transcribe_audio(audio_path, response_format="vtt", save_output=False):
    client = OpenAI()
    audio_file = open(audio_path, "rb")
    transcript = client.audio.translations.create(
        model="whisper-1",
        file=audio_file,
        response_format=response_format
    )

    if save_output:
        output_filename = audio_path.replace("/audio/", f"/{response_format}/").replace(".mp3", f".{response_format}")
        ensure_path_exists(output_filename)
        
        # Write the transcription to a file
        with open(output_filename, "w") as file:
            file.write(transcript)

        return output_filename
    else:
        return transcript


def transcribe(audio_path, chunk_length_ms=10*60*1000, progress=None, progress_text="Transcribing", start_progress=0.3, end_progress=0.8):
    """
    Splits a long audio file into manageable chunks, transcribes each, and then combines the results.
    
    Parameters:
    - audio_path: str. Path to the input audio file.
    - chunk_length_ms: int. Length of each audio chunk in milliseconds. Default is 10 minutes.
    
    Returns:
    - A string containing the combined transcription of the entire audio.
    """
    # Load the audio file
    audio = AudioSegment.from_mp3(audio_path)
    
    # Calculate the number of chunks needed
    num_chunks = math.ceil(len(audio) / chunk_length_ms)
    chunk_progress = (end_progress - start_progress) / num_chunks

    transcriptions = []
    
    for i in range(num_chunks):

        if progress is not None:
            current_progress = start_progress + (i) * chunk_progress
            progress(current_progress, desc=f"{progress_text} {i+1}/{num_chunks}")
        
        # Split the audio into the specified chunk
        start = i * chunk_length_ms
        end = min((i + 1) * chunk_length_ms, len(audio))
        chunk = audio[start:end]    
        
        # Export the chunk to a temporary file
        chunk_file = f"temp_chunk_{i}.mp3"
        chunk.export(chunk_file, format="mp3")
        
        transcription = "NOTE This is where the audio was splitted, for processing it in chunks..."
        transcription += transcribe_audio(chunk_file)
        
        adjusted_transcription = shift_time_in_subtitle(transcription, start)
        transcriptions.append(adjusted_transcription)
        
        # Cleanup the temporary chunk file
        os.remove(chunk_file)
    
    # Combine the transcriptions
    combined_transcription = "\n".join(transcriptions)
    
    return combined_transcription

def time_to_seconds(time_str):
    h, m, s = map(float, time_str.split(':'))
    return h * 3600 + m * 60 + s

import os
import re

def combine_subtitle_lines(vtt_content_or_path):
    # If the input is a file path, read the content of the file
    if os.path.exists(vtt_content_or_path):
        with open(vtt_content_or_path, 'r') as file:
            vtt_content = file.read()
    else:
        vtt_content = vtt_content_or_path

    # Split the VTT content into individual subtitle blocks
    subtitle_blocks = vtt_content.strip().split('\n\n')

    # List to store combined subtitle lines
    combined_subtitle_lines = []

    # Initialize variables to store current timestamp block
    start_time = None
    end_time = None
    combined_text = ""

    subtitle_data = []

    # Iterate over each subtitle block
    for block in subtitle_blocks:
        # Extract the start and end timestamps from the block
        timestamps = re.findall(r'(\d{2}:\d{2}:\d{2}.\d{3})', block)
        if len(timestamps) != 2:
            continue
        start, end = timestamps


        # Extract the subtitle text from the block
        text = " ".join(block.split("\n")[1:])

        # If this is the first subtitle block or there is a pause between this block and the previous one
        if start_time is None or (time_to_seconds(start) - time_to_seconds(end_time)) > 1:
            # If this is not the first subtitle block, append the previous combined subtitle to the list
            if start_time is not None:
                #combined_subtitle_lines.append(f"{start_time} --> {end_time}\n{combined_text}")
                combined_subtitle_lines.append({
                    "start": time_to_seconds(start_time),
                    "end": time_to_seconds(end_time),
                    "duration": time_to_seconds(end_time) - time_to_seconds(start_time),
                    "text": combined_text,
                    "vtt": f"{start_time} --> {end_time}\n{combined_text}"
                })
            # Update start time for the new timestamp block
            start_time = start

            # Initialize end time and combined text for the new timestamp block
            end_time = end
            combined_text = text

            subtitle_data.append({
                "start": time_to_seconds(start_time),
                "end": time_to_seconds(end_time),
                "duration": time_to_seconds(end_time) - time_to_seconds(start_time),
                "text": combined_text,
                "vtt": f"{start_time} --> {end_time}\n{combined_text}"

            })
        else:
            # Combine the subtitle text with the previous one
            combined_text += " " + text

            # Update the end time to the end time of the current subtitle block
            end_time = end

            # Check if the current subtitle block ends with a sentence-ending punctuation
            if text.endswith(".") or text.endswith("?") or text.endswith("!"):
                # If the subtitle block ends with punctuation, treat it as the end of a sentence
                # Append the combined subtitle to the list and reset variables for the next subtitle
                combined_subtitle_lines.append({
                    "start": time_to_seconds(start_time),
                    "end": time_to_seconds(end_time),
                    "duration": time_to_seconds(end_time) - time_to_seconds(start_time),
                    "text": combined_text,
                    "vtt": f"{start_time} --> {end_time}\n{combined_text}"
                })
                start_time = None
                end_time = None
                combined_text = ""

    # Append the last combined subtitle block to the list
    #combined_subtitle_lines.append(f"{start_time} --> {end_time}\n{combined_text}")
    combined_subtitle_lines.append({
        "start": time_to_seconds(start_time),
        "end": time_to_seconds(end_time),
        "duration": time_to_seconds(end_time) - time_to_seconds(start_time),
        "text": combined_text,
        "vtt": f"{start_time} --> {end_time}\n{combined_text}"
    })
    # Add "WEBVTT" at the beginning of the combined subtitle text
    combined_subtitle_text = "WEBVTT\n\n" + "\n\n".join(map(lambda x:x["vtt"], combined_subtitle_lines))

    return combined_subtitle_text, combined_subtitle_lines