from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas import LearnerEventItem, LearnerEventsResponse, LearnerEventSummary
from app.services.event_ledger_service import get_user_learning_history

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/{user_id}", response_model=LearnerEventsResponse)
async def get_events(user_id: str, limit: int = Query(200, ge=1, le=2000)) -> LearnerEventsResponse:
    payload = get_user_learning_history(user_id=user_id, limit=limit)
    events = [LearnerEventItem(**item) for item in payload.get("events", [])]
    summary = LearnerEventSummary(**payload.get("summary", {"user_id": user_id}))
    return LearnerEventsResponse(user_id=user_id, events=events, summary=summary, outcomes=payload.get("outcomes", {}))
