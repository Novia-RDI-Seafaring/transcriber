from openai import OpenAI

def split_prompt_into_chunks(user_prompt, max_tokens):
    """
    Splits the user_prompt into chunks that don't exceed the max_tokens limit.
    This is a simplified example that assumes user_prompt is a string and splits by whitespace.
    A more sophisticated approach might be needed for accurate token count estimation.
    
    Parameters:
    - user_prompt: The text to split into chunks.
    - max_tokens: The maximum token count for each chunk.
    
    Returns:
    - A list of text chunks.
    """
    # This is a placeholder implementation.
    # You should replace it with logic that accurately splits the text based on token counts.
    words = user_prompt.split()
    chunks = [' '.join(words[i:i+max_tokens]) for i in range(0, len(words), max_tokens)]
    return chunks

def process_long_text_with_openai(system_prompt, user_prompt):
    """
    Generalized function to process text with OpenAI, including corrections or translations.
    Handles splitting the user_prompt into multiple parts if it exceeds the token limit.
    
    Parameters:
    - system_prompt: The instruction or context to provide to the model.
    - user_prompt: The user input text to process.
    
    Returns:
    - The processed text as a string.
    """
    client = OpenAI()
    max_tokens = 4096  # Adjust based on your use case and model capabilities
    
    # Split the user_prompt into chunks if necessary
    prompts = split_prompt_into_chunks(user_prompt, max_tokens)
    
    completed_texts = []
    for prompt in prompts:
        
        completion = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        completed_texts.append(completion.choices[0].message.content)
    
    # Combine the processed text chunks into a single string
    return "\n".join(completed_texts)

#https://platform.openai.com/docs/guides/speech-to-text/improving-reliability

def generate_corrected_transcript(user_prompt):
    words = ['Example']
    system_prompt = f"""You are a helpful assistant.
    Your task is to correct any spelling discrepancies in the transcribed text.
    
    Make sure that the names of the following words are spelled correctly:
    {", ".join(words)}
    
    Only add necessary punctuation such as periods, commas, and capitalization, and use only the context provided.
    Remove where it says "NOTE: This is where the audio was split, for processing it in chunks..."
    """    

    return process_long_text_with_openai(system_prompt, user_prompt)