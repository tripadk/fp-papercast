from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas import LearningInsightsResponse, LearningStateResponse
from app.services.learning_state_service import get_learning_state_report
from app.services.profile_service import get_user_goal
from app.store import CONFUSION_STORE, LEARNING_STORE

router = APIRouter(prefix="/learning-state", tags=["learning-state"])
v1_router = APIRouter(prefix="/api/v1/learning-state", tags=["learning-state"])
logger = logging.getLogger(__name__)


@router.get("/{user_id}", response_model=LearningStateResponse)
async def get_learning_state(user_id: str) -> LearningStateResponse:
    logger.info("Learning state request received user_id=%s", user_id)
    try:
        payload = get_learning_state_report(
            learning_store=LEARNING_STORE,
            confusion_store=CONFUSION_STORE,
            user_id=user_id,
            goal_resolver=get_user_goal,
        )
        return LearningStateResponse(**payload)
    except Exception as exc:
        logger.exception("Unhandled error in /learning-state/%s", user_id)
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(
            status_code=status_code,
            content={"error": "learning_state_failed", "detail": detail, "route": f"/learning-state/{user_id}"},
        )


@v1_router.get("", response_model=LearningInsightsResponse)
async def get_learning_insights(user_email: str = Query(...)) -> LearningInsightsResponse:
    logger.info("Learning insights request received user_email=%s", user_email)
    print(f"[route:/api/v1/learning-state] request received user_email={user_email}")
    try:
        payload = get_learning_state_report(
            learning_store=LEARNING_STORE,
            confusion_store=CONFUSION_STORE,
            user_id=user_email,
            goal_resolver=get_user_goal,
        )
        topics = payload.get("topics", []) if isinstance(payload, dict) else []
        weak_topics = [str(item.get("topic", "")) for item in topics if str(item.get("priority", "")) == "high"][:5]
        recommendations = [
            {
                "concept_id": str(item.get("concept_id", "")),
                "topic": str(item.get("topic", "")),
                "recommendation": f"Use {str(item.get('next_mode_hint', 'notes')).replace('_', ' ')} for {str(item.get('topic', 'this concept'))}",
                "priority": str(item.get("priority", "medium")),
            }
            for item in topics[:5]
        ]
        topic_count = len(topics)
        avg_mastery = round(sum(float(item.get("mastery_level", 0.0)) for item in topics) / max(1, topic_count), 2)
        avg_retention = round(sum(float(item.get("retention_score", 0.0)) for item in topics) / max(1, topic_count), 2)
        return LearningInsightsResponse(
            user_email=user_email,
            progress={
                "topics_tracked": topic_count,
                "average_mastery": avg_mastery,
                "average_retention": avg_retention,
            },
            weak_topics=weak_topics,
            recommendations=recommendations,
        )
    except Exception as exc:
        logger.exception("Unhandled error in /api/v1/learning-state")
        print(f"[route:/api/v1/learning-state][error] {type(exc).__name__}: {exc}")
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(
            status_code=status_code,
            content={"error": "learning_insights_failed", "detail": detail, "route": "/api/v1/learning-state"},
        )
