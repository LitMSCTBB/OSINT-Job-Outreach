from typing import Optional, Literal
import os
os.environ["TRANSFORMERS_NO_TF"] = "1"
# from transformers import pipeline
from openai import AsyncOpenAI

_local_model = None
openai = AsyncOpenAI()

def get_local_model():
    from transformers import pipeline
    global _local_model
    if _local_model is None:
        # Use a small but capable model for text generation
        _local_model = pipeline('text-generation', model='TinyLlama/TinyLlama-1.1B-Chat-v1.0')
    return _local_model

# create quick prompter function where you can specify provider model and prompt
async def prompt(
    system_prompt: str = "",
    user_prompt: str = "",
    model: Optional[str] = None,
    provider: Literal["openai", "google", "local"] = "openai",
    temperature: float = 0.3,
    max_tokens: int = 1024
) -> str:
    """
    Generic prompt function that supports both OpenAI and Google Gemini models.
    
    Args:
        system_prompt: The system instructions/context
        user_prompt: The actual user query/prompt
        model: Specific model to use (e.g., "gpt-4", "gemini-pro")
                If None, uses default for the provider
        provider: Which AI provider to use ("openai" or "google" or "local")
        temperature: Controls randomness (0-1)
        max_tokens: Maximum number of tokens to generate
    
    Returns:
        Generated text response
    """
    if provider == "openai":
        # Use OpenAI's API
        model = model or os.getenv("OPENAI_MODEL", "gpt-4")
        response = await openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    
    # elif provider == "google":
    #     # Use Google's Gemini API
    #     model = model or os.getenv("GOOGLE_MODEL", "gemini-pro")
        
    #     # Combine system and user prompts for Gemini
    #     # Since Gemini doesn't have a direct system prompt concept
    #     combined_prompt = f"{system_prompt}\n\nUser Request: {user_prompt}"
        
    #     model_instance = genai.GenerativeModel(model)
    #     response = model_instance.generate_content(
    #         contents=combined_prompt,
    #         generation_config=genai.types.GenerationConfig(
    #             temperature=temperature,
    #             max_output_tokens=max_tokens,
    #         )
    #     )
        
    #     return response.text.strip()
    
    elif provider == "local":
        # Use local LLM for text generation
        model = get_local_model()
        
        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\nUser: {user_prompt}\nAssistant:"
        
        # Generate response
        # dumb token override for now
        max_length = full_prompt.count(" ") + 50
        response = model(full_prompt, max_new_tokens=128, num_return_sequences=1)[0]['generated_text']
        
        # Extract just the assistant's response
        return response.split("Assistant:")[-1].strip()
    
    else:
        raise ValueError(f"Unsupported provider: {provider}. Use 'openai', 'google', or 'local'")
