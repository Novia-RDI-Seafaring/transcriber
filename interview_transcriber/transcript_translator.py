from openai import OpenAI
from .promt_chunker import process_long_text_with_openai

def translate_transcript(user_prompt, language):
    client = OpenAI()

    system_prompt = f"""You are a helpful assistant.
    Your task is to translate a transcript into {language}
    Keep timestamps intact. If there are not timestamps, translate the text.
    """
    return process_long_text_with_openai(system_prompt, user_prompt)
