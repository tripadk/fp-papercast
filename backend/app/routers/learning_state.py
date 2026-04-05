from __future__ import annotations

from fastapi import APIRouter

from app.schemas import LearningStateResponse
from app.services.learning_state_service import get_learning_state_report
from app.services.profile_service import get_user_goal
from app.store import CONFUSION_STORE, LEARNING_STORE

router = APIRouter(prefix="/learning-state", tags=["learning-state"])


@router.get("/{user_id}", response_model=LearningStateResponse)
async def get_learning_state(user_id: str) -> LearningStateResponse:
    payload = get_learning_state_report(
        learning_store=LEARNING_STORE,
        confusion_store=CONFUSION_STORE,
        user_id=user_id,
        goal_resolver=get_user_goal,
    )
    return LearningStateResponse(**payload)
