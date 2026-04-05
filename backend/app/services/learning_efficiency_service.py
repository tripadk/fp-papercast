from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.services.concept_service import get_concept_label, normalize_concept
from app.services.spaced_repetition_service import ensure_user_tracker
from app.store import save_state

TARGET_ATTEMPTS_FOR_COMPLETION = 5


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _completion_rate(attempts: int) -> float:
    return min(1.0, float(max(0, attempts)) / float(TARGET_ATTEMPTS_FOR_COMPLETION))


def _normalized_efficiency_score(accuracy: float, completion_rate: float, time_spent: int) -> float:
    effective_minutes = max(1.0, float(time_spent) / 60.0)
    raw_score = (max(0.0, min(1.0, accuracy)) * max(0.0, min(1.0, completion_rate))) / effective_minutes
    return round(max(0.0, min(100.0, raw_score * 100.0)), 2)


def _difficulty_from_score(score: float) -> str:
    if score >= 75:
        return "hard"
    if score >= 45:
        return "medium"
    return "easy"


def _priority_from_score(score: float) -> str:
    if score < 30:
        return "high"
    if score < 60:
        return "medium"
    return "low"


def update_learning_efficiency(store: dict[str, dict], user_id: str, topic: str, accuracy: float, time_spent: int, attempts: int, content_id: str = "", concept_id: str = "") -> dict[str, Any]:
    tracker = ensure_user_tracker(store, user_id)
    learning_efficiency = tracker.setdefault("learning_efficiency", {})
    concept = normalize_concept(user_id=user_id, content_id=content_id or "global", raw_text=topic) if not concept_id else {"concept_id": concept_id, "label": get_concept_label(concept_id, topic)}
    entry = learning_efficiency.setdefault(
        concept["concept_id"],
        {
            "concept_id": concept["concept_id"],
            "topic": concept["label"],
            "total_time_spent": 0,
            "total_attempts": 0,
            "weighted_accuracy_sum": 0.0,
            "quiz_accuracy": 0.0,
            "completion_rate": 0.0,
            "learning_efficiency_score": 0.0,
            "difficulty_adjustment": "easy",
            "priority": "high",
            "updated_at": _now_iso(),
        },
    )

    valid_attempts = max(0, int(attempts))
    valid_time_spent = max(0, int(time_spent))
    valid_accuracy = max(0.0, min(1.0, float(accuracy)))

    entry["total_time_spent"] = int(entry.get("total_time_spent", 0)) + valid_time_spent
    entry["total_attempts"] = int(entry.get("total_attempts", 0)) + valid_attempts
    entry["weighted_accuracy_sum"] = float(entry.get("weighted_accuracy_sum", 0.0)) + (valid_accuracy * max(1, valid_attempts))

    total_attempts = int(entry.get("total_attempts", 0))
    weighted_accuracy_sum = float(entry.get("weighted_accuracy_sum", 0.0))
    quiz_accuracy = weighted_accuracy_sum / max(1, total_attempts)
    completion_rate = _completion_rate(total_attempts)
    score = _normalized_efficiency_score(accuracy=quiz_accuracy, completion_rate=completion_rate, time_spent=int(entry.get("total_time_spent", 0)))

    entry["quiz_accuracy"] = round(quiz_accuracy, 3)
    entry["completion_rate"] = round(completion_rate, 3)
    entry["learning_efficiency_score"] = score
    entry["difficulty_adjustment"] = _difficulty_from_score(score)
    entry["priority"] = _priority_from_score(score)
    entry["updated_at"] = _now_iso()

    tracker["updated_at"] = entry["updated_at"]
    save_state()
    return entry


def get_learning_efficiency_report(store: dict[str, dict], user_id: str) -> dict[str, Any]:
    tracker = ensure_user_tracker(store, user_id)
    learning_efficiency = tracker.get("learning_efficiency", {})
    topics = []
    for concept_id, entry in learning_efficiency.items():
        if not isinstance(entry, dict):
            continue
        topics.append(
            {
                "concept_id": concept_id,
                "topic": str(entry.get("topic", get_concept_label(concept_id, concept_id))),
                "time_spent": int(entry.get("total_time_spent", 0)),
                "quiz_accuracy": float(entry.get("quiz_accuracy", 0.0)),
                "attempts": int(entry.get("total_attempts", 0)),
                "completion_rate": float(entry.get("completion_rate", 0.0)),
                "learning_efficiency_score": float(entry.get("learning_efficiency_score", 0.0)),
                "difficulty_adjustment": str(entry.get("difficulty_adjustment", "easy")),
                "priority": str(entry.get("priority", "high")),
                "updated_at": str(entry.get("updated_at", "")),
            }
        )
    topics.sort(key=lambda item: item.get("learning_efficiency_score", 0.0))
    average_score = round(sum(float(item.get("learning_efficiency_score", 0.0)) for item in topics) / len(topics), 2) if topics else 0.0
    return {"user_id": user_id, "average_learning_efficiency_score": average_score, "prioritized_topics": topics, "updated_at": str(tracker.get("updated_at", _now_iso()))}
