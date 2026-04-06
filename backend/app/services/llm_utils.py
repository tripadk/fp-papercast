from __future__ import annotations

import logging
from typing import Any

from groq import Groq
from app.core.config import settings


logger = logging.getLogger(__name__)


def _groq_client() -> Groq:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY not configured in .env")
    return Groq(api_key=settings.groq_api_key)


def groq_chat(prompt: str, system_prompt: str = "You are a helpful research assistant.", model: str = "llama3.1-8b-instant", max_tokens: int = 1000) -> str:
    """
    Simple, robust Groq chat completion with error handling.
    """
    try:
        client = _groq_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"Groq API error: {str(e)}")
        return "Sorry, I encountered an issue processing your request."


def groq_chat_structured(prompt: str, system_prompt: str, response_format: dict[str, Any]) -> dict[str, Any]:
    """
    For structured outputs like podcast dialogue.
    """
    json_prompt = f"Respond with valid JSON matching this schema: {response_format}\\n\\n{prompt}"
    try:
        result = groq_chat(json_prompt, system_prompt)
        import json
        parsed = json.loads(result)
        return parsed
    except:
        return response_format

