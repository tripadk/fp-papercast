from __future__ import annotations

import json
import re
from typing import Any

from groq import Groq

from app.core.config import settings


def _groq_client() -> Groq:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    return Groq(api_key=settings.groq_api_key)


def _goal_instruction(goal: str) -> str:
    normalized = (goal or "general").strip().lower()
    mapping = {
        "upsc": "Use descriptive, theory-heavy, and long-form explanatory notes.",
        "jee": "Prioritize formulas, numerical focus, and problem-solving structure.",
        "neet": "Prioritize definitions, diagram cues, and factual recall style notes.",
        "cat": "Keep notes short, logical, and concept clarity focused.",
    }
    return mapping.get(normalized, "Use a balanced clarity-first study style.")


def _mode_instruction(mode: str) -> str:
    normalized = (mode or "beginner").strip().lower()
    mapping = {
        "beginner": "Keep notes accessible with simple wording and basic examples.",
        "exam_mode": "Emphasize exam-focused key points and likely testable ideas.",
        "deep_learning": "Include deeper technical nuance and richer conceptual detail.",
        "quick_revision": "Keep notes concise, high-yield, and easy to revise quickly.",
    }
    return mapping.get(normalized, mapping["beginner"])


def extract_top_citations(text: str, limit: int = 10) -> list[str]:
    source = text or ""
    if not source:
        return []

    heading = re.search(r"(?is)\b(?:references|bibliography|works cited)\b\s*[:\n]?", source)
    if not heading:
        return []

    reference_text = source[heading.end() : heading.end() + 18000]
    if not reference_text.strip():
        return []

    candidates = []
    # Pattern 1: Author et al. (2022) - Title
    for match in re.finditer(
        r"([A-Z][A-Za-z\-]+(?:\s+et al\.)?\s*\(\d{4}\)\s*[–\-:]\s*[^.\n]{8,220})",
        reference_text,
    ):
        candidates.append(match.group(1).strip())

    # Pattern 2: Author, 2021, Title
    for match in re.finditer(
        r"([A-Z][A-Za-z\-]+(?:\s+&\s+[A-Z][A-Za-z\-]+)?(?:\s+et al\.)?,\s*(?:19|20)\d{2}[^.\n]{8,220})",
        reference_text,
    ):
        candidates.append(match.group(1).strip())

    # Pattern 3: bracketed refs [1] ...
    for chunk in re.split(r"(?=\[\d+\])", reference_text):
        line = re.sub(r"\s+", " ", chunk).strip(" -•\n\t")
        if len(line) < 22:
            continue
        if not re.search(r"(?:\(\d{4}\)|(?:19|20)\d{2})", line):
            continue
        candidates.append(line[:220])

    deduped = []
    seen = set()
    for entry in candidates:
        key = entry.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
        if len(deduped) >= limit:
            break
    return deduped[:limit]


def generate_study_notes(text: str, goal: str = "general", learning_mode: str = "beginner") -> dict[str, str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return _fallback_study_notes("")

    raw = ""
    try:
        client = _groq_client()
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are helping a student prepare structured study notes from a research paper. "
                        "Return strict JSON only. "
                        f"Learning goal guidance: {_goal_instruction(goal)} "
                        f"Learning mode guidance: {_mode_instruction(learning_mode)}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Generate structured study notes in this format:\n"
                        "Core Idea\n"
                        "Key Concepts (with explanation + example)\n"
                        "Key Points\n"
                        "Important Results\n"
                        "Limitations\n"
                        "Applications\n"
                        "Quick Revision\n\n"
                        "Rules:\n"
                        "- Use bullet points.\n"
                        "- Use short sentences.\n"
                        "- Keep language simple and exam-focused.\n"
                        "- Avoid long paragraphs.\n\n"
                        "Return JSON:\n"
                        "{\n"
                        '  "core_idea": "...",\n'
                        '  "key_concepts": "...",\n'
                        '  "key_points": "...",\n'
                        '  "important_results": "...",\n'
                        '  "limitations": "...",\n'
                        '  "applications": "...",\n'
                        '  "quick_revision": "..."\n'
                        "}\n\n"
                        f"Paper text:\n{cleaned[:14000]}"
                    ),
                },
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
    except Exception:
        raw = ""

    parsed = _parse_json_object(raw)
    if not parsed:
        return _fallback_study_notes(cleaned)

    notes = {
        "core_idea": str(parsed.get("core_idea", "")).strip(),
        "key_concepts": str(parsed.get("key_concepts", "")).strip(),
        "key_points": str(parsed.get("key_points", "")).strip(),
        "important_results": str(parsed.get("important_results", "")).strip(),
        "limitations": str(parsed.get("limitations", "")).strip(),
        "applications": str(parsed.get("applications", "")).strip(),
        "quick_revision": str(parsed.get("quick_revision", "")).strip(),
    }
    if any(not value for value in notes.values()):
        return _fallback_study_notes(cleaned)
    return notes


def _parse_json_object(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def _fallback_study_notes(text: str) -> dict[str, str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    def part(start: int, fallback: str) -> str:
        chunk = " ".join(sentences[start : start + 2]).strip()
        return chunk or fallback

    return {
        "core_idea": part(0, "- The paper solves one clear problem with a focused method."),
        "key_concepts": part(
            2,
            "- Concept 1: Short explanation.\n- Example: Simple scenario to remember it.",
        ),
        "key_points": part(
            4,
            "- Point 1: Main method insight.\n- Point 2: Baseline comparison insight.",
        ),
        "important_results": part(6, "- Reported results show measurable changes in tested settings."),
        "limitations": part(6, "- Limited data/scope.\n- Assumptions may not hold in all cases."),
        "applications": part(8, "- Application in real systems.\n- Example: domain-specific usage."),
        "quick_revision": "- Core in one line.\n- Top 3 facts.\n- One key limitation.\n- One practical use.",
    }
