from __future__ import annotations

import json
from typing import Any

from groq import Groq

from app.core.config import settings


def _groq_client() -> Groq:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    return Groq(api_key=settings.groq_api_key)


def _lang_name(language: str) -> str:
    normalized = (language or "english").strip().lower()
    if normalized == "hindi":
        return "Hindi"
    return "English"


def translate_text(text: str, output_language: str = "english") -> str:
    source = (text or "").strip()
    if not source:
        return ""
    if (output_language or "english").strip().lower() == "english":
        return source

    try:
        client = _groq_client()
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise translator. Translate content faithfully while preserving meaning and structure."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Translate the following text to {_lang_name(output_language)}:\n\n{source[:14000]}",
                },
            ],
        )
        translated = (response.choices[0].message.content or "").strip()
        return translated or source
    except Exception:
        return source


def translate_list(items: list[str], output_language: str = "english") -> list[str]:
    if not items:
        return []
    if (output_language or "english").strip().lower() == "english":
        return items

    payload = [str(item) for item in items]
    try:
        client = _groq_client()
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": "Translate the JSON array values only and return strict JSON array output.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Translate this JSON array to {_lang_name(output_language)} and return only JSON:\n"
                        f"{json.dumps(payload, ensure_ascii=False)}"
                    ),
                },
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            cleaned = [str(item).strip() for item in parsed if str(item).strip()]
            if cleaned:
                return cleaned
    except Exception:
        pass
    return payload


def translate_study_notes(notes: dict[str, str], output_language: str = "english") -> dict[str, str]:
    if not notes:
        return {}
    if (output_language or "english").strip().lower() == "english":
        return notes

    result: dict[str, str] = {}
    for key, value in notes.items():
        result[key] = translate_text(str(value), output_language)
    return result


def translate_related_papers(
    papers: list[dict[str, Any]],
    output_language: str = "english",
) -> list[dict[str, Any]]:
    if not papers:
        return []
    if (output_language or "english").strip().lower() == "english":
        return papers

    translated: list[dict[str, Any]] = []
    for paper in papers:
        if not isinstance(paper, dict):
            continue
        translated.append(
            {
                "title": translate_text(str(paper.get("title", "")), output_language),
                "authors": str(paper.get("authors", "")),
                "summary": translate_text(str(paper.get("summary", "")), output_language),
                "link": str(paper.get("link", "")),
            }
        )
    return translated

