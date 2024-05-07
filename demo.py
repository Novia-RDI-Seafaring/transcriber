import gradio as gr

from interview_transcriber import download_youtube_video, convert_video_to_mp3, \
    generate_corrected_transcript, transcribe, translate_transcript

def translate_text(text, language):
    """
    Wrapper function for translating text into the selected language.
    """
    translated_text = translate_transcript(text, language)
    return translated_text


with gr.Blocks() as app:
    with gr.Row():
        video_url_input = gr.Textbox(label="YouTube Video URL", placeholder="Enter YouTube video URL here...")
        transcribe_btn = gr.Button("Transcribe")
    with gr.Row():
        transcription_output = gr.Textbox(label="Transcription", placeholder="Transcribed text will appear here...", lines=10)
        with gr.Column():
            language_dropdown = gr.Dropdown(label="Select Language", choices=["English", "Swedish", "Finnish", "German", "Russian", "Greek"], value="English")
            translate_btn = gr.Button("Translate")

        translation_output = gr.Textbox(label="Translated Text", placeholder="Translated text will appear here...", lines=10)
    
    def process_youtube_video(video_url, progress=gr.Progress()):
        """
        Downloads a video from YouTube, converts it to MP3, and transcribes it.
        """
        progress(0, desc="Downloading video")
        video_path, video_title, id = download_youtube_video(video_url)

        progress(0.2, desc=f"{video_title} - Making audio version")
        audio_path = convert_video_to_mp3(video_path)

        progress(0.3, desc=f"{video_title} - Transcribing audio")
        transcription = transcribe(audio_path, chunk_length_ms=10*60*100, progress=progress, progress_text=f"{video_title} - Transcribing chunk", start_progress=0.3, end_progress=0.8)

        progress(0.8, desc=f"{video_title} - Correcting spelling mistakes")
        corrected_transcription = generate_corrected_transcript(transcription)
        
        progress(1, desc="Done")
        return corrected_transcription
   
    transcribe_btn.click(
        process_youtube_video, 
        inputs=[video_url_input], 
        outputs=transcription_output
    )

    translate_btn.click(
        fn=lambda text, lang: translate_text(text, lang), 
        inputs=[transcription_output, language_dropdown], 
        outputs=translation_output
    )

if __name__ == '__main__':
    app.launch()

