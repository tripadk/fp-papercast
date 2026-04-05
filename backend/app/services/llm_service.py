from __future__ import annotations

import json
import re
from typing import Any

from groq import Groq

from app.core.config import settings
from app.services.podcast_service import generate_podcast_transcript as build_podcast_transcript


def _groq_client() -> Groq:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    return Groq(api_key=settings.groq_api_key)


def _goal_instruction(goal: str) -> str:
    normalized = (goal or "general").strip().lower()
    mapping = {
        "upsc": "Use descriptive, theory-heavy, and long-form explanations with contextual depth.",
        "jee": "Prioritize formulas, numerical reasoning, and step-by-step problem-solving focus.",
        "neet": "Prioritize crisp definitions, diagram-friendly cues, and factual recall points.",
        "cat": "Keep outputs short, logical, and centered on concept clarity.",
    }
    return mapping.get(normalized, "Keep a balanced explanation with clear concepts and practical understanding.")


def _mode_instruction(mode: str) -> str:
    normalized = (mode or "beginner").strip().lower()
    mapping = {
        "beginner": (
            "Use beginner-friendly language, short explanations, and concrete simple examples. "
            "Summary length: short to medium. Quiz difficulty target: easy."
        ),
        "exam_mode": (
            "Use exam-oriented phrasing, high-yield points, and test-style framing. "
            "Summary length: medium. Quiz difficulty target: medium to hard."
        ),
        "deep_learning": (
            "Provide deeper conceptual and technical depth with rigorous detail and nuanced examples. "
            "Summary length: long. Quiz difficulty target: hard."
        ),
        "quick_revision": (
            "Focus on concise revision bullets, key takeaways, and memory anchors. "
            "Summary length: short. Quiz difficulty target: easy to medium."
        ),
    }
    return mapping.get(normalized, mapping["beginner"])


def _generate_structured_learning_bundle(
    text: str,
    podcast_length: str = "standard",
    podcast_style: str = "casual",
    goal: str = "general",
    learning_mode: str = "beginner",
) -> dict[str, Any]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return _fallback_learning_bundle("", podcast_length=podcast_length, podcast_style=podcast_style)

    raw = ""
    try:
        client = _groq_client()
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an academic assistant. Return strict JSON only, no markdown. "
                        f"Learning goal guidance: {_goal_instruction(goal)} "
                        f"Learning mode guidance: {_mode_instruction(learning_mode)}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Analyze this paper and return JSON with keys:\n"
                        "- summary (string)\n"
                        "- study_notes (object with core_idea, key_concepts, key_points, important_results, limitations, applications, quick_revision)\n"
                        "- flashcards (array up to 8 objects with concept, question, answer, hint)\n"
                        "- transcript (string suitable for an educational podcast)\n\n"
                        "Constraints:\n"
                        "- Extract only from the provided paper text; no outside facts.\n"
                        "- No hallucinations or invented details.\n"
                        "- Make flashcards exam-relevant and high-yield.\n"
                        "- For study_notes use this strict style:\n"
                        "  * Core Idea: 2-3 short lines.\n"
                        "  * Key Concepts: bullet format 'concept: explanation' (max 15 words each).\n"
                        "  * Key Points: bullets only, each <= 15 words.\n"
                        "  * Important Results: crisp factual statements.\n"
                        "  * Limitations: short bullets.\n"
                        "  * Applications: real-world uses.\n"
                        "  * Quick Revision: max 5 one-line fact bullets.\n"
                        "- No paragraphs, no filler, no repetition.\n"
                        "- Use simple language.\n"
                        "- Add examples where possible in Key Concepts and Applications.\n"
                        f"- Transcript style: {podcast_style}\n"
                        f"- Transcript length target: {podcast_length}\n\n"
                        f"Paper text:\n{cleaned[:12000]}"
                    ),
                },
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
    except Exception:
        raw = ""

    parsed = _parse_json_object(raw)
    summary = str(parsed.get("summary", "")).strip()
    if not summary:
        summary = _fallback_summary(cleaned)

    notes_raw = parsed.get("study_notes")
    if isinstance(notes_raw, dict):
        study_notes = {
            "core_idea": str(notes_raw.get("core_idea", "")).strip(),
            "key_concepts": str(notes_raw.get("key_concepts", "")).strip(),
            "key_points": str(notes_raw.get("key_points", "")).strip(),
            "important_results": str(notes_raw.get("important_results", "")).strip(),
            "limitations": str(notes_raw.get("limitations", "")).strip(),
            "applications": str(notes_raw.get("applications", "")).strip(),
            "quick_revision": str(notes_raw.get("quick_revision", "")).strip(),
        }
    else:
        study_notes = {}
    if any(
        not study_notes.get(key, "").strip()
        for key in [
            "core_idea",
            "key_concepts",
            "key_points",
            "important_results",
            "limitations",
            "applications",
            "quick_revision",
        ]
    ):
        study_notes = _study_notes_from_summary(summary)
    study_notes = _normalize_study_notes(study_notes)

    flashcards = _parse_flashcards(json.dumps(parsed.get("flashcards", [])), limit=8)
    if not flashcards:
        flashcards = _fallback_exam_flashcards(cleaned, limit=8)

    transcript = str(parsed.get("transcript", "")).strip()
    if not transcript:
        notes = " ".join([segment for segment in cleaned.split(". ")[:4] if segment]).strip()
        transcript = build_podcast_transcript(summary=summary, key_notes=notes)

    return {
        "summary": summary,
        "study_notes": study_notes,
        "flashcards": flashcards,
        "transcript": transcript[:5000],
    }


