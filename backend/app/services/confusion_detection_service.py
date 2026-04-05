from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any

from app.services.concept_service import get_concept_label, normalize_concept
from app.services.llm_service import explain_like_twelve, infer_methodology_steps
from app.store import save_state

WRONG_ANSWER_WINDOW = 5
WRONG_ANSWER_THRESHOLD = 3
SIMILAR_QUESTION_WINDOW = 6
SIMILAR_QUESTION_THRESHOLD = 2
QUESTION_SIMILARITY_THRESHOLD = 0.6
LONG_RESPONSE_TIME_SECONDS = 45.0


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", (text or "").lower()))


def _jaccard_similarity(a: str, b: str) -> float:
    left = _tokenize(a)
    right = _tokenize(b)
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / len(left.union(right))


def _ensure_state(store: dict[str, dict], user_email: str, content_id: str, concept_id: str, topic: str) -> dict[str, Any]:
    user_state = store.setdefault(user_email, {"contents": {}, "updated_at": _now_iso()})
    contents = user_state.setdefault("contents", {})
    content_state = contents.setdefault(content_id, {"topics": {}, "updated_at": _now_iso()})
    topic_state = content_state.setdefault("topics", {}).setdefault(
        concept_id,
        {
            "concept_id": concept_id,
            "topic": topic,
            "topic_status": "clear",
            "interactions": [],
            "wrong_answer_count": 0,
            "similar_question_count": 0,
            "long_response_count": 0,
            "actions": {"simpler_explanation": "", "real_life_example": "", "step_by_step_breakdown": []},
            "updated_at": _now_iso(),
        },
    )
    if topic:
        topic_state["topic"] = topic
    return topic_state


def _count_wrong_answers(interactions: list[dict[str, Any]]) -> int:
    return sum(1 for item in interactions[-WRONG_ANSWER_WINDOW:] if item.get("is_correct") is False)


def _count_similar_questions(interactions: list[dict[str, Any]], new_question: str) -> int:
    recent = interactions[-SIMILAR_QUESTION_WINDOW:]
    return sum(1 for item in recent if str(item.get("question", "")).strip() and _jaccard_similarity(str(item.get("question", "")), new_question) >= QUESTION_SIMILARITY_THRESHOLD)


def _count_long_response(interactions: list[dict[str, Any]]) -> int:
    return sum(1 for item in interactions[-SIMILAR_QUESTION_WINDOW:] if float(item.get("response_time_seconds", 0.0)) >= LONG_RESPONSE_TIME_SECONDS)


def _build_real_life_example(topic: str, paper_record: dict[str, Any]) -> str:
    study_notes = paper_record.get("study_notes", {}) if isinstance(paper_record, dict) else {}
    applications = str(study_notes.get("applications", "")).strip() if isinstance(study_notes, dict) else ""
    for line in applications.splitlines():
        cleaned = re.sub(r"^\s*[-*]\s*", "", line).strip()
        if cleaned:
            return cleaned
    return f"Real-life example: Treat '{topic}' as a skill learned from simple cases before harder ones."


def _build_step_by_step_breakdown(topic: str, paper_record: dict[str, Any]) -> list[str]:
    paper_text = str(paper_record.get("text", "")).strip() if isinstance(paper_record, dict) else ""
    steps = [str(item).strip() for item in infer_methodology_steps(paper_text) if str(item).strip()]
    return steps[:6] if steps else [f"Define {topic}.", "Work through one example.", "Check common mistakes.", "Retry one short question."]


def _build_actions(topic: str, paper_record: dict[str, Any]) -> dict[str, Any]:
    paper_text = str(paper_record.get("text", "")).strip() if isinstance(paper_record, dict) else ""
    paper_summary = str(paper_record.get("summary", "")).strip() if isinstance(paper_record, dict) else ""
    return {
        "simpler_explanation": explain_like_twelve(context=paper_text, summary=paper_summary),
        "real_life_example": _build_real_life_example(topic, paper_record),
        "step_by_step_breakdown": _build_step_by_step_breakdown(topic, paper_record),
    }


