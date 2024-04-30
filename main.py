from interview_transcriber.transcript_generator import generate_transcript
from interview_transcriber.speaker_identifier_with_embeddings import identify_speakers
import json
import argparse

def main(audio_file_path, output_file_path, context_file_path=None, use_local=False):
    # Read the context file if provided
    context_string = None
    if context_file_path:
        with open(context_file_path, 'r') as file:
            context_string = file.read()

    # Identify speakers, passing context data if available
    subtitle_data = identify_speakers(audio_file_path, context_string=context_string, use_local=use_local)
        
    # Generate the transcript and save it to the specified output file
    generate_transcript(subtitle_data, file_path=output_file_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a transcript from audio data.")
    parser.add_argument('audio_file_path', type=str, help='The path to the audio file.')
    parser.add_argument('output_file_path', type=str, help='The path to the output text file where the transcript will be saved.')
    parser.add_argument('--context_file_path', type=str, help='Optional path to a text file providing context for speaker identification.', default=None)
    parser.add_argument('--use_local', action='store_true', help="Use local whisper")

    args = parser.parse_args()
    main(args.audio_file_path, args.output_file_path, args.context_file_path, args.use_local)