def generate_summary(text: str, goal: str = "general", learning_mode: str = "beginner"):
    bundle = _generate_structured_learning_bundle(
        text=text,
        podcast_length="standard",
        podcast_style="casual",
        goal=goal,
        learning_mode=learning_mode,
    )
    return str(bundle.get("summary", "")).strip() or _fallback_summary(text or "")

def generate_podcast_transcript(
    text: str,
    summary: str,
    podcast_length: str = "standard",
    podcast_style: str = "casual",
    goal: str = "general",
    learning_mode: str = "beginner",
) -> str:
    cleaned_text = re.sub(r"\s+", " ", text or "").strip()
    notes = " ".join([segment for segment in cleaned_text.split(". ")[:4] if segment]).strip()
    goal_note = f"Study goal: {goal.upper()} - {_goal_instruction(goal)}"
    mode_note = f"Learning mode: {learning_mode.upper()} - {_mode_instruction(learning_mode)}"
    return build_podcast_transcript(summary=summary, key_notes=f"{goal_note}. {mode_note}. {notes}")


def generate_methodology_steps(text: str, goal: str = "general", learning_mode: str = "beginner") -> list[str]:
    content = (text or "").strip()
    if not content:
        return _fallback_methodology_steps("")

    prompt = (
        "You are a research assistant.\n"
        "Extract the key methodological steps of this research paper.\n\n"
        f"Learning goal guidance: {_goal_instruction(goal)}\n\n"
        f"Learning mode guidance: {_mode_instruction(learning_mode)}\n\n"
        "Return them as an ordered JSON list of short step names.\n"
        "Example output:\n"
        "[\n"
        '  "Data Collection",\n'
        '  "Data Preprocessing",\n'
        '  "Feature Engineering",\n'
        '  "Model Training",\n'
        '  "Evaluation",\n'
        '  "Results Analysis"\n'
        "]\n\n"
        f"Paper text:\n{content[:7000]}"
    )

    steps: list[str] = []
    try:
        client = _groq_client()
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": "Extract research workflow steps with high precision."},
                {"role": "user", "content": prompt},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        steps = _parse_steps(raw)
    except Exception:
        steps = []

    if not steps:
        steps = _fallback_methodology_steps(content)
    return steps


