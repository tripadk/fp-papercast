from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas import LearningInsightsApiResponse, LearningInsightsResponse, LearningStateResponse
from app.services.llm_service import analyze_learning_progress
from app.store import LEARNING_STORE

router = APIRouter(prefix="/learning-state", tags=["learning-state"])
v1_router = APIRouter(prefix="/api/v1/learning-state", tags=["learning-state"])
insights_router = APIRouter(prefix="/api/v1/learning-insights", tags=["learning-insights"])
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


def _build_learning_insights_payload(user_email: str) -> LearningInsightsApiResponse:
    progress_payload = _mock_progress(user_email)
    progress = progress_payload["progress"]
    analysis = analyze_learning_progress(progress_payload)
    completed_topics = int(progress.get("completed_topics", 0) or 0)
    average_score = int(progress.get("average_score", 0) or 0)
    weak_topics = progress_payload["weak_topics"]

    strengths = [
        "Learning activity is being tracked consistently.",
        f"Average score is currently {average_score}%.",
    ]
    if completed_topics > 0:
        strengths.append(f"{completed_topics} topics have been completed so far.")

    weaknesses = weak_topics[:3] or ["Foundational understanding still needs reinforcement."]
    recommendations = [
        f"Review {topic} with short notes and one follow-up question."
        for topic in weaknesses[:3]
    ]
    if analysis:
        recommendations.append(analysis[:240])

    progress_summary = (
        f"Completed topics: {completed_topics}. "
        f"Average score: {average_score}%. "
        f"Current weak areas: {', '.join(weaknesses)}."
    )
    return LearningInsightsApiResponse(
        user_email=user_email,
        progress_summary=progress_summary,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations[:4],
    )


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


@insights_router.get("", response_model=LearningInsightsApiResponse)
async def get_learning_insights_api(user_email: str = Query(...)) -> LearningInsightsApiResponse:
    logger.info("Learning insights API request received user_email=%s", user_email)
    try:
        return _build_learning_insights_payload(user_email)
    except Exception as exc:
        logger.exception("Learning insights API route failed")
        return JSONResponse(
            status_code=200,
            content={
                "user_email": user_email,
                "progress_summary": "Could not compute live learning insights.",
                "strengths": ["The learner profile is available."],
                "weaknesses": ["Live analysis is temporarily unavailable."],
                "recommendations": [f"Fallback used due to {type(exc).__name__}."],
            },
        )
