from __future__ import annotations

from typing import Any

from app.services.event_ledger_service import get_mode_performance

DEFAULT_MODE_ORDER = ["notes", "audio", "quiz", "flashcards"]


def select_mode_for_concept(user_id: str, concept_id: str, fallback_mode: str = "notes") -> tuple[str, str]:
    performance = get_mode_performance(user_id=user_id, concept_id=concept_id)
    if not performance:
        return fallback_mode, "no historical outcome data"

    best_mode = fallback_mode
    best_reward = float("-inf")
    for mode in DEFAULT_MODE_ORDER:
        stats = performance.get(mode)
        if not isinstance(stats, dict):
            continue
        reward = float(stats.get("reward_sum", 0.0)) / max(1.0, float(stats.get("count", 0.0)))
        if reward > best_reward:
            best_reward = reward
            best_mode = mode

    return best_mode, f"best historical learning gain per time for concept ({best_mode})"


def select_difficulty(topic_state: dict[str, Any]) -> str:
    mastery = float(topic_state.get("mastery_level", 0.0))
    retention = float(topic_state.get("retention_score", 0.0))
    confusion = float(topic_state.get("confusion_level", 0.0))
    if confusion >= 60 or retention <= 40:
        return "easy"
    if mastery >= 80 and retention >= 70 and confusion < 35:
        return "hard"
    return "medium"