def update_confusion_status(
    store: dict[str, dict],
    paper_store: dict[str, dict],
    user_email: str,
    content_id: str,
    topic: str,
    question: str,
    is_correct: bool,
    response_time_seconds: float,
    concept_id: str = "",
) -> dict[str, Any]:
    concept = normalize_concept(user_id=user_email, content_id=content_id, raw_text=topic or question, aliases=[question, topic]) if not concept_id else {"concept_id": concept_id, "label": get_concept_label(concept_id, topic or question)}
    topic_state = _ensure_state(store=store, user_email=user_email, content_id=content_id, concept_id=concept["concept_id"], topic=concept["label"])
    interactions = topic_state.get("interactions", [])
    interactions.append({"question": question.strip(), "is_correct": bool(is_correct), "response_time_seconds": max(0.0, float(response_time_seconds)), "timestamp": _now_iso()})
    topic_state["interactions"] = interactions[-50:]

    wrong_count = _count_wrong_answers(topic_state["interactions"])
    similar_count = _count_similar_questions(topic_state["interactions"][:-1], question)
    long_response_count = _count_long_response(topic_state["interactions"])

    wrong_flag = wrong_count >= WRONG_ANSWER_THRESHOLD
    similar_flag = similar_count >= SIMILAR_QUESTION_THRESHOLD
    long_response_flag = float(response_time_seconds) >= LONG_RESPONSE_TIME_SECONDS
    is_confused = wrong_flag or similar_flag or long_response_flag

    topic_state["topic_status"] = "confused" if is_confused else "clear"
    topic_state["wrong_answer_count"] = wrong_count
    topic_state["similar_question_count"] = similar_count
    topic_state["long_response_count"] = long_response_count
    topic_state["actions"] = _build_actions(topic=concept["label"], paper_record=paper_store.get(content_id, {})) if is_confused else {"simpler_explanation": "", "real_life_example": "", "step_by_step_breakdown": []}
    topic_state["updated_at"] = _now_iso()
    store[user_email]["updated_at"] = topic_state["updated_at"]
    save_state()

    return {
        "concept_id": concept["concept_id"],
        "topic": concept["label"],
        "topic_status": topic_state["topic_status"],
        "signals": {
            "repeated_wrong_answers": wrong_flag,
            "repeated_similar_questions": similar_flag,
            "long_response_time": long_response_flag,
        },
        "wrong_answer_count": wrong_count,
        "similar_question_count": similar_count,
        "long_response_count": long_response_count,
        "actions": topic_state["actions"],
        "updated_at": topic_state["updated_at"],
    }


def get_confusion_status(store: dict[str, dict], user_email: str, content_id: str) -> list[dict[str, Any]]:
    user_state = store.get(user_email, {})
    content_state = user_state.get("contents", {}).get(content_id, {}) if isinstance(user_state, dict) else {}
    topics = content_state.get("topics", {}) if isinstance(content_state, dict) else {}
    result: list[dict[str, Any]] = []
    for concept_id, topic_state in topics.items():
        if not isinstance(topic_state, dict):
            continue
        result.append(
            {
                "concept_id": concept_id,
                "topic": str(topic_state.get("topic", "")),
                "topic_status": str(topic_state.get("topic_status", "clear")),
                "signals": {
                    "repeated_wrong_answers": int(topic_state.get("wrong_answer_count", 0)) >= WRONG_ANSWER_THRESHOLD,
                    "repeated_similar_questions": int(topic_state.get("similar_question_count", 0)) >= SIMILAR_QUESTION_THRESHOLD,
                    "long_response_time": int(topic_state.get("long_response_count", 0)) > 0,
                },
                "wrong_answer_count": int(topic_state.get("wrong_answer_count", 0)),
                "similar_question_count": int(topic_state.get("similar_question_count", 0)),
                "long_response_count": int(topic_state.get("long_response_count", 0)),
                "actions": topic_state.get("actions", {}),
                "updated_at": str(topic_state.get("updated_at", "")),
            }
        )
    result.sort(key=lambda item: (item.get("topic_status") != "confused", item.get("topic", "")))
    return result
