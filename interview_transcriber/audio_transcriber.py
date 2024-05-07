from openai import OpenAI
from pydub import AudioSegment
from pydub.silence import split_on_silence
from interview_transcriber.file_utils import ensure_path_exists
from interview_transcriber.subtitle_time_shifter import shift_time_in_subtitle
from .file_utils import get_content
from faster_whisper import WhisperModel
from types import SimpleNamespace

import math, os, re

def seconds_to_vtt_time(seconds):
    """Converts a float `seconds` to a string in VTT time format HH:MM:SS.mmm"""
    millis = int(seconds * 1000)
    hours, remainder = divmod(millis, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"

def ends_with_sentence_terminator(text):
    """
    Check if the given string ends with a sentence terminator (. ? ! ; ... : —).

    Args:
    text (str): The string to check.

    Returns:
    bool: True if the string ends with one of the specified characters or sequences, otherwise False.
    """
    # Include complex terminators like ellipsis and check with text.endswith
    sentence_terminators = ('.', '?', '!', ';', '...', ':', '—')
    
    # Return True if any valid terminator is at the end of the text
    return any(text.endswith(terminator) for terminator in sentence_terminators) if text else False

class ExtendableSegment:
    def __init__(self, d=None):
        if d is not None:
            self.text = d["word"]
            self.start = d["start"]
            self.end = d["end"]
        else:
            self.text = ''
            self.start = None
            self.end = None

    def __add__(self, other):
        # Extend the current segment by another segment
        if hasattr(other, 'word') and hasattr(other, 'start') and hasattr(other, 'end'):
            if self.start is None or self.end is None:
                # Initialize the current segment with the attributes of the other segment if uninitialized
                self.text = other.word
                self.start = other.start
                self.end = other.end
            else:
                # Otherwise, concatenate text and update the end
                self.text += " " + other.word
                self.end = other.end
            return self
        else:
            return NotImplemented

    def __repr__(self):
        # Provides a nice way to print the objects of this class
        return f"ExtendableSegment(text='{self.text}', start={self.start}, end={self.end})"

def add_punctuation_to_words(segment):
    import re
    
    # Extract the text and words list from the dictionary
    text = segment.text
    word_entries = segment.words
    
    # Extract words and punctuation from the text for comparison
    text_words_with_punctuation = re.findall(r'\w+|[,.?!]', text)
    
    # Initialize variables
    updated_word_entries = []
    index_text = 0
    len_text_words = len(text_words_with_punctuation)
    
    # Process each word entry in the dictionary
    for word_entry in word_entries:
        if isinstance(word_entry, dict):
            word_entry = SimpleNamespace(**word_entry)
        word = word_entry.word
        # Scan through text words to find matches and check for trailing punctuation
        while index_text < len_text_words:
            current_text_word = text_words_with_punctuation[index_text]
            if current_text_word == word:
                # Append word and check for trailing punctuation
                if index_text + 1 < len_text_words and re.match(r'[,.?!]', text_words_with_punctuation[index_text + 1]):
                    word += text_words_with_punctuation[index_text + 1]
                    index_text += 1  # Move past the punctuation as well
                updated_word_entries.append({'word': word, 'start': word_entry.start, 'end': word_entry.end})
                index_text += 1
                break
            index_text += 1
    
    # Update the dictionary with punctuated words
    segment.words = updated_word_entries
    return segment
        

def get_sentences_by_words(segments):
    new_segments = []

    for segment in segments:
        try:
            if isinstance(segment, dict):
                segment = SimpleNamespace(**segment)

            segment = add_punctuation_to_words(segment)
        except Exception as e:
            print(e)
            segment = segment

        new_segment = ExtendableSegment()

        for word in segment.words:
            if isinstance(word, dict):
                word = SimpleNamespace(**word)


            if ends_with_sentence_terminator(word.word):
                new_segment += word
                new_segments.append(new_segment)
                new_segment = ExtendableSegment()
            else:
                new_segment += word

        if new_segment.text:
            new_segments.append(new_segment)
    return new_segments

def get_transcription_prompt(language):
    TRANSCRIBE_PROMPTS = {
        "en": "This is a transcription.",
        "da": "Dette er en transskription.",  # Danish
        "sv": "Detta är en transkription.",   # Swedish
        "no": "Dette er en transkripsjon.",   # Norwegian (Bokmål)
        "nn": "Dette er ei transkripsjon.",   # Norwegian (Nynorsk)
        "fi": "Tämä on transkriptio.",        # Finnish
        "is": "Þetta er þýðing.",             # Icelandic
        "et": "See on transkriptsioon.",      # Estonian
        "de": "Das ist eine Transkription.",  # German
        "fr": "Ceci est une transcription.",  # French
        "es": "Esto es una transcripción.",   # Spanish
        "it": "Questa è una trascrizione."    # Italian
    }    
    if language in TRANSCRIBE_PROMPTS:
        return TRANSCRIBE_PROMPTS[language]
    else:
        return TRANSCRIBE_PROMPTS["en"]

def transcribe_audio(audio_path, context_string="", use_local=False, response_format="vtt", save_output=False, language=None):
    if use_local:
        model_size = "large-v3"
        model = WhisperModel(model_size, device="auto")

        _segments, info = model.transcribe(audio_path, word_timestamps=True, beam_size=5, condition_on_previous_text=False, initial_prompt=get_transcription_prompt(language) + ". " + context_string, language=language)
    else:
        client = OpenAI()
        audio_file = open(audio_path, "rb")
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            prompt = get_transcription_prompt(language) + ". " + context_string,
            language=language,
            timestamp_granularities = ['word']
        )

        _segments = [response]
    print("segments...")
    print(_segments)
    segments = get_sentences_by_words(_segments)
    if response_format == "vtt":
        transcript = "WEBVTT\n\n"
        transcript += "\n\n".join([f"{seconds_to_vtt_time(segment.start)} --> {seconds_to_vtt_time(segment.end)}\n{segment.text.strip()}" for segment in segments]).replace("  ", " ")
    elif response_format == "txt":
        transcript = " ".join([segment.text for segment in segments]).replace("  ", " ")
    elif response_format == "json":
        transcript = {"segments": segments}
    else:
        transcript = segments

        print(transcript)
        

    if save_output:
        output_filename = audio_path.replace("/audio/", f"/{response_format}/").replace(".mp3", f".{response_format}")
        ensure_path_exists(output_filename)
        
        # Write the transcription to a file
        with open(output_filename, "w") as file:
            file.write(transcript)

        return output_filename
    else:
        return transcript


def transcribe(audio_path, context_string="", use_local=False, chunk_length_ms=10*60*1000, progress=None, progress_text="Transcribing", start_progress=0.3, end_progress=0.8, language=None):
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
        
        #transcription = "NOTE This is where the audio was splitted, for processing it in chunks..."
        transcription = str(transcribe_audio(audio_path=chunk_file, context_string=context_string, use_local=use_local, language=language)).replace("WEBVTT\n\n", "").strip()

        adjusted_transcription = shift_time_in_subtitle(transcription, start)
        transcriptions.append(adjusted_transcription)
        
        # Cleanup the temporary chunk file
        os.remove(chunk_file)
    
    # Combine the transcriptions
    combined_transcription = "\n\n".join(transcriptions)
    
    return combined_transcription

def time_to_seconds(time_str):
    h, m, s = map(float, time_str.split(':'))
    return h * 3600 + m * 60 + s

import os
import re

def combine_subtitle_lines(vtt_content_or_path):
    vtt_content = get_content(vtt_content_or_path)

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
    if start_time is not None:
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