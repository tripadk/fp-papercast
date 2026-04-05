from __future__ import annotations

from typing import Any

from app.services.concept_service import get_concept_label
from app.services.policy_engine import select_difficulty, select_mode_for_concept
from app.services.profile_service import get_user_goal
from app.services.learning_state_service import get_learning_state_report
from app.store import CONFUSION_STORE, KNOWLEDGE_GRAPH_STORE, LEARNING_STORE


def _mastered(topic_state: dict[str, Any]) -> bool:
    return (
        float(topic_state.get("mastery_level", 0.0)) >= 70.0
        and float(topic_state.get("retention_score", 0.0)) >= 60.0
        and float(topic_state.get("confusion_level", 0.0)) < 40.0
    )


def _concept_candidates(
    user_id: str,
    content_id: str,
    requested_concept_id: str = "",
) -> list[dict[str, Any]]:
    state = get_learning_state_report(
        learning_store=LEARNING_STORE,
        confusion_store=CONFUSION_STORE,
        user_id=user_id,
        goal_resolver=get_user_goal,
    )
    state_map = {
        str(item.get("concept_id", "")).strip(): item
        for item in state.get("topics", [])
        if isinstance(item, dict) and str(item.get("concept_id", "")).strip()
    }

    graph_payload = KNOWLEDGE_GRAPH_STORE.get(content_id, {})
    topics = graph_payload.get("graph", {}).get("topics", []) if isinstance(graph_payload, dict) else []
    candidates: list[dict[str, Any]] = []
    for topic in topics:
        if not isinstance(topic, dict):
            continue
        for concept_item in topic.get("concept_items", []):
            if not isinstance(concept_item, dict):
                continue
            concept_id = str(concept_item.get("concept_id", "")).strip()
            if not concept_id:
                continue
            topic_state = state_map.get(
                concept_id,
                {
                    "concept_id": concept_id,
                    "topic": str(concept_item.get("label", concept_id)),
                    "mastery_level": 0.0,
                    "confusion_level": 0.0,
                    "retention_score": 0.0,
                    "priority": "high",
                    "next_mode_hint": "notes",
                },
            )
            prereqs = [str(item).strip() for item in concept_item.get("prerequisites", []) if str(item).strip()]
            prereq_ready = all(_mastered(state_map.get(prereq, {})) for prereq in prereqs)
            candidates.append(
                {
                    "concept_id": concept_id,
                    "label": str(concept_item.get("label", concept_id)),
                    "difficulty_level": str(concept_item.get("difficulty_level", "medium")),
                    "prerequisites": prereqs,
                    "prereq_ready": prereq_ready,
                    "state": topic_state,
                }
            )

    if requested_concept_id:
        direct = [item for item in candidates if item["concept_id"] == requested_concept_id]
        if direct:
            return direct

    if candidates:
        return candidates

    fallback_state = list(state_map.values())
    if fallback_state:
        return [
            {
                "concept_id": str(item.get("concept_id", "")),
                "label": str(item.get("topic", "General Revision")),
                "difficulty_level": "medium",
                "prerequisites": [],
                "prereq_ready": True,
                "state": item,
            }
            for item in fallback_state
        ]

    concept_id = requested_concept_id.strip() or f"{content_id}:general"
    return [
        {
            "concept_id": concept_id,
            "label": get_concept_label(concept_id, "General Revision"),
            "difficulty_level": "medium",
            "prerequisites": [],
            "prereq_ready": True,
            "state": {
                "concept_id": concept_id,
                "topic": "General Revision",
                "mastery_level": 0.0,
                "confusion_level": 0.0,
                "retention_score": 0.0,
                "priority": "high",
                "next_mode_hint": "notes",
            },
        }
    ]


def select_next_action(user_id: str, content_id: str, concept_id: str = "") -> dict[str, Any]:
    candidates = _concept_candidates(user_id=user_id, content_id=content_id, requested_concept_id=concept_id)
    candidates.sort(
        key=lambda item: (
            not bool(item.get("prereq_ready", False)),
            str(item["state"].get("priority", "medium")) != "high",
            float(item["state"].get("retention_score", 0.0)),
            float(item["state"].get("mastery_level", 0.0)),
            -float(item["state"].get("confusion_level", 0.0)),
        )
    )
    selected = candidates[0]
    selected_state = selected["state"]

    fallback_mode = str(selected_state.get("next_mode_hint", "notes")).strip().lower() or "notes"
    if fallback_mode == "podcast":
        fallback_mode = "audio"
    mode, policy_reason = select_mode_for_concept(user_id=user_id, concept_id=selected["concept_id"], fallback_mode=fallback_mode)
    difficulty = select_difficulty(selected_state)

    reason_parts = [policy_reason]
    if not selected.get("prereq_ready", True):
        reason_parts.append("requested concept blocked by unmet prerequisites")
    elif selected.get("prerequisites"):
        reason_parts.append("prerequisites satisfied")
    if float(selected_state.get("confusion_level", 0.0)) >= 55:
        reason_parts.append("high confusion detected")
    if float(selected_state.get("retention_score", 0.0)) <= 45:
        reason_parts.append("low retention detected")

    return {
        "concept_id": selected["concept_id"],
        "concept": selected["label"],
        "mode": mode,
        "difficulty": difficulty,
        "reason": "; ".join(reason_parts),
        "topic_state": selected_state,
    }
