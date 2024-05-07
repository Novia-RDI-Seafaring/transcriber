def generate_transcript(subtitle_data, file_path=None):
    transcript = []  # Holds the complete formatted transcript
    current_speaker = None  # Tracks the current speaker
    speaker_text = []  # Collects text for the current speaker

    # Iterate through each entry in the subtitle data
    for entry in subtitle_data:
        # Assuming 'speaker' is a key in each subtitle entry
        speaker_name = entry['speaker']

        # Check if the speaker has changed
        if speaker_name != current_speaker:
            # If there's a current speaker, save their accumulated text
            if current_speaker is not None:
                transcript.append(f"{current_speaker}: {' '.join(speaker_text)}")
            # Reset for the new speaker
            current_speaker = speaker_name
            speaker_text = [entry['text']]  # Start the new speaker's text
        else:
            # No speaker change, continue adding text
            speaker_text.append(entry['text'])

    # Append the last speaker's text to the transcript
    if current_speaker is not None and speaker_text:
        transcript.append(f"{current_speaker}: {' '.join(speaker_text)}")

    # Join the transcript into a single string with two newlines between speaker entries
    formatted_transcript = '\n\n'.join(transcript)

    # Write to a file if a file path is provided
    if file_path:
        with open(file_path, 'w') as file:
            file.write(formatted_transcript)
        print(f"Transcript has been written to {file_path}")
    else:
        return formatted_transcript
