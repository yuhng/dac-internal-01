import os

import anthropic
import openai
from dotenv import load_dotenv
from typesafe_sdk import RetryPolicy, TypeSafeClient

# OpenAI
def create_openai_client(*, timeout: float = 120.0, max_retries: int = 2) -> openai.OpenAI:
    """Create a client using OPENAI_API_KEY from the environment or .env"""
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        raise RuntimeError("Set OPENAI_API_KEY in your environment")
    return openai.OpenAI(api_key=api_key, timeout=timeout, max_retries=max_retries)

# JEV Model
def create_jev_client(*, model: str = "jev-latest", timeout: float = 120.0, max_retries: int = 2) -> TypeSafeClient:
    """Create a client using TYPESAFE_API_KEY from the environment or .env. Use it as a context manager to close it."""
    load_dotenv()
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key or not api_key.strip():
        raise RuntimeError("Set TYPESAFE_API_KEY in your environment")
    return TypeSafeClient(api_key=api_key, model=model, timeout=timeout,
                          retry=RetryPolicy(max_retries=max_retries))

# Claude
def create_claude_client(*, timeout: float = 120.0, max_retries: int = 2) -> anthropic.Anthropic:
    """Create a client using ANTHROPIC_API_KEY from the environment or .env"""
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not api_key.strip():
        raise RuntimeError("Set ANTHROPIC_API_KEY in your environment")
    return anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=max_retries)

