from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from app.services.concept_service import get_concept_label
from app.services.event_ledger_service import rebuild_user_tracker_from_events, record_learning_outcome
from app.store import save_state


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _priority_from_signals(mastery: float, confusion: float, retention: float) -> str:
    if confusion >= 60 or retention <= 45 or mastery <= 35:
        return "high"
    if confusion >= 35 or retention <= 65 or mastery <= 70:
        return "medium"
    return "low"


def _goal_adaptation(goal: str, mastery: float, confusion: float) -> dict[str, str]:
    level = "advanced" if mastery >= 70 and confusion < 35 else "simplified"
    mapping = {
        "upsc": "descriptive, theory-heavy, long explanations",
        "jee": "formula-driven, problem-solving, numerical focus",
        "neet": "definition-first, diagram cues, factual recall",
        "cat": "short, logical, concept-clarity focused",
        "general": "balanced conceptual explanation",
    }
    return {"goal": goal, "style": mapping.get(goal, mapping["general"]), "level": level}


def recommend_mode_from_topic_state(topic_state: dict[str, Any]) -> str:
    confusion = float(topic_state.get("confusion_level", 0.0))
    retention = float(topic_state.get("retention_score", 0.0))
    mastery = float(topic_state.get("mastery_level", 0.0))
    if confusion >= 70:
        return "flashcards"
    if retention <= 45:
        return "notes"
    if mastery >= 80:
        return "quiz"
    return "audio"


def _ensure_learning_state_bucket(learning_store: dict[str, dict], user_id: str) -> dict[str, Any]:
    tracker = learning_store.setdefault(user_id, {})
    tracker.setdefault("topics_studied", {})
    tracker.setdefault("quiz_performance", {})
    tracker.setdefault("weak_topics", {})
    tracker.setdefault("strong_topics", {})
    tracker.setdefault("recall_performance", {})
    tracker.setdefault("learning_efficiency", {})
    tracker.setdefault("revision_schedule", {})
    tracker.setdefault("reassessment_queue", {})
    tracker.setdefault("intervention_history", {})
    tracker.setdefault("updated_at", _now_iso())
    state = tracker.setdefault("learning_state", {"goal": "general", "topics": {}, "updated_at": _now_iso()})
    state.setdefault("goal", "general")
    state.setdefault("topics", {})
    state.setdefault("updated_at", _now_iso())
    return tracker


def initialize_learning_state_for_content(
    learning_store: dict[str, dict],
    user_id: str,
    content_id: str,
    graph_payload: dict[str, Any],
    goal_resolver: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    tracker = _ensure_learning_state_bucket(learning_store, user_id)
    goal = "general"
    if goal_resolver:
        try:
            goal = str(goal_resolver(user_id) or "general").strip().lower()
        except Exception:
            goal = "general"
    topics_state = tracker.setdefault("learning_state", {}).setdefault("topics", {})
    for topic in graph_payload.get("graph", {}).get("topics", []):
        if not isinstance(topic, dict):
            continue
        for concept_item in topic.get("concept_items", []):
            if not isinstance(concept_item, dict):
                continue
            concept_id = str(concept_item.get("concept_id", "")).strip()
            if not concept_id:
                continue
            topics_state.setdefault(
                concept_id,
                {
                    "concept_id": concept_id,
                    "topic": str(concept_item.get("label", concept_id)),
                    "content_id": content_id,
                    "mastery_level": 0.0,
                    "confusion_level": 0.0,
                    "retention_score": 0.0,
                    "priority": "high",
                    "attempts": 0,
                    "accuracy": 0.0,
                    "goal_adaptation": _goal_adaptation(goal, 0.0, 0.0),
                    "next_mode_hint": "notes",
                    "prerequisites": [str(item).strip() for item in concept_item.get("prerequisites", []) if str(item).strip()],
                    "difficulty_level": str(concept_item.get("difficulty_level", "medium")),
                    "reassessment_due_at": "",
                },
            )
    tracker["updated_at"] = _now_iso()
    save_state()
    return tracker["learning_state"]


def refresh_learning_state(
    learning_store: dict[str, dict],
    confusion_store: dict[str, dict],
    user_id: str,
    goal_resolver: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    tracker = _ensure_learning_state_bucket(learning_store, user_id)
    rebuild_user_tracker_from_events(tracker=tracker, user_id=user_id)
    goal = "general"
    if goal_resolver:
        try:
            goal = str(goal_resolver(user_id) or "general").strip().lower()
        except Exception:
            goal = "general"
    if goal not in {"upsc", "jee", "neet", "cat", "general"}:
        goal = "general"

    quiz_perf = tracker.get("quiz_performance", {})
    weak_topics = tracker.get("weak_topics", {})
    strong_topics = tracker.get("strong_topics", {})
    recall_perf = tracker.get("recall_performance", {})
    efficiency = tracker.get("learning_efficiency", {})
    reassessment_queue = tracker.get("reassessment_queue", {})
    previous_topics = tracker.get("learning_state", {}).get("topics", {})

    confusion_topics = confusion_store.get(user_id, {}).get("contents", {}) if isinstance(confusion_store.get(user_id, {}), dict) else {}
    confusion_map: dict[str, dict[str, Any]] = {}
    for content_state in confusion_topics.values():
        if not isinstance(content_state, dict):
            continue
        for concept_id, state in (content_state.get("topics", {}) or {}).items():
            if isinstance(state, dict):
                confusion_map[str(concept_id)] = state

    concept_keys: set[str] = set()
    for source in [quiz_perf, weak_topics, strong_topics, recall_perf, efficiency, confusion_map, previous_topics]:
        if isinstance(source, dict):
            concept_keys.update(str(key).strip() for key in source.keys() if str(key).strip())

    topics_payload: dict[str, dict[str, Any]] = {}
    for concept_id in concept_keys:
        quiz_entry = quiz_perf.get(concept_id, {}) if isinstance(quiz_perf, dict) else {}
        recall_entry = recall_perf.get(concept_id, {}) if isinstance(recall_perf, dict) else {}
        weak_entry = weak_topics.get(concept_id, {}) if isinstance(weak_topics, dict) else {}
        strong_entry = strong_topics.get(concept_id, {}) if isinstance(strong_topics, dict) else {}
        efficiency_entry = efficiency.get(concept_id, {}) if isinstance(efficiency, dict) else {}
        confusion_entry = confusion_map.get(concept_id, {}) if isinstance(confusion_map, dict) else {}
        previous_entry = previous_topics.get(concept_id, {}) if isinstance(previous_topics, dict) else {}

        attempts = int(quiz_entry.get("attempts", 0))
        accuracy = float(quiz_entry.get("accuracy", 0.0)) * 100.0
        if attempts == 0:
            recall_attempts = int(recall_entry.get("correct", 0)) + int(recall_entry.get("incorrect", 0))
            attempts = recall_attempts
            accuracy = (float(recall_entry.get("correct", 0)) / max(1, recall_attempts)) * 100.0 if recall_attempts else 0.0

        efficiency_score = float(efficiency_entry.get("learning_efficiency_score", 0.0))
        weak_severity = float(weak_entry.get("severity", 0.0))
        strong_confidence = float(strong_entry.get("confidence", 0.0))
        wrong = int(confusion_entry.get("wrong_answer_count", 0))
        similar = int(confusion_entry.get("similar_question_count", 0))
        long_resp = int(confusion_entry.get("long_response_count", 0))

        confusion_raw = (6.0 * wrong) + (4.0 * similar) + (3.0 * long_resp) + (8.0 * weak_severity) - (5.0 * strong_confidence)
        confusion_level = _clamp(confusion_raw)
        retention_base = accuracy if attempts > 0 else 35.0
        retention_score = _clamp(retention_base + min(25.0, attempts * 2.0) - min(30.0, confusion_level * 0.3))
        mastery_level = _clamp((0.50 * accuracy) + (0.30 * efficiency_score) + (5.0 * strong_confidence) - (0.20 * confusion_level) - (3.0 * weak_severity))
        previous_mastery = float(previous_entry.get("mastery_level", mastery_level))

        if previous_entry and previous_mastery != mastery_level:
            last_mode = str(previous_entry.get("next_mode_hint", "notes"))
            response_time = float(efficiency_entry.get("avg_response_time_seconds", 0.0))
            record_learning_outcome(
                user_id=user_id,
                content_id=str(previous_entry.get("content_id", "")),
                concept_id=concept_id,
                mode_used=last_mode,
                improvement_score=round(mastery_level - previous_mastery, 2),
                time_taken=max(1.0, response_time),
                before_mastery=round(previous_mastery, 2),
                after_mastery=round(mastery_level, 2),
            )

        priority = _priority_from_signals(mastery_level, confusion_level, retention_score)
        display_topic = (
            str(quiz_entry.get("topic") or recall_entry.get("topic") or weak_entry.get("concept") or strong_entry.get("concept") or efficiency_entry.get("topic") or previous_entry.get("topic") or get_concept_label(concept_id, concept_id))
            .strip()
        )

        topic_state = {
            "concept_id": concept_id,
            "topic": display_topic,
            "content_id": str(previous_entry.get("content_id", "")),
            "mastery_level": round(mastery_level, 2),
            "confusion_level": round(confusion_level, 2),
            "retention_score": round(retention_score, 2),
            "priority": priority,
            "attempts": attempts,
            "accuracy": round(accuracy, 2),
            "goal_adaptation": _goal_adaptation(goal, mastery_level, confusion_level),
            "prerequisites": [str(item).strip() for item in previous_entry.get("prerequisites", []) if str(item).strip()],
            "difficulty_level": str(previous_entry.get("difficulty_level", "medium")),
            "reassessment_due_at": str((reassessment_queue.get(concept_id, {}) or {}).get("due_at", previous_entry.get("reassessment_due_at", ""))),
        }
        topic_state["next_mode_hint"] = recommend_mode_from_topic_state(topic_state)
        topics_payload[concept_id] = topic_state

    tracker["learning_state"] = {"goal": goal, "topics": topics_payload, "updated_at": _now_iso()}
    tracker["updated_at"] = tracker["learning_state"]["updated_at"]
    save_state()
    return tracker["learning_state"]


def get_learning_state_report(
    learning_store: dict[str, dict],
    confusion_store: dict[str, dict],
    user_id: str,
    goal_resolver: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    state = refresh_learning_state(
        learning_store=learning_store,
        confusion_store=confusion_store,
        user_id=user_id,
        goal_resolver=goal_resolver,
    )
    topics = list(state.get("topics", {}).values()) if isinstance(state, dict) else []
    topics.sort(
        key=lambda item: (
            str(item.get("priority", "medium")) != "high",
            float(item.get("retention_score", 0.0)),
            float(item.get("mastery_level", 0.0)),
            -float(item.get("confusion_level", 0.0)),
        )
    )
    return {"user_id": user_id, "goal": state.get("goal", "general"), "topics": topics, "updated_at": state.get("updated_at", _now_iso())}
