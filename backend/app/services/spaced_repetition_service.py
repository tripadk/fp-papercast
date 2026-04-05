from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.concept_service import get_concept_label, normalize_concept
from app.store import save_state

SRS_INTERVALS_DAYS = [1, 3, 7, 14]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_iso(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(UTC)


def ensure_user_tracker(store: dict[str, dict], user_email: str) -> dict[str, Any]:
    if user_email not in store:
        store[user_email] = {
            "viewed_topics": [],
            "topics_studied": {},
            "quiz_performance": {},
            "weak_topics": {},
            "strong_topics": {},
            "recall_performance": {},
            "learning_efficiency": {},
            "revision_schedule": {},
            "reassessment_queue": {},
            "updated_at": _now_iso(),
        }
    tracker = store[user_email]
    for key, default in {
        "viewed_topics": [],
        "topics_studied": {},
        "quiz_performance": {},
        "weak_topics": {},
        "strong_topics": {},
        "recall_performance": {},
        "learning_efficiency": {},
        "revision_schedule": {},
        "reassessment_queue": {},
    }.items():
        tracker.setdefault(key, default.copy() if isinstance(default, dict) else list(default))
    tracker.setdefault("updated_at", _now_iso())
    return tracker


def _schedule_key(concept_id: str, paper_id: str = "") -> str:
    return f"{(paper_id or '').strip().lower()}::{concept_id.strip().lower()}" if paper_id else concept_id.strip().lower()


def _next_interval_index(current_index: int, is_correct: bool, accuracy: float) -> int:
    idx = max(0, min(current_index, len(SRS_INTERVALS_DAYS) - 1))
    acc = max(0.0, min(1.0, float(accuracy)))
    if is_correct:
        idx += 2 if acc >= 0.85 else 1 if acc >= 0.65 else 0
    else:
        idx = 0 if acc < 0.4 else idx - 1
    return max(0, min(idx, len(SRS_INTERVALS_DAYS) - 1))


def update_revision_schedule(
    store: dict[str, dict],
    user_email: str,
    topic: str,
    is_correct: bool,
    paper_id: str = "",
    accuracy: float | None = None,
    concept_id: str = "",
) -> dict[str, Any]:
    tracker = ensure_user_tracker(store, user_email)
    concept = normalize_concept(user_id=user_email, content_id=paper_id or "global", raw_text=topic, aliases=[topic]) if not concept_id else {"concept_id": concept_id, "label": get_concept_label(concept_id, topic)}
    if accuracy is None:
        accuracy = float(tracker.get("quiz_performance", {}).get(concept["concept_id"], {}).get("accuracy", 0.0))
    accuracy = max(0.0, min(1.0, float(accuracy)))

    schedule = tracker.setdefault("revision_schedule", {})
    key = _schedule_key(concept["concept_id"], paper_id)
    now = datetime.now(UTC)
    entry = schedule.setdefault(
        key,
        {
            "concept_id": concept["concept_id"],
            "topic": concept["label"],
            "paper_id": (paper_id or "").strip(),
            "interval_index": 0,
            "interval_days": SRS_INTERVALS_DAYS[0],
            "next_review_date": (now + timedelta(days=SRS_INTERVALS_DAYS[0])).isoformat(),
            "last_reviewed_at": "",
            "total_reviews": 0,
            "correct_reviews": 0,
            "accuracy_snapshot": 0.0,
        },
    )

    next_index = _next_interval_index(int(entry.get("interval_index", 0)), is_correct=is_correct, accuracy=accuracy)
    interval_days = SRS_INTERVALS_DAYS[next_index]
    next_review = now + timedelta(days=interval_days)

    entry["interval_index"] = next_index
    entry["interval_days"] = interval_days
    entry["next_review_date"] = next_review.isoformat()
    entry["last_reviewed_at"] = now.isoformat()
    entry["total_reviews"] = int(entry.get("total_reviews", 0)) + 1
    entry["correct_reviews"] = int(entry.get("correct_reviews", 0)) + (1 if is_correct else 0)
    entry["accuracy_snapshot"] = round(accuracy, 3)

    tracker.setdefault("reassessment_queue", {})[concept["concept_id"]] = {
        "concept_id": concept["concept_id"],
        "topic": concept["label"],
        "paper_id": paper_id.strip(),
        "due_at": next_review.isoformat(),
        "reason": "post-intervention reassessment",
    }
    tracker["updated_at"] = _now_iso()
    save_state()
    return entry


def get_revision_schedule(store: dict[str, dict], user_email: str, include_all: bool = False, limit: int = 50) -> list[dict[str, Any]]:
    tracker = ensure_user_tracker(store, user_email)
    schedule = tracker.get("revision_schedule", {})
    now = datetime.now(UTC)
    items: list[dict[str, Any]] = []
    for entry in schedule.values():
        if not isinstance(entry, dict):
            continue
        next_review_dt = _parse_iso(str(entry.get("next_review_date", "")))
        if not include_all and next_review_dt > now:
            continue
        items.append(
            {
                "concept_id": str(entry.get("concept_id", "")),
                "topic": str(entry.get("topic", "")),
                "paper_id": str(entry.get("paper_id", "")),
                "interval_days": int(entry.get("interval_days", 1)),
                "next_review_date": str(entry.get("next_review_date", "")),
                "last_reviewed_at": str(entry.get("last_reviewed_at", "")),
                "accuracy_snapshot": float(entry.get("accuracy_snapshot", 0.0)),
                "total_reviews": int(entry.get("total_reviews", 0)),
                "correct_reviews": int(entry.get("correct_reviews", 0)),
                "is_due": next_review_dt <= now,
            }
        )
    items.sort(key=lambda item: _parse_iso(str(item.get("next_review_date", ""))))
    return items[: max(1, limit)]


def _touch_topic_studied(tracker: dict[str, Any], concept_id: str, topic: str, paper_id: str = "", source: str = "manual") -> None:
    if not concept_id.strip():
        return
    timestamp = _now_iso()
    topics = tracker.setdefault("topics_studied", {})
    entry = topics.setdefault(
        concept_id,
        {"concept_id": concept_id, "topic": topic.strip(), "paper_id": (paper_id or "").strip(), "count": 0, "sources": [], "last_seen": timestamp},
    )
    entry["count"] = int(entry.get("count", 0)) + 1
    if source and source not in entry.get("sources", []):
        entry.setdefault("sources", []).append(source)
    if paper_id:
        entry["paper_id"] = paper_id.strip()
    if topic:
        entry["topic"] = topic.strip()
    entry["last_seen"] = timestamp


def record_strong_topic(store: dict[str, dict], user_email: str, concept: str, paper_id: str = "", reason: str = "", confidence: float = 1.0, concept_id: str = "") -> dict[str, Any]:
    tracker = ensure_user_tracker(store, user_email)
    normalized = normalize_concept(user_id=user_email, content_id=paper_id or "global", raw_text=concept) if not concept_id else {"concept_id": concept_id, "label": get_concept_label(concept_id, concept)}
    timestamp = _now_iso()
    entry = tracker.setdefault("strong_topics", {}).setdefault(
        normalized["concept_id"],
        {"concept_id": normalized["concept_id"], "concept": normalized["label"], "paper_id": paper_id.strip(), "confidence": 0.0, "reason": reason or "strong understanding signals", "last_seen": timestamp},
    )
    entry["confidence"] = float(entry.get("confidence", 0.0)) + max(0.3, float(confidence))
    if reason:
        entry["reason"] = reason
    entry["last_seen"] = timestamp
    _touch_topic_studied(tracker, normalized["concept_id"], normalized["label"], paper_id=paper_id, source="strength-update")
    tracker["updated_at"] = timestamp
    save_state()
    return tracker


def record_topic_view(store: dict[str, dict], user_email: str, topic: str, paper_id: str = "", confidence: int = 3, source: str = "manual") -> dict[str, Any]:
    tracker = ensure_user_tracker(store, user_email)
    normalized = normalize_concept(user_id=user_email, content_id=paper_id or "global", raw_text=topic)
    timestamp = _now_iso()
    tracker["viewed_topics"].append(
        {
            "concept_id": normalized["concept_id"],
            "topic": normalized["label"],
            "paper_id": paper_id.strip(),
            "confidence": max(1, min(confidence, 5)),
            "source": source or "manual",
            "viewed_at": timestamp,
        }
    )
    _touch_topic_studied(tracker, normalized["concept_id"], normalized["label"], paper_id=paper_id, source=source or "manual")
    if confidence >= 4:
        record_strong_topic(store=store, user_email=user_email, concept=normalized["label"], paper_id=paper_id, reason=f"high confidence topic view ({source or 'manual'})", confidence=0.8, concept_id=normalized["concept_id"])
    elif confidence <= 2:
        record_weak_area(store=store, user_email=user_email, concept=normalized["label"], severity=max(1, 4 - confidence), paper_id=paper_id, reason="low confidence", concept_id=normalized["concept_id"])
    tracker["updated_at"] = timestamp
    save_state()
    return tracker


def record_weak_area(store: dict[str, dict], user_email: str, concept: str, severity: int = 3, paper_id: str = "", reason: str = "", concept_id: str = "") -> dict[str, Any]:
    tracker = ensure_user_tracker(store, user_email)
    normalized = normalize_concept(user_id=user_email, content_id=paper_id or "global", raw_text=concept) if not concept_id else {"concept_id": concept_id, "label": get_concept_label(concept_id, concept)}
    timestamp = _now_iso()
    entry = tracker.setdefault("weak_topics", {}).setdefault(
        normalized["concept_id"],
        {"concept_id": normalized["concept_id"], "concept": normalized["label"], "paper_id": paper_id.strip(), "severity": 0.0, "reason": reason or "manually marked weak", "last_seen": timestamp},
    )
    entry["severity"] = float(entry.get("severity", 0.0)) + max(1, min(severity, 5)) * 0.7
    if reason:
        entry["reason"] = reason
    entry["last_seen"] = timestamp
    _touch_topic_studied(tracker, normalized["concept_id"], normalized["label"], paper_id=paper_id, source="weak-area")
    tracker["updated_at"] = timestamp
    save_state()
    return tracker


def build_daily_revision_list(store: dict[str, dict], user_email: str, limit: int = 10) -> list[dict[str, Any]]:
    tracker = ensure_user_tracker(store, user_email)
    weak_areas = tracker.get("weak_topics", {})
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    now = datetime.now(UTC)
    for concept_id, entry in weak_areas.items():
        if not isinstance(entry, dict):
            continue
        last_seen = _parse_iso(str(entry.get("last_seen", now.isoformat())))
        days_since = max(0.0, (now - last_seen).total_seconds() / 86400.0)
        score = float(entry.get("severity", 0.0)) + (0.6 * days_since)
        items.append({"concept_id": concept_id, "concept": str(entry.get("concept", get_concept_label(concept_id, concept_id))), "score": round(score, 2), "reason": str(entry.get("reason", "weak area")), "paper_id": str(entry.get("paper_id", ""))})
        seen.add(concept_id)

    learning_state = tracker.get("learning_state", {})
    for concept_id, topic_state in (learning_state.get("topics", {}) or {}).items():
        if concept_id in seen or not isinstance(topic_state, dict):
            continue
        priority = str(topic_state.get("priority", "medium")).lower()
        confusion = float(topic_state.get("confusion_level", 0.0))
        retention = float(topic_state.get("retention_score", 0.0))
        priority_boost = 4.0 if priority == "high" else 2.0 if priority == "medium" else 0.5
        score = priority_boost + (confusion * 0.08) + max(0.0, (100.0 - retention) * 0.05)
        items.append({"concept_id": concept_id, "concept": str(topic_state.get("topic", get_concept_label(concept_id, concept_id))), "score": round(score, 2), "reason": "central learning state priority", "paper_id": str(topic_state.get("content_id", ""))})

    items.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    return items[: max(1, limit)]


def build_flashcards_for_weak_concepts(store: dict[str, dict], user_email: str, paper_store: dict[str, dict], limit: int = 12) -> list[dict[str, str]]:
    revision_items = build_daily_revision_list(store, user_email, limit=limit)
    cards: list[dict[str, str]] = []
    for item in revision_items:
        concept = str(item.get("concept", "")).strip()
        paper_id = str(item.get("paper_id", "")).strip()
        paper = paper_store.get(paper_id, {}) if paper_id else {}
        summary_line = str(paper.get("summary", "")).splitlines()[0].strip() if str(paper.get("summary", "")).strip() else ""
        cards.append(
            {
                "concept_id": str(item.get("concept_id", "")),
                "concept": concept,
                "question": f"What is {concept} and why does it matter?",
                "answer": (summary_line or f"{concept} is a core concept that needs revision.")[:260],
                "hint": f"Focus on the definition, intuition, and one practical use of {concept}.",
                "paper_id": paper_id,
            }
        )
    return cards


def generate_active_recall_items(study_notes: dict[str, str], paper_id: str = "", user_email: str = "") -> list[dict[str, str]]:
    if not study_notes:
        return []
    cards: list[dict[str, str]] = []
    for topic, answer in study_notes.items():
        clean_answer = (answer or "").strip()
        if not clean_answer:
            continue
        normalized = normalize_concept(user_id=user_email or "anonymous@local", content_id=paper_id or "global", raw_text=topic)
        cards.append(
            {
                "id": normalized["concept_id"],
                "concept_id": normalized["concept_id"],
                "topic": normalized["label"],
                "prompt": _mask_important_phrase(clean_answer),
                "answer": clean_answer,
                "paper_id": paper_id,
            }
        )
    return cards


def _mask_important_phrase(text: str) -> str:
    words = text.split()
    if len(words) < 4:
        return "Try to recall this concept: " + text
    candidates = [word for word in words if len(word.strip(".,;:!?")) >= 6] or [words[min(2, len(words) - 1)]]
    return f"Try to recall this concept: {text.replace(candidates[0], '_____', 1)}"


def record_recall_attempt(store: dict[str, dict], user_email: str, topic: str, is_correct: bool, paper_id: str = "", concept_id: str = "") -> dict[str, Any]:
    tracker = ensure_user_tracker(store, user_email)
    normalized = normalize_concept(user_id=user_email, content_id=paper_id or "global", raw_text=topic) if not concept_id else {"concept_id": concept_id, "label": get_concept_label(concept_id, topic)}
    perf = tracker.setdefault("recall_performance", {}).setdefault(
        normalized["concept_id"],
        {"concept_id": normalized["concept_id"], "topic": normalized["label"], "paper_id": paper_id.strip(), "correct": 0, "incorrect": 0, "last_attempt": _now_iso()},
    )
    if is_correct:
        perf["correct"] = int(perf.get("correct", 0)) + 1
    else:
        perf["incorrect"] = int(perf.get("incorrect", 0)) + 1
        record_weak_area(store=store, user_email=user_email, concept=normalized["label"], severity=2, paper_id=paper_id, reason="active recall incorrect attempt", concept_id=normalized["concept_id"])
    perf["last_attempt"] = _now_iso()
    attempts = int(perf.get("correct", 0)) + int(perf.get("incorrect", 0))
    accuracy = int(perf.get("correct", 0)) / attempts if attempts else 0.0
    tracker.setdefault("quiz_performance", {})[normalized["concept_id"]] = {
        "concept_id": normalized["concept_id"],
        "topic": normalized["label"],
        "paper_id": paper_id.strip(),
        "attempts": attempts,
        "correct": int(perf.get("correct", 0)),
        "incorrect": int(perf.get("incorrect", 0)),
        "accuracy": round(accuracy, 3),
        "last_attempt": perf["last_attempt"],
    }
    tracker["updated_at"] = perf["last_attempt"]
    save_state()
    return perf


def get_user_learning_memory(store: dict[str, dict], user_email: str) -> dict[str, Any]:
    tracker = ensure_user_tracker(store, user_email)
    return {
        "topics_studied": tracker.get("topics_studied", {}),
        "quiz_performance": tracker.get("quiz_performance", {}),
        "weak_topics": tracker.get("weak_topics", {}),
        "strong_topics": tracker.get("strong_topics", {}),
        "updated_at": tracker.get("updated_at", _now_iso()),
    }
