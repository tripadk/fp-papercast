from __future__ import annotations

import json
import logging
import re
from typing import Any

from groq import Groq

from app.core.config import settings

logger = logging.getLogger(__name__)


def _groq_client() -> Groq:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    return Groq(api_key=settings.groq_api_key)


def _clip(text: str, limit: int = 200) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:limit]


def _fallback_text(source: str, default: str) -> str:
    cleaned = re.sub(r"\s+", " ", source or "").strip()
    if not cleaned:
        return default
    return cleaned[:400]


def generate_response(
    prompt: str,
    system_prompt: str = "You are a helpful research assistant.",
    *,
    max_tokens: int = 800,
    fallback: str = "I could not generate a response right now.",
) -> str:
    print(f"[llm][prompt] {_clip(prompt)}")
    try:
        client = _groq_client()
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        content = (response.choices[0].message.content or "").strip()
        if not content:
            content = fallback
        print(f"[llm][response] {_clip(content)}")
        return content
    except Exception as exc:
        logger.exception("Groq request failed")
        print(f"[llm][error] {type(exc).__name__}: {exc}")
        print(f"[llm][response] {_clip(fallback)}")
        return fallback


def answer_question(
    context: str,
    question: str,
    history: list[dict[str, str]] | None = None,
    goal: str = "general",
    learning_mode: str = "beginner",
) -> str:
    del history, goal, learning_mode
    paper_text = (context or "").strip() or (
        "Mock paper content: This paper studies a method, reports some results, and discusses limitations."
    )
    prompt = (
        "Answer the question based on the paper. If not found, say 'Not in paper'.\n\n"
        f"Paper:\n{paper_text[:6000]}\n\n"
        f"Question:\n{(question or '').strip()}"
    )
    fallback = "Not in paper"
    return generate_response(
        prompt,
        system_prompt="Answer only from the paper. If the paper does not contain it, reply exactly: Not in paper.",
        max_tokens=300,
        fallback=fallback,
    )


def generate_podcast_script(paper_content: str) -> str:
    source = (paper_content or "").strip() or (
        "Mock paper content: This paper proposes a simple method, evaluates it, and shares the main finding."
    )
    prompt = (
        "Convert this paper into a short 2-person podcast conversation (Host & Expert). Keep it simple.\n\n"
        f"Paper:\n{source[:7000]}"
    )
    fallback = (
        "Host: What is this paper about?\n"
        "Expert: It explains a research idea, how it was tested, and what the main result was.\n"
        "Host: Why does that matter?\n"
        "Expert: It helps readers understand the method, the evidence, and the practical takeaway."
    )
    return generate_response(
        prompt,
        system_prompt="Write a short, clear podcast dialogue using only Host and Expert.",
        max_tokens=500,
        fallback=fallback,
    )


def analyze_learning_progress(progress_payload: dict[str, Any]) -> str:
    payload = progress_payload or {
        "progress": {"completed_topics": 0, "average_score": 0},
        "weak_topics": [],
    }
    prompt = (
        "Analyze this learning progress and give strengths, weaknesses, and suggestions.\n\n"
        f"Data:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    fallback = (
        "Strengths: The learner is engaging with the system.\n"
        "Weaknesses: Some topics still need reinforcement.\n"
        "Suggestions: Review weak topics first, then practice with short quizzes."
    )
    return generate_response(
        prompt,
        system_prompt="Give a short learning analysis in plain text with strengths, weaknesses, and suggestions.",
        max_tokens=250,
        fallback=fallback,
    )


def explain_like_twelve(context: str, summary: str = "") -> str:
    source = (summary or "").strip() or (context or "").strip()
    prompt = f"Explain this paper in very simple words for a 12-year-old:\n\n{source[:5000]}"
    fallback = "This paper tries to solve a problem, explains one method, and shows what happened after testing it."
    return generate_response(
        prompt,
        system_prompt="Explain in plain, short sentences. Keep it easy to understand.",
        max_tokens=200,
        fallback=fallback,
    )


def generate_learning_bundle(
    text: str,
    podcast_length: str = "standard",
    podcast_style: str = "casual",
    goal: str = "general",
    learning_mode: str = "beginner",
) -> dict[str, Any]:
    del podcast_length, podcast_style, goal, learning_mode
    source = (text or "").strip()
    summary = generate_response(
        f"Summarize this paper in simple study notes.\n\nPaper:\n{source[:7000]}",
        system_prompt="Write a short, clear summary for a student.",
        max_tokens=400,
        fallback=_fallback_text(source, "This paper describes a method, its results, and its main takeaway."),
    )
    transcript = generate_podcast_script(source)
    return {
        "summary": summary,
        "study_notes": {
            "core_idea": summary,
            "key_concepts": "Concepts are summarized from the uploaded paper.",
            "key_points": summary,
            "important_results": "Main results are included in the summary.",
            "limitations": "Limitations should be checked in the paper text.",
            "applications": "Applications depend on the paper topic.",
            "quick_revision": summary,
        },
        "flashcards": [],
        "transcript": transcript,
    }


def infer_methodology_steps(text: str) -> list[str]:
    source = (text or "").lower()
    steps: list[str] = []
    if "data" in source:
        steps.append("Collect data")
    if "method" in source or "model" in source:
        steps.append("Apply method")
    if "result" in source or "evaluation" in source:
        steps.append("Evaluate results")
    if not steps:
        steps = ["Read paper", "Identify method", "Review results"]
    return steps


def methodology_steps_to_mermaid(steps: list[str]) -> str:
    cleaned = [step.strip() for step in steps if step and step.strip()] or ["Read paper", "Review method", "Check result"]
    lines = ["flowchart LR"]
    for index, step in enumerate(cleaned):
        node = chr(65 + index)
        lines.append(f'{node}["{step}"]')
        if index > 0:
            prev = chr(64 + index)
            lines.append(f"{prev} --> {node}")
    return "\n".join(lines)
