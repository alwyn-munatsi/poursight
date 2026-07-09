"""Shared Groq client. Groq's API is OpenAI-compatible, so both LLM stages
use the openai SDK pointed at Groq's endpoint rather than a bespoke client.
"""

from openai import OpenAI

from app import config

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def get_client() -> OpenAI:
    return OpenAI(api_key=config.GROQ_API_KEY, base_url=GROQ_BASE_URL)