def generate_exam_flashcards(
    text: str,
    goal: str = "general",
    learning_mode: str = "beginner",
    limit: int = 8,
) -> list[dict[str, str]]:
    bundle = _generate_structured_learning_bundle(
        text=text,
        podcast_length="standard",
        podcast_style="casual",
        goal=goal,
        learning_mode=learning_mode,
    )
    cards = bundle.get("flashcards", [])
    if not isinstance(cards, list):
        cards = []
    cleaned_cards = []
    for item in cards[: max(1, limit)]:
        if not isinstance(item, dict):
            continue
        concept = str(item.get("concept", "")).strip()
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        hint = str(item.get("hint", "")).strip()
        if concept and question and answer:
            cleaned_cards.append(
                {
                    "concept": concept,
                    "question": question,
                    "answer": answer,
                    "hint": hint,
                }
            )
    if cleaned_cards:
        return cleaned_cards
    return _fallback_exam_flashcards(text, limit=limit)


def generate_learning_bundle(
    text: str,
    podcast_length: str = "standard",
    podcast_style: str = "casual",
    goal: str = "general",
    learning_mode: str = "beginner",
) -> dict[str, Any]:
    return _generate_structured_learning_bundle(
        text=text,
        podcast_length=podcast_length,
        podcast_style=podcast_style,
        goal=goal,
        learning_mode=learning_mode,
    )


def infer_methodology_steps(text: str) -> list[str]:
    return _fallback_methodology_steps(text)


def analyze_paper_bundle(text: str, goal: str = "general", learning_mode: str = "beginner") -> dict[str, Any]:
    content = re.sub(r"\s+", " ", text or "").strip()
    trimmed = content[:8000]
    if not trimmed:
        fallback_summary = _fallback_summary(content)
        return {
            "summary": fallback_summary,
            "key_insights": _insights_from_summary(fallback_summary),
            "study_notes": _study_notes_from_summary(fallback_summary),
            "methodology_steps": _fallback_methodology_steps(content),
            "importance_extraction": _fallback_importance_extraction(fallback_summary, []),
        }

    raw = ""
    try:
        client = _groq_client()
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You analyze research papers for students and return strict JSON only. "
                        "Do not include markdown. "
                        f"Learning goal guidance: {_goal_instruction(goal)} "
                        f"Learning mode guidance: {_mode_instruction(learning_mode)}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Analyze this paper and return JSON with keys:\n"
                        "- summary (string)\n"
                        "- key_insights (array of 4-6 concise strings)\n"
                        "- study_notes (object with core_idea, key_concepts, key_points, important_results, limitations, applications, quick_revision)\n"
                        "- methodology_steps (array of 4-8 short step names)\n\n"
                        "- importance_extraction (object with must_know, important, optional; each is an array of concise points)\n\n"
                        "Prioritize exam-relevant content in must_know first, then important, then optional.\n\n"
                        f"Paper text:\n{trimmed}"
                    ),
                },
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
    except Exception:
        raw = ""

    parsed = _parse_json_object(raw)
    summary = str(parsed.get("summary", "")).strip()
    if not summary:
        summary = _fallback_summary(content)

    key_insights = _parse_string_list(parsed.get("key_insights"), limit=6)
    if not key_insights:
        key_insights = _insights_from_summary(summary)

    notes_raw = parsed.get("study_notes")
    if isinstance(notes_raw, dict):
        study_notes = {
            "core_idea": str(notes_raw.get("core_idea", "")).strip(),
            "key_concepts": str(notes_raw.get("key_concepts", "")).strip(),
            "key_points": str(notes_raw.get("key_points", "")).strip(),
            "important_results": str(notes_raw.get("important_results", "")).strip(),
            "limitations": str(notes_raw.get("limitations", "")).strip(),
            "applications": str(notes_raw.get("applications", "")).strip(),
            "quick_revision": str(notes_raw.get("quick_revision", "")).strip(),
        }
    else:
        study_notes = {}

    if any(
        not study_notes.get(key, "").strip()
        for key in [
            "core_idea",
            "key_concepts",
            "key_points",
            "important_results",
            "limitations",
            "applications",
            "quick_revision",
        ]
    ):
        study_notes = _study_notes_from_summary(summary)
    study_notes = _normalize_study_notes(study_notes)

    methodology_steps = _parse_string_list(parsed.get("methodology_steps"), limit=8)
    if not methodology_steps:
        methodology_steps = _fallback_methodology_steps(content)

    importance_raw = parsed.get("importance_extraction")
    importance_extraction = {
        "must_know": [],
        "important": [],
        "optional": [],
    }
    if isinstance(importance_raw, dict):
        importance_extraction = {
            "must_know": _parse_string_list(importance_raw.get("must_know"), limit=8),
            "important": _parse_string_list(importance_raw.get("important"), limit=8),
            "optional": _parse_string_list(importance_raw.get("optional"), limit=8),
        }

    if not any(importance_extraction.values()):
        importance_extraction = _fallback_importance_extraction(summary, key_insights)

    return {
        "summary": summary,
        "key_insights": key_insights,
        "study_notes": study_notes,
        "methodology_steps": methodology_steps,
        "importance_extraction": importance_extraction,
    }


