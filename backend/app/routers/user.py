from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    LearningEfficiencyResponse,
    LearningEfficiencyUpdateRequest,
    UserGoalResponse,
    UserGoalUpdateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from app.services.learning_state_service import refresh_learning_state
from app.services.learning_efficiency_service import get_learning_efficiency_report, update_learning_efficiency
from app.services.profile_service import get_or_create_profile, get_user_goal, update_profile, update_user_goal
from app.store import CONFUSION_STORE, LEARNING_STORE

router = APIRouter(prefix="/api/v1/user", tags=["user"])


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    user_email: str = Query(...),
    name: str = Query(default=""),
    profile_image: str = Query(default=""),
) -> UserProfileResponse:
    try:
        profile = get_or_create_profile(user_email=user_email, name=name, profile_image=profile_image)
        return UserProfileResponse(**profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/profile/update", response_model=UserProfileResponse)
async def post_profile_update(payload: UserProfileUpdateRequest) -> UserProfileResponse:
    try:
        profile = update_profile(
            user_email=payload.user_email,
            name=payload.name,
            institution=payload.institution,
            bio=payload.bio,
            profile_image=payload.profile_image,
            goal=payload.goal,
        )
        return UserProfileResponse(**profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{user_id}/learning-efficiency", response_model=LearningEfficiencyResponse)
async def post_learning_efficiency(user_id: str, payload: LearningEfficiencyUpdateRequest) -> LearningEfficiencyResponse:
    try:
        update_learning_efficiency(
            store=LEARNING_STORE,
            user_id=user_id,
            topic=payload.topic,
            accuracy=payload.accuracy,
            time_spent=payload.time_spent,
            attempts=payload.attempts,
        )
        refresh_learning_state(
            learning_store=LEARNING_STORE,
            confusion_store=CONFUSION_STORE,
            user_id=user_id,
            goal_resolver=get_user_goal,
        )
        report = get_learning_efficiency_report(LEARNING_STORE, user_id=user_id)
        return LearningEfficiencyResponse(**report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{user_id}/learning-efficiency", response_model=LearningEfficiencyResponse)
async def get_learning_efficiency(user_id: str) -> LearningEfficiencyResponse:
    report = get_learning_efficiency_report(LEARNING_STORE, user_id=user_id)
    return LearningEfficiencyResponse(**report)


@router.get("/{user_id}/goal", response_model=UserGoalResponse)
async def get_user_goal_route(user_id: str) -> UserGoalResponse:
    goal = get_user_goal(user_id)
    return UserGoalResponse(user_id=user_id, goal=goal)


@router.post("/{user_id}/goal", response_model=UserGoalResponse)
async def post_user_goal_route(user_id: str, payload: UserGoalUpdateRequest) -> UserGoalResponse:
    profile = update_user_goal(user_email=user_id, goal=payload.goal)
    return UserGoalResponse(user_id=user_id, goal=str(profile.get("goal", "general")))
