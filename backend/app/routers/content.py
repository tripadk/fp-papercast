from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ConfusionInteractionRequest, ConfusionStatusResponse, LearningInteractionRequest, NextModeResponse
from app.services.adaptive_learning_engine import select_next_action
from app.services.concept_service import normalize_concept
from app.services.event_ledger_service import record_learning_event
from app.services.confusion_detection_service import get_confusion_status, update_confusion_status
from app.services.learning_efficiency_service import update_learning_efficiency
from app.services.learning_state_service import get_learning_state_report
from app.services.profile_service import get_user_goal
from app.services.spaced_repetition_service import update_revision_schedule
from app.store import CONFUSION_STORE, LEARNING_STORE, PAPER_STORE

router = APIRouter(prefix="/content", tags=["content"])


def _ensure_content(content_id: str) -> dict:
    paper = PAPER_STORE.get(content_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Content not found.")
    return paper


@router.post("/{content_id}/next-action", response_model=NextModeResponse)
async def next_action(content_id: str, payload: LearningInteractionRequest) -> NextModeResponse:
    _ensure_content(content_id)
    baseline = get_learning_state_report(
        learning_store=LEARNING_STORE,
        confusion_store=CONFUSION_STORE,
        user_id=payload.user_email,
        goal_resolver=get_user_goal,
    )
    candidate_concept_id = ""
    if baseline.get("topics"):
        candidate_concept_id = str((baseline["topics"][0] or {}).get("concept_id", ""))
    result = select_next_action(user_id=payload.user_email, content_id=content_id, concept_id=candidate_concept_id)
    concept_id = str(result.get("concept_id", "")).strip()
    concept = str(result.get("concept", "General Revision"))
    inferred_correct = float(payload.accuracy) >= 0.6

    record_learning_event(
        user_id=payload.user_email,
        content_id=content_id,
        concept_id=concept_id,
        topic=concept,
        event_type="intervention",
        correctness=inferred_correct,
        response_time=float(payload.time_spent),
        mode_used=str(result.get("mode", "notes")),
        metadata={"difficulty": str(result.get("difficulty", "medium")), "reason": str(result.get("reason", ""))},
    )
    update_revision_schedule(
        store=LEARNING_STORE,
        user_email=payload.user_email,
        topic=concept,
        is_correct=inferred_correct,
        paper_id=content_id,
        accuracy=float(payload.accuracy),
        concept_id=concept_id,
    )
    update_learning_efficiency(
        store=LEARNING_STORE,
        user_id=payload.user_email,
        topic=concept,
        accuracy=float(payload.accuracy),
        time_spent=max(1, int(payload.time_spent)),
        attempts=1,
        content_id=content_id,
        concept_id=concept_id,
    )
    update_confusion_status(
        store=CONFUSION_STORE,
        paper_store=PAPER_STORE,
        user_email=payload.user_email,
        content_id=content_id,
        topic=concept,
        question=f"adaptive:{concept}",
        is_correct=inferred_correct,
        response_time_seconds=float(payload.time_spent),
        concept_id=concept_id,
    )
    get_learning_state_report(
        learning_store=LEARNING_STORE,
        confusion_store=CONFUSION_STORE,
        user_id=payload.user_email,
        goal_resolver=get_user_goal,
    )
    return NextModeResponse(
        content_id=content_id,
        user_email=payload.user_email,
        previous_mode=str((baseline.get("topics", [{}])[0] or {}).get("next_mode_hint", "notes")) if baseline.get("topics") else "notes",
        current_mode=str(result.get("mode", "notes")),
        reason=str(result.get("reason", "")),
        concept_id=concept_id,
        concept=concept,
        difficulty=str(result.get("difficulty", "medium")),
        repeated_mistakes=float((result.get("topic_state", {}) or {}).get("confusion_level", 0.0)) >= 60.0,
        recommendations=[f"Focus on {concept}", f"Use {str(result.get('mode', 'notes'))} mode next"],
    )


@router.post("/{content_id}/next-mode", response_model=NextModeResponse)
async def next_mode(content_id: str, payload: LearningInteractionRequest) -> NextModeResponse:
    return await next_action(content_id, payload)


@router.post("/{content_id}/confusion-status", response_model=ConfusionStatusResponse)
async def post_confusion_status(content_id: str, payload: ConfusionInteractionRequest) -> ConfusionStatusResponse:
    _ensure_content(content_id)
    concept = normalize_concept(user_id=payload.user_email, content_id=content_id, raw_text=payload.topic, aliases=[payload.question])
    update_confusion_status(
        store=CONFUSION_STORE,
        paper_store=PAPER_STORE,
        user_email=payload.user_email,
        content_id=content_id,
        topic=payload.topic,
        question=payload.question,
        is_correct=payload.is_correct,
        response_time_seconds=payload.response_time_seconds,
        concept_id=concept["concept_id"],
    )
    inferred_accuracy = 1.0 if payload.is_correct else 0.0
    record_learning_event(
        user_id=payload.user_email,
        content_id=content_id,
        concept_id=concept["concept_id"],
        topic=concept["label"],
        event_type="quiz",
        correctness=payload.is_correct,
        response_time=payload.response_time_seconds,
        mode_used="quiz",
    )
    update_revision_schedule(store=LEARNING_STORE, user_email=payload.user_email, topic=concept["label"], is_correct=payload.is_correct, paper_id=content_id, accuracy=inferred_accuracy, concept_id=concept["concept_id"])
    update_learning_efficiency(store=LEARNING_STORE, user_id=payload.user_email, topic=concept["label"], accuracy=inferred_accuracy, time_spent=max(1, int(payload.response_time_seconds)), attempts=1, content_id=content_id, concept_id=concept["concept_id"])
    get_learning_state_report(learning_store=LEARNING_STORE, confusion_store=CONFUSION_STORE, user_id=payload.user_email, goal_resolver=get_user_goal)
    topics = get_confusion_status(store=CONFUSION_STORE, user_email=payload.user_email, content_id=content_id)
    return ConfusionStatusResponse(content_id=content_id, user_email=payload.user_email, topics=topics)


@router.get("/{content_id}/confusion-status", response_model=ConfusionStatusResponse)
async def get_content_confusion_status(content_id: str, user_email: str = Query(...)) -> ConfusionStatusResponse:
    _ensure_content(content_id)
    topics = get_confusion_status(store=CONFUSION_STORE, user_email=user_email, content_id=content_id)
    return ConfusionStatusResponse(content_id=content_id, user_email=user_email, topics=topics)