def methodology_steps_to_mermaid(steps: list[str]) -> str:
    usable = [step.strip() for step in steps if step and step.strip()]
    if not usable:
        usable = _fallback_methodology_steps("")

    lines = ["flowchart LR"]
    node_ids = [chr(65 + idx) if idx < 26 else f"N{idx + 1}" for idx in range(len(usable))]
    for idx, step in enumerate(usable):
        escaped = step.replace("[", "(").replace("]", ")")
        lines.append(f'{node_ids[idx]}["{escaped}"]:::stage')
    for idx in range(len(usable) - 1):
        lines.append(f"{node_ids[idx]} --> {node_ids[idx + 1]}")
    lines.append("linkStyle default stroke:#38bdf8,stroke-width:2px,opacity:0.9")
    lines.append("classDef stage fill:#0f172a,stroke:#38bdf8,color:#e2e8f0,stroke-width:1.5px;")
    return "\n".join(lines)


def answer_question(
    context: str,
    question: str,
    history: list[dict[str, str]] | None = None,
    goal: str = "general",
    learning_mode: str = "beginner",
) -> str:
    history_text = _history_to_text(history or [])
    try:
        client = _groq_client()
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are PaperCast, an AI assistant that helps students understand research papers.\n\n"
                        f"Learning goal guidance: {_goal_instruction(goal)}\n\n"
                        f"Learning mode guidance: {_mode_instruction(learning_mode)}\n\n"
                        "Rules for answering:\n"
                        "1. Base your answer ONLY on the provided paper context.\n"
                        "2. Do not invent information not present in the paper.\n"
                        "3. Keep answers concise and easy to read.\n"
                        "4. Prefer bullet points or short paragraphs.\n"
                        "5. Do NOT ask unnecessary follow-up questions.\n"
                        "6. Do NOT repeat the entire context.\n"
                        "7. If the answer is not in the context, say: "
                        "'The paper does not provide enough information about this.'\n\n"
                        "Tone:\n"
                        "Clear, academic, helpful for students.\n\n"
                        "Example structure:\n"
                        "- Brief explanation\n"
                        "- Bullet points if needed\n"
                        "- Short conclusion if helpful"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Rules:\n"
                        "- Answer only from the paper context provided below.\n"
                        "- Use the chat history only to resolve follow-up references like 'this method' or 'that result'.\n"
                        "- If the paper does not contain the answer, clearly say that the paper does not provide enough information.\n"
                        "- Explain ideas in simple language for students.\n"
                        "- Do not invent citations, results, or background knowledge from outside the paper.\n\n"
                        f"Paper context:\n{context[:12000]}\n\n"
                        f"Chat history:\n{history_text or 'No previous chat.'}\n\n"
                        f"Current question: {question}"
                    ),
                },
            ],
        )
        return response.choices[0].message.content or "I could not generate an answer."
    except Exception:
        return _fallback_chat_answer(context, question)


