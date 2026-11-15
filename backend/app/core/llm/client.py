import os

import openai
from dotenv import load_dotenv


def create_llm_client(*, timeout: float = 120.0, max_retries: int = 2) -> openai.OpenAI:
    """Create a client using OPENAI_API_KEY from the environment or .env"""
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        raise RuntimeError("Set OPENAI_API_KEY in your environment")
    return openai.OpenAI(api_key=api_key, timeout=timeout, max_retries=max_retries)
