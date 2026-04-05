from __future__ import annotations

from fastapi import APIRouter

from app.schemas import LearningNextActionRequest, LearningNextActionResponse
from app.services.adaptive_learning_engine import select_next_action
from app.services.profile_service import get_user_goal
from app.store import LEARNING_STORE

router = APIRouter(prefix="/learning", tags=["learning"])


@router.post("/next-action", response_model=LearningNextActionResponse)
async def get_next_learning_action(payload: LearningNextActionRequest) -> LearningNextActionResponse:
    tracker = LEARNING_STORE.get(payload.user_id, {})
    learning_state = tracker.get("learning_state", {}) if isinstance(tracker, dict) else {}
    topics = learning_state.get("topics", {}) if isinstance(learning_state, dict) else {}
    concept_id = next(iter(topics.keys()), "")
    content_id = ""
    if concept_id:
        content_id = str((topics.get(concept_id, {}) or {}).get("content_id", ""))
    result = select_next_action(user_id=payload.user_id, content_id=content_id, concept_id=concept_id)
    return LearningNextActionResponse(
        user_id=payload.user_id,
        goal=get_user_goal(payload.user_id),
        concept_id=result.get("concept_id", ""),
        next_topic=result.get("concept", "General Revision"),
        next_mode=result.get("mode", "notes"),
        difficulty_level=result.get("difficulty", "medium"),
        quiz_difficulty=result.get("difficulty", "medium"),
        rationale=[result.get("reason", "adaptive policy selection")],
        topic_state=result.get("topic_state", {"mastery_level": 0.0, "confusion_level": 0.0, "retention_score": 0.0, "priority": "high"}),
        recent_activity=payload.recent_activity,
    )
