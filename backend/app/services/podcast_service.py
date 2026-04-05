from __future__ import annotations

import re
from typing import Literal

SECTION_TITLES = [
    "Introduction",
    "Research Problem",
    "Methodology",
    "Results",
    "Real-world Applications",
    "Conclusion",
]


def generate_podcast_transcript(summary: str, key_notes: str = "") -> str:
    cleaned_summary = re.sub(r"\s+", " ", summary or "").strip()
    cleaned_notes = re.sub(r"\s+", " ", key_notes or "").strip()
    if not cleaned_summary:
        cleaned_summary = "This paper presents a meaningful research contribution."
    if not cleaned_notes:
        cleaned_notes = "The methodology and results sections describe the core workflow and findings."

    transcript = f"""
Host: Welcome to today's PaperCast research breakdown.
Expert: Today we explore a paper discussing:
{cleaned_summary}

Host: Great. Let's walk through the key ideas in a simple way.
Expert: Absolutely. Here are the core notes from the paper:
{cleaned_notes}

Host: First, what problem are the researchers solving?
Expert: The paper targets a practical research challenge and explains why existing approaches are not sufficient.

Host: How does the methodology work?
Expert: The method follows a structured pipeline that includes data preparation, modeling or analysis, and evaluation.

Host: What did the results show?
Expert: The results indicate measurable improvements and highlight where the approach performs best.

Host: Where can this be applied in the real world?
Expert: The findings can support real-world decision-making and provide direction for future research extensions.

Host: Final takeaway for students?
Expert: Focus on the research question, the method choices, and how strongly the evidence supports the conclusions.
"""
    return transcript.strip()[:5000]


def generate_podcast_chapters(transcript: str) -> list[dict[str, str]]:
    words = max(1, len(re.findall(r"\b\w+\b", transcript)))
    total_seconds = int((words / 150.0) * 60)
    weights = [0.12, 0.18, 0.20, 0.20, 0.17, 0.13]

    chapters: list[dict[str, str]] = []
    elapsed = 0
    for title, weight in zip(SECTION_TITLES, weights, strict=False):
        chapters.append({"time": _format_timestamp(elapsed), "title": title})
        elapsed += int(total_seconds * weight)

    if chapters:
        chapters[0]["time"] = "00:00"
    return chapters


def generate_timestamped_sentences(transcript: str) -> list[dict[str, str | float]]:
    normalized = re.sub(r"\s+", " ", (transcript or "").replace("\n", " ")).strip()
    if not normalized:
        return []

    raw_sentences = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+", normalized) if chunk.strip()]
    if not raw_sentences:
        raw_sentences = [normalized]

    # Keep readable units: merge very short fragments into the previous sentence.
    sentences: list[str] = []
    for sentence in raw_sentences:
        if sentences and len(sentence.split()) < 4:
            sentences[-1] = f"{sentences[-1]} {sentence}".strip()
        else:
            sentences.append(sentence)

    weights = [max(1, len(re.findall(r"\b\w+\b", sentence))) for sentence in sentences]
    total_weight = sum(weights) or 1
    total_words = sum(weights)
    total_seconds = max(6.0, (total_words / 150.0) * 60.0)

    elapsed = 0.0
    segments: list[dict[str, str | float]] = []
    for idx, sentence in enumerate(sentences):
        if idx == len(sentences) - 1:
            start_time = elapsed
        else:
            start_time = elapsed
            elapsed += total_seconds * (weights[idx] / total_weight)

        segments.append(
            {
                "time": _format_timestamp(int(start_time)),
                "start_seconds": round(start_time, 2),
                "text": sentence,
            }
        )

    return segments


def _format_timestamp(seconds: int) -> str:
    mm = max(0, seconds) // 60
    ss = max(0, seconds) % 60
    return f"{mm:02d}:{ss:02d}"