def _fallback_chat_answer(context: str, question: str) -> str:
    cleaned = re.sub(r"\s+", " ", context or "").strip()
    if not cleaned:
        return "The paper does not provide enough information about this."

    question_tokens = set(re.findall(r"[a-z]{4,}", (question or "").lower()))
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
    if not sentences:
        return "The paper does not provide enough information about this."

    if not question_tokens:
        return sentences[0][:420]

    best_sentence = ""
    best_overlap = 0
    for sentence in sentences[:80]:
        sentence_tokens = set(re.findall(r"[a-z]{4,}", sentence.lower()))
        overlap = len(question_tokens.intersection(sentence_tokens))
        if overlap > best_overlap:
            best_overlap = overlap
            best_sentence = sentence

    if best_overlap == 0:
        return "The paper does not provide enough information about this."
    return best_sentence[:420]


def explain_like_twelve(context: str, summary: str = "") -> str:
    source = summary.strip() or (context or "").strip()
    if not source:
        return "Imagine this paper is teaching one main idea. It explains a problem, a way to solve it, and what happened when they tested it."

    try:
        client = _groq_client()
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Explain research ideas for a 12-year-old student. "
                        "Use plain words, short sentences, and simple examples. "
                        "Keep it concise in 4-6 bullet points."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Explain this paper in simple terms:\n{source[:9000]}",
                },
            ],
        )
        output = (response.choices[0].message.content or "").strip()
        if output:
            return output
    except Exception:
        pass

    return _fallback_explain_like_twelve(source)


def _fallback_explain_like_twelve(source: str) -> str:
    cleaned = re.sub(r"\s+", " ", source).strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
    if not sentences:
        return "This paper tries to solve a hard problem by testing a clear method and checking results."

    picks = sentences[:4]
    bullets = [f"- {sentence[:180]}" for sentence in picks]
    prefix = "Here is the simple version:\n"
    return prefix + "\n".join(bullets)


def _history_to_text(history: list[dict[str, str]]) -> str:
    usable_messages = []
    for message in history[-8:]:
        role = message.get("role", "").strip().lower()
        content = message.get("content", "").strip()
        if role in {"user", "assistant"} and content:
            speaker = "User" if role == "user" else "Assistant"
            usable_messages.append(f"{speaker}: {content}")
    return "\n".join(usable_messages)


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


def _parse_string_list(value: Any, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = [str(item).strip(" -\n\t") for item in value if str(item).strip()]
    return cleaned[:limit]


def _bullets(text: str, max_words: int = 15, max_items: int = 5, enforce_colon: bool = False) -> str:
    raw = str(text or "").replace("\r", "\n")
    lines = []
    for chunk in raw.split("\n"):
        clean = re.sub(r"^\s*[-*•]\s*", "", chunk).strip()
        if not clean:
            continue
        words = clean.split()
        clean = " ".join(words[:max_words]).strip()
        if not clean:
            continue
        if enforce_colon and ":" not in clean:
            clean = f"Concept: {clean}"
        lines.append(clean)

    deduped: list[str] = []
    seen = set()
    for line in lines:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(line)
        if len(deduped) >= max_items:
            break

    return "\n".join([f"- {line}" for line in deduped])


def _normalize_study_notes(notes: dict[str, str]) -> dict[str, str]:
    return {
        "core_idea": _bullets(notes.get("core_idea", ""), max_words=18, max_items=3),
        "key_concepts": _bullets(notes.get("key_concepts", ""), max_words=15, max_items=6, enforce_colon=True),
        "key_points": _bullets(notes.get("key_points", ""), max_words=15, max_items=8),
        "important_results": _bullets(notes.get("important_results", ""), max_words=16, max_items=6),
        "limitations": _bullets(notes.get("limitations", ""), max_words=14, max_items=6),
        "applications": _bullets(notes.get("applications", ""), max_words=15, max_items=6),
        "quick_revision": _bullets(notes.get("quick_revision", ""), max_words=15, max_items=5),
    }


def _insights_from_summary(summary: str) -> list[str]:
    lines = [line.strip() for line in summary.splitlines() if line.strip()]
    insights = [line.strip(" -\t") for line in lines if ":" not in line][:6]
    if insights:
        return insights
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", summary) if s.strip()]
    return sentences[:5]


def _study_notes_from_summary(summary: str) -> dict[str, str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", summary) if s.strip()]

    def pick(default: str, keywords: list[str], offset: int) -> str:
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in keywords):
                return sentence
        return sentences[offset] if len(sentences) > offset else default

    core_line_1 = pick(
        "This paper solves one clear problem using a focused method.",
        ["problem", "challenge", "issue"],
        0,
    )
    core_line_2 = pick(
        "The method is tested and compared using reported evidence.",
        ["method", "approach", "evaluate", "result"],
        1,
    )
    core_line_3 = pick(
        "Main takeaway: practical value depends on context and assumptions.",
        ["conclusion", "takeaway", "implication"],
        2,
    )

    return {
        "core_idea": f"- {core_line_1}\n- {core_line_2}\n- {core_line_3}",
        "key_concepts": (
            "- Core concept: main idea behind the method (example: simple baseline comparison)\n"
            "- Evaluation setup: how performance is measured (example: accuracy or benchmark score)\n"
            "- Assumption boundary: when method may fail (example: out-of-domain data)"
        ),
        "key_points": (
            "- Problem, method, and evidence chain is the main structure.\n"
            "- Compare with baseline before interpreting claims.\n"
            "- Focus on assumptions behind reported gains."
        ),
        "important_results": (
            f"- {pick('Performance change is reported against a baseline.', ['result', 'accuracy', 'performance'], 3)}\n"
            f"- {pick('Evidence supports the main claim under tested settings.', ['finding', 'improv', 'outperform'], 4)}"
        ),
        "limitations": (
            "- Results may depend on dataset scope.\n"
            "- Assumptions can limit generalization.\n"
            "- Real-world variance may reduce performance."
        ),
        "applications": (
            "- Can support domain decision pipelines.\n"
            "- Useful for benchmark-driven optimization.\n"
            "- Example: apply method to similar structured tasks."
        ),
        "quick_revision": (
            "- Core: one method solves one stated problem.\n"
            "- Verify result against baseline metrics.\n"
            "- Check assumptions before generalizing.\n"
            "- Note strongest factual finding.\n"
            "- Remember one practical application."
        ),
    }


def _fallback_summary(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    source = cleaned[:2000]
    if not source:
        source = (
            "The uploaded PDF text could not be extracted clearly, so this fallback summary uses a minimal "
            "description. The paper appears to present a research topic, an approach, and practical implications."
        )

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", source) if s.strip()]
    if not sentences:
        sentences = [source]

    def section(start: int, count: int, default: str) -> str:
        part = " ".join(sentences[start : start + count]).strip()
        return part or default

    research_problem = section(
        0,
        2,
        "The paper investigates an important research problem described in the uploaded document.",
    )
    key_idea = section(
        2,
        2,
        "The key idea is to provide a practical method or framework to address the problem.",
    )
    methodology = section(
        4,
        2,
        "The methodology includes data-driven analysis, experiments, and evaluation of outcomes.",
    )
    applications = section(
        6,
        2,
        "Applications include real-world use in related domains and guidance for future research.",
    )

    return (
        f"Research Problem: {research_problem}\n\n"
        f"Key Idea: {key_idea}\n\n"
        f"Methodology: {methodology}\n\n"
        f"Applications: {applications}"
    )


def _parse_steps(raw: str) -> list[str]:
    if not raw:
        return []

    parsed: Any = None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", raw)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                parsed = None

    if isinstance(parsed, list):
        cleaned = [str(item).strip(" -•\n\t") for item in parsed if str(item).strip()]
        if cleaned:
            return cleaned[:8]

    lines = [
        re.sub(r"^\d+[\.\)]\s*", "", line).strip(" -•\t")
        for line in raw.splitlines()
        if line.strip()
    ]
    lines = [line for line in lines if len(line) > 2]
    return lines[:8]


def _fallback_methodology_steps(text: str) -> list[str]:
    lower = text.lower()
    steps: list[str] = []

    if any(token in lower for token in ["collect", "dataset", "data source", "sampling"]):
        steps.append("Data Collection")
    if any(token in lower for token in ["clean", "preprocess", "normaliz", "tokeniz", "feature"]):
        steps.append("Data Preprocessing")
    if any(token in lower for token in ["model", "train", "optimiz", "learn"]):
        steps.append("Model Training")
    if any(token in lower for token in ["evaluate", "metric", "benchmark", "validation", "test"]):
        steps.append("Evaluation")
    if any(token in lower for token in ["result", "analysis", "discussion", "conclusion"]):
        steps.append("Results Analysis")

    if len(steps) < 3:
        steps = [
            "Data Collection",
            "Data Preprocessing",
            "Model Training",
            "Evaluation",
            "Results",
        ]
    return steps[:8]


def _parse_flashcards(raw: str, limit: int = 8) -> list[dict[str, str]]:
    if not raw:
        return []

    parsed: Any = None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", raw)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                parsed = None

    if not isinstance(parsed, list):
        return []

    cards: list[dict[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        concept = str(item.get("concept", "")).strip()
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        hint = str(item.get("hint", "")).strip()
        if not (concept and question and answer):
            continue
        cards.append(
            {
                "concept": concept,
                "question": question,
                "answer": answer,
                "hint": hint,
            }
        )
        if len(cards) >= limit:
            break

    return cards


def _fallback_exam_flashcards(text: str, limit: int = 8) -> list[dict[str, str]]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]
    cards: list[dict[str, str]] = []
    for idx, sentence in enumerate(sentences[:limit]):
        cards.append(
            {
                "concept": f"Key Point {idx + 1}",
                "question": f"What is the main idea of key point {idx + 1}?",
                "answer": sentence[:260],
                "hint": "Focus on the central claim and why it matters for exams.",
            }
        )

    if not cards:
        cards = [
            {
                "concept": "Core Thesis",
                "question": "What core problem and solution does the paper present?",
                "answer": "The paper presents a central research problem and proposes an approach to solve it.",
                "hint": "Recall problem, method, and result in one line.",
            }
        ]
    return cards[:limit]


def _fallback_learning_bundle(text: str, podcast_length: str = "standard", podcast_style: str = "casual") -> dict[str, Any]:
    summary = _fallback_summary(text)
    notes = _study_notes_from_summary(summary)
    flashcards = _fallback_exam_flashcards(text, limit=8)
    key_notes = " ".join([segment for segment in re.split(r"(?<=[.!?])\s+", text)[:4] if segment]).strip()
    transcript = build_podcast_transcript(summary=summary, key_notes=key_notes)[:5000]
    return {
        "summary": summary,
        "study_notes": notes,
        "flashcards": flashcards,
        "transcript": transcript,
        "podcast_length": podcast_length,
        "podcast_style": podcast_style,
    }


def _fallback_importance_extraction(summary: str, key_insights: list[str]) -> dict[str, list[str]]:
    source_points = [item.strip() for item in key_insights if item and item.strip()]
    if not source_points:
        source_points = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", summary or "")
            if s and s.strip()
        ]

    must_know = source_points[:3]
    important = source_points[3:6]
    optional = source_points[6:9]

    if not must_know:
        must_know = ["Core problem statement and the main proposed approach."]
    if not important:
        important = ["Key supporting findings and evaluation highlights."]
    if not optional:
        optional = ["Background details and extended context for deeper study."]

    return {
        "must_know": must_know,
        "important": important,
        "optional": optional,
    }
