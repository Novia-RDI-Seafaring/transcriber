```
from youtube_subtitles import download_youtube_video, convert_video_to_mp3, \
    generate_corrected_transcript, transcribe_audio, translate_transcript

video_url = "https://www.youtube.com/watch?v=kpM6P0-s6U0" # short file
video_path, video_title = download_youtube_video(video_url)
audio_path = convert_video_to_mp3(video_path)

print(
    translate_transcript(
        generate_corrected_transcript("hello thär, i äm a telefåun seilsmän"),
        "swedish"
    )
)

def demo_input():
    sentence = input("Give me a sentence: ")
    print(f"you said {sentence}")

    corrected_sentece = generate_corrected_transcript(sentence)
    print(f"you might have meant: {corrected_sentece}")

    translated_sentence = translate_transcript(corrected_sentece, "frehnch")
    print(f"or as they say in France: {translated_sentence}")


import gradio as gr

def translate_text(text, language):
    """
    Wrapper function for translating text into the selected language.
    """
    translated_text = translate_transcript(text, language)
    return translated_text



```