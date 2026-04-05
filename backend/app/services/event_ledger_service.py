from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings

EVENT_TYPES = {"quiz", "chat", "recall", "mode_switch", "intervention"}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _db_path() -> Path:
    return Path(settings.events_db_path)


def _normalize_key(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(str(_db_path()))


def init_event_ledger() -> None:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS learner_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                content_id TEXT NOT NULL DEFAULT '',
                concept_id TEXT NOT NULL DEFAULT '',
                topic TEXT NOT NULL DEFAULT '',
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                correctness INTEGER NULL,
                response_time REAL NULL,
                mode_used TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        columns = {row[1] for row in conn.execute("PRAGMA table_info(learner_events)").fetchall()}
        if "concept_id" not in columns:
            conn.execute("ALTER TABLE learner_events ADD COLUMN concept_id TEXT NOT NULL DEFAULT ''")
        if "metadata_json" not in columns:
            conn.execute("ALTER TABLE learner_events ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                content_id TEXT NOT NULL DEFAULT '',
                concept_id TEXT NOT NULL,
                mode_used TEXT NOT NULL,
                improvement_score REAL NOT NULL DEFAULT 0.0,
                time_taken REAL NOT NULL DEFAULT 0.0,
                before_mastery REAL NOT NULL DEFAULT 0.0,
                after_mastery REAL NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_learner_events_user_time ON learner_events(user_id, timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_learner_events_user_concept ON learner_events(user_id, concept_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_learning_outcomes_user_concept ON learning_outcomes(user_id, concept_id)"
        )
        conn.commit()


def record_learning_event(
    user_id: str,
    content_id: str,
    concept_id: str,
    topic: str,
    event_type: str,
    correctness: bool | None = None,
    response_time: float | None = None,
    mode_used: str = "",
    timestamp: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    clean_user = (user_id or "").strip()
    if not clean_user:
        raise ValueError("user_id is required")
    normalized_type = (event_type or "").strip().lower()
    if normalized_type not in EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {event_type}")

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO learner_events (
                user_id,
                content_id,
                concept_id,
                topic,
                event_type,
                timestamp,
                correctness,
                response_time,
                mode_used,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clean_user,
                (content_id or "").strip(),
                (concept_id or "").strip(),
                (topic or "").strip(),
                normalized_type,
                timestamp or _now_iso(),
                None if correctness is None else int(bool(correctness)),
                None if response_time is None else max(0.0, float(response_time)),
                (mode_used or "").strip(),
                json_dumps(metadata or {}),
            ),
        )
        conn.commit()


def record_learning_outcome(
    user_id: str,
    content_id: str,
    concept_id: str,
    mode_used: str,
    improvement_score: float,
    time_taken: float,
    before_mastery: float,
    after_mastery: float,
) -> None:
    if not concept_id.strip():
        return
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO learning_outcomes (
                user_id,
                content_id,
                concept_id,
                mode_used,
                improvement_score,
                time_taken,
                before_mastery,
                after_mastery,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id.strip(),
                (content_id or "").strip(),
                concept_id.strip(),
                (mode_used or "").strip(),
                float(improvement_score),
                max(0.0, float(time_taken)),
                float(before_mastery),
                float(after_mastery),
                _now_iso(),
            ),
        )
        conn.commit()


def get_user_events(user_id: str, limit: int = 200) -> list[dict[str, Any]]:
    clean_user = (user_id or "").strip()
    if not clean_user:
        return []
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT user_id, content_id, concept_id, topic, event_type, timestamp, correctness, response_time, mode_used, metadata_json
            FROM learner_events
            WHERE user_id = ?
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (clean_user, max(1, int(limit))),
        ).fetchall()

    events: list[dict[str, Any]] = []
    for row in rows:
        correctness_raw = row["correctness"]
        events.append(
            {
                "user_id": str(row["user_id"]),
                "content_id": str(row["content_id"]),
                "concept_id": str(row["concept_id"]),
                "topic": str(row["topic"]),
                "event_type": str(row["event_type"]),
                "timestamp": str(row["timestamp"]),
                "correctness": None if correctness_raw is None else bool(int(correctness_raw)),
                "response_time": None if row["response_time"] is None else float(row["response_time"]),
                "mode_used": str(row["mode_used"]),
                "metadata": json_loads(str(row["metadata_json"] or "{}")),
            }
        )
    return events


def _outcomes_by_concept(user_id: str) -> dict[str, list[dict[str, Any]]]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT concept_id, mode_used, improvement_score, time_taken, before_mastery, after_mastery, created_at
            FROM learning_outcomes
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
    result: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        concept_id = str(row["concept_id"])
        result.setdefault(concept_id, []).append(
            {
                "concept_id": concept_id,
                "mode_used": str(row["mode_used"]),
                "improvement_score": float(row["improvement_score"]),
                "time_taken": float(row["time_taken"]),
                "before_mastery": float(row["before_mastery"]),
                "after_mastery": float(row["after_mastery"]),
                "created_at": str(row["created_at"]),
            }
        )
    return result


def get_mode_performance(user_id: str, concept_id: str) -> dict[str, dict[str, float]]:
    outcomes = _outcomes_by_concept(user_id).get(concept_id, [])
    aggregated: dict[str, dict[str, float]] = {}
    for item in outcomes:
        mode = str(item.get("mode_used", "")).strip() or "notes"
        entry = aggregated.setdefault(mode, {"count": 0.0, "reward_sum": 0.0, "improvement_sum": 0.0, "time_sum": 0.0})
        time_taken = max(1.0, float(item.get("time_taken", 0.0)))
        improvement = float(item.get("improvement_score", 0.0))
        entry["count"] += 1.0
        entry["improvement_sum"] += improvement
        entry["time_sum"] += time_taken
        entry["reward_sum"] += improvement / time_taken
    return aggregated


def _concept_metrics_from_events(user_id: str, limit: int = 5000) -> dict[str, dict[str, Any]]:
    events = get_user_events(user_id=user_id, limit=limit)
    by_concept: dict[str, dict[str, Any]] = {}
    for event in reversed(events):
        concept_id = _normalize_key(str(event.get("concept_id", "")))
        if not concept_id:
            continue
        entry = by_concept.setdefault(
            concept_id,
            {
                "concept_id": concept_id,
                "topic": str(event.get("topic", concept_id)),
                "paper_id": "",
                "attempts": 0,
                "correct": 0,
                "incorrect": 0,
                "last_attempt": "",
                "total_response_time": 0.0,
                "response_samples": 0,
                "recall_correct": 0,
                "recall_incorrect": 0,
                "mode_counts": {},
            },
        )
        topic = str(event.get("topic", "")).strip()
        if topic:
            entry["topic"] = topic
        content_id = str(event.get("content_id", "")).strip()
        if content_id:
            entry["paper_id"] = content_id
        entry["last_attempt"] = str(event.get("timestamp", ""))
        correctness = event.get("correctness")
        if correctness is not None:
            entry["attempts"] += 1
            if bool(correctness):
                entry["correct"] += 1
            else:
                entry["incorrect"] += 1
        response_time = event.get("response_time")
        if response_time is not None:
            entry["total_response_time"] += max(0.0, float(response_time))
            entry["response_samples"] += 1
        event_type = str(event.get("event_type", "")).strip().lower()
        if event_type == "recall":
            if bool(correctness):
                entry["recall_correct"] += 1
            else:
                entry["recall_incorrect"] += 1
        mode_used = str(event.get("mode_used", "")).strip()
        if mode_used:
            entry["mode_counts"][mode_used] = int(entry["mode_counts"].get(mode_used, 0)) + 1
    return by_concept


def rebuild_user_tracker_from_events(tracker: dict[str, Any], user_id: str) -> None:
    concept_metrics = _concept_metrics_from_events(user_id=user_id, limit=5000)
    if not concept_metrics:
        return

    quiz_performance = tracker.setdefault("quiz_performance", {})
    recall_performance = tracker.setdefault("recall_performance", {})
    learning_efficiency = tracker.setdefault("learning_efficiency", {})
    intervention_history = tracker.setdefault("intervention_history", {})
    outcomes_map = _outcomes_by_concept(user_id)

    for concept_id, metric in concept_metrics.items():
        attempts = int(metric.get("attempts", 0))
        correct = int(metric.get("correct", 0))
        incorrect = int(metric.get("incorrect", 0))
        accuracy = (float(correct) / max(1, attempts)) if attempts else 0.0
        total_time = float(metric.get("total_response_time", 0.0))
        avg_response = total_time / max(1, int(metric.get("response_samples", 0)))
        topic_name = str(metric.get("topic", concept_id))
        paper_id = str(metric.get("paper_id", ""))
        last_attempt = str(metric.get("last_attempt", ""))

        quiz_performance[concept_id] = {
            "concept_id": concept_id,
            "topic": topic_name,
            "paper_id": paper_id,
            "attempts": attempts,
            "correct": correct,
            "incorrect": incorrect,
            "accuracy": round(accuracy, 3),
            "last_attempt": last_attempt,
        }

        recall_correct = int(metric.get("recall_correct", 0))
        recall_incorrect = int(metric.get("recall_incorrect", 0))
        if recall_correct + recall_incorrect > 0:
            recall_performance[concept_id] = {
                "concept_id": concept_id,
                "topic": topic_name,
                "paper_id": paper_id,
                "correct": recall_correct,
                "incorrect": recall_incorrect,
                "last_attempt": last_attempt,
            }

        completion_rate = min(1.0, attempts / 5.0) if attempts > 0 else 0.0
        effective_minutes = max(1.0, total_time / 60.0)
        efficiency_score = max(0.0, min(100.0, ((accuracy * completion_rate) / effective_minutes) * 100.0))
        learning_efficiency[concept_id] = {
            "concept_id": concept_id,
            "topic": topic_name,
            "total_time_spent": int(round(total_time)),
            "total_attempts": attempts,
            "weighted_accuracy_sum": round(accuracy * max(1, attempts), 3),
            "quiz_accuracy": round(accuracy, 3),
            "completion_rate": round(completion_rate, 3),
            "learning_efficiency_score": round(efficiency_score, 2),
            "difficulty_adjustment": "hard" if efficiency_score >= 75 else "medium" if efficiency_score >= 45 else "easy",
            "priority": "high" if efficiency_score < 30 else "medium" if efficiency_score < 60 else "low",
            "avg_response_time_seconds": round(avg_response, 2),
            "updated_at": _now_iso(),
        }
        intervention_history[concept_id] = outcomes_map.get(concept_id, [])

    tracker["updated_at"] = _now_iso()


def get_user_event_summary(user_id: str) -> dict[str, Any]:
    events = list(reversed(get_user_events(user_id=user_id, limit=5000)))
    total_events = len(events)
    by_type = {event_type: 0 for event_type in sorted(EVENT_TYPES)}
    scored: list[int] = []
    for event in events:
        event_type = str(event.get("event_type", "")).strip().lower()
        if event_type in by_type:
            by_type[event_type] += 1
        correctness = event.get("correctness")
        if correctness is not None:
            scored.append(1 if bool(correctness) else 0)

    overall_accuracy = (sum(scored) / len(scored)) if scored else 0.0
    recent = scored[-20:]
    previous = scored[-40:-20]
    recent_accuracy = (sum(recent) / len(recent)) if recent else overall_accuracy
    previous_accuracy = (sum(previous) / len(previous)) if previous else overall_accuracy
    improvement_delta = recent_accuracy - previous_accuracy

    concept_metrics = _concept_metrics_from_events(user_id=user_id, limit=5000)
    topic_history = []
    for metric in concept_metrics.values():
        attempts = int(metric.get("attempts", 0))
        if attempts <= 0:
            continue
        correct = int(metric.get("correct", 0))
        topic_history.append(
            {
                "concept_id": str(metric.get("concept_id", "")),
                "topic": str(metric.get("topic", "")),
                "attempts": attempts,
                "accuracy": round(correct / max(1, attempts), 3),
                "last_interaction": str(metric.get("last_attempt", "")),
            }
        )
    topic_history.sort(key=lambda item: (item["attempts"], item["accuracy"]), reverse=True)

    return {
        "user_id": user_id,
        "total_events": total_events,
        "events_by_type": by_type,
        "overall_accuracy": round(overall_accuracy, 3),
        "recent_accuracy": round(recent_accuracy, 3),
        "previous_accuracy": round(previous_accuracy, 3),
        "improvement_delta": round(improvement_delta, 3),
        "topic_history": topic_history[:50],
        "updated_at": _now_iso(),
    }


def get_user_learning_history(user_id: str, limit: int = 2000) -> dict[str, Any]:
    return {
        "events": get_user_events(user_id=user_id, limit=limit),
        "outcomes": _outcomes_by_concept(user_id),
        "summary": get_user_event_summary(user_id=user_id),
    }


def json_dumps(payload: dict[str, Any]) -> str:
    try:
        import json

        return json.dumps(payload, ensure_ascii=False)
    except Exception:
        return "{}"


def json_loads(raw: str) -> dict[str, Any]:
    try:
        import json

        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}
