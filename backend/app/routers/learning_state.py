from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas import LearningInsightsResponse, LearningStateResponse
from app.services.llm_service import analyze_learning_progress
from app.store import LEARNING_STORE

router = APIRouter(prefix="/learning-state", tags=["learning-state"])
v1_router = APIRouter(prefix="/api/v1/learning-state", tags=["learning-state"])
logger = logging.getLogger(__name__)


def _mock_progress(user_email: str) -> dict:
    bucket = LEARNING_STORE.get(user_email, {}) if isinstance(LEARNING_STORE.get(user_email, {}), dict) else {}
    topics = bucket.get("topics_studied", {}) if isinstance(bucket, dict) else {}
    weak_topics = list((bucket.get("weak_topics", {}) or {}).keys())[:5] if isinstance(bucket, dict) else []
    completed_topics = len(topics) if isinstance(topics, dict) else 0
    average_score = 62 if completed_topics == 0 else min(95, 60 + completed_topics * 3)
    return {
        "progress": {"completed_topics": completed_topics, "average_score": average_score},
        "weak_topics": weak_topics or ["Research methods", "Result interpretation"],
    }


@router.get("/{user_id}", response_model=LearningStateResponse)
async def get_learning_state(user_id: str) -> LearningStateResponse:
    return LearningStateResponse(user_id=user_id, goal="general", topics=[], updated_at="")


@v1_router.get("", response_model=LearningInsightsResponse)
async def get_learning_insights(user_email: str = Query(...)) -> LearningInsightsResponse:
    logger.info("Learning insights request received user_email=%s", user_email)
    try:
        progress_payload = _mock_progress(user_email)
        analysis = analyze_learning_progress(progress_payload)
        recommendations = [
            {
                "concept_id": "",
                "topic": topic,
                "recommendation": f"Review {topic} with short notes and one practice question.",
                "priority": "high",
            }
            for topic in progress_payload["weak_topics"][:3]
        ]
        return LearningInsightsResponse(
            user_email=user_email,
            progress=progress_payload["progress"],
            weak_topics=progress_payload["weak_topics"],
            recommendations=recommendations or [
                {
                    "concept_id": "",
                    "topic": "General revision",
                    "recommendation": analysis[:300],
                    "priority": "medium",
                }
            ],
        )
    except Exception as exc:
        logger.exception("Learning insights route failed")
        return JSONResponse(
            status_code=200,
            content={
                "user_email": user_email,
                "progress": {"completed_topics": 0, "average_score": 0},
                "weak_topics": ["Basics"],
                "recommendations": [
                    {
                        "concept_id": "",
                        "topic": "Basics",
                        "recommendation": f"Could not compute live insights: {type(exc).__name__}",
                        "priority": "medium",
                    }
                ],
            },
        )
