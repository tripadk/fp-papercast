from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Query

from app.schemas import (
    ActiveRecallItem,
    ActiveRecallResponse,
    DailyRevisionResponse,
    FlashcardItem,
    FlashcardsResponse,
    QuizPerformanceSummaryItem,
    RecallAttemptRequest,
    RecallPerformanceItem,
    RecallPerformanceResponse,
    RevisionItem,
    RevisionScheduleItem,
    RevisionScheduleResponse,
    RevisionScheduleUpdateRequest,
    StrongTopicItem,
    TopicMemoryItem,
    TopicViewRequest,
    UserLearningMemoryResponse,
    WeakAreaRequest,
    WeakTopicItem,
)
from app.services.concept_service import normalize_concept
from app.services.event_ledger_service import record_learning_event
from app.services.learning_efficiency_service import update_learning_efficiency
from app.services.learning_state_service import refresh_learning_state
from app.services.confusion_detection_service import update_confusion_status
from app.services.profile_service import get_user_goal
from app.services.spaced_repetition_service import (
    build_daily_revision_list,
    build_flashcards_for_weak_concepts,
    generate_active_recall_items,
    get_revision_schedule,
    get_user_learning_memory,
    record_recall_attempt,
    record_strong_topic,
    record_topic_view,
    record_weak_area,
    update_revision_schedule,
)
from app.store import CONFUSION_STORE, LEARNING_STORE, PAPER_STORE

router = APIRouter(prefix="/api/v1/revision", tags=["revision"])


@router.post("/view-topic")
async def post_view_topic(payload: TopicViewRequest) -> dict[str, str]:
    record_topic_view(store=LEARNING_STORE, user_email=payload.user_email, topic=payload.topic, paper_id=payload.paper_id, confidence=payload.confidence, source=payload.source)
    return {"status": "ok"}


@router.post("/weak-area")
async def post_weak_area(payload: WeakAreaRequest) -> dict[str, str]:
    record_weak_area(store=LEARNING_STORE, user_email=payload.user_email, concept=payload.concept, severity=payload.severity, paper_id=payload.paper_id, reason=payload.reason)
    return {"status": "ok"}


@router.post("/strong-topic")
async def post_strong_topic(payload: WeakAreaRequest) -> dict[str, str]:
    record_strong_topic(store=LEARNING_STORE, user_email=payload.user_email, concept=payload.concept, paper_id=payload.paper_id, reason=payload.reason or "manual strong topic mark", confidence=max(1, min(payload.severity, 5)) * 0.25)
    return {"status": "ok"}


@router.get("/daily", response_model=DailyRevisionResponse)
async def get_daily_revision(user_email: str = Query(...), limit: int = Query(10, ge=1, le=50)) -> DailyRevisionResponse:
    items = [RevisionItem(**item) for item in build_daily_revision_list(LEARNING_STORE, user_email, limit=limit)]
    return DailyRevisionResponse(user_email=user_email, generated_at=datetime.now(UTC).isoformat(), items=items)


@router.get("/flashcards", response_model=FlashcardsResponse)
async def get_flashcards(user_email: str = Query(...), limit: int = Query(12, ge=1, le=100)) -> FlashcardsResponse:
    cards = [FlashcardItem(**item) for item in build_flashcards_for_weak_concepts(store=LEARNING_STORE, user_email=user_email, paper_store=PAPER_STORE, limit=limit)]
    return FlashcardsResponse(user_email=user_email, generated_at=datetime.now(UTC).isoformat(), cards=cards)


@router.get("/active-recall/paper/{paper_id}", response_model=ActiveRecallResponse)
async def get_active_recall(paper_id: str, user_email: str = Query(...)) -> ActiveRecallResponse:
    paper = PAPER_STORE.get(paper_id, {})
    study_notes = paper.get("study_notes", {}) if isinstance(paper, dict) else {}
    items = [ActiveRecallItem(**item) for item in generate_active_recall_items(study_notes=study_notes, paper_id=paper_id, user_email=user_email)]
    return ActiveRecallResponse(paper_id=paper_id, user_email=user_email, generated_at=datetime.now(UTC).isoformat(), items=items)


@router.post("/active-recall/attempt")
async def post_active_recall_attempt(payload: RecallAttemptRequest) -> dict[str, str]:
    concept = normalize_concept(user_id=payload.user_email, content_id=payload.paper_id or "global", raw_text=payload.topic)
    response_time_seconds = 30.0
    record_learning_event(user_id=payload.user_email, content_id=payload.paper_id, concept_id=concept["concept_id"], topic=concept["label"], event_type="recall", correctness=payload.is_correct, response_time=response_time_seconds, mode_used="flashcards")
    perf = record_recall_attempt(store=LEARNING_STORE, user_email=payload.user_email, topic=concept["label"], is_correct=payload.is_correct, paper_id=payload.paper_id, concept_id=concept["concept_id"])
    attempts = int(perf.get("correct", 0)) + int(perf.get("incorrect", 0))
    accuracy = int(perf.get("correct", 0)) / attempts if attempts else 0.0
    update_revision_schedule(store=LEARNING_STORE, user_email=payload.user_email, topic=concept["label"], is_correct=payload.is_correct, paper_id=payload.paper_id, accuracy=accuracy, concept_id=concept["concept_id"])
    update_learning_efficiency(store=LEARNING_STORE, user_id=payload.user_email, topic=concept["label"], accuracy=accuracy, time_spent=int(response_time_seconds), attempts=1, content_id=payload.paper_id, concept_id=concept["concept_id"])
    if payload.paper_id and payload.paper_id in PAPER_STORE:
        update_confusion_status(store=CONFUSION_STORE, paper_store=PAPER_STORE, user_email=payload.user_email, content_id=payload.paper_id, topic=concept["label"], question=payload.topic, is_correct=payload.is_correct, response_time_seconds=response_time_seconds, concept_id=concept["concept_id"])
    refresh_learning_state(learning_store=LEARNING_STORE, confusion_store=CONFUSION_STORE, user_id=payload.user_email, goal_resolver=get_user_goal)
    return {"status": "ok"}


@router.post("/schedule", response_model=RevisionScheduleResponse)
async def post_revision_schedule(payload: RevisionScheduleUpdateRequest) -> RevisionScheduleResponse:
    concept = normalize_concept(user_id=payload.user_email, content_id=payload.paper_id or "global", raw_text=payload.topic)
    update_revision_schedule(store=LEARNING_STORE, user_email=payload.user_email, topic=concept["label"], is_correct=payload.is_correct, paper_id=payload.paper_id, accuracy=payload.accuracy, concept_id=concept["concept_id"])
    items = [RevisionScheduleItem(**item) for item in get_revision_schedule(store=LEARNING_STORE, user_email=payload.user_email, include_all=True, limit=100)]
    return RevisionScheduleResponse(user_email=payload.user_email, generated_at=datetime.now(UTC).isoformat(), items=items)


@router.get("/schedule", response_model=RevisionScheduleResponse)
async def get_schedule(user_email: str = Query(...), include_all: bool = Query(False), limit: int = Query(30, ge=1, le=200)) -> RevisionScheduleResponse:
    items = [RevisionScheduleItem(**item) for item in get_revision_schedule(store=LEARNING_STORE, user_email=user_email, include_all=include_all, limit=limit)]
    return RevisionScheduleResponse(user_email=user_email, generated_at=datetime.now(UTC).isoformat(), items=items)


@router.get("/active-recall/performance", response_model=RecallPerformanceResponse)
async def get_recall_performance(user_email: str = Query(...)) -> RecallPerformanceResponse:
    tracker = LEARNING_STORE.get(user_email, {})
    performance = tracker.get("recall_performance", {}) if isinstance(tracker, dict) else {}
    items = [RecallPerformanceItem(topic=str(entry.get("topic", key)), paper_id=str(entry.get("paper_id", "")), correct=int(entry.get("correct", 0)), incorrect=int(entry.get("incorrect", 0)), last_attempt=str(entry.get("last_attempt", ""))) for key, entry in performance.items() if isinstance(entry, dict)]
    items.sort(key=lambda item: (item.incorrect - item.correct, item.last_attempt), reverse=True)
    return RecallPerformanceResponse(user_email=user_email, items=items)


@router.get("/memory", response_model=UserLearningMemoryResponse)
async def get_user_memory(user_email: str = Query(...)) -> UserLearningMemoryResponse:
    payload = get_user_learning_memory(LEARNING_STORE, user_email)
    topics_studied = [TopicMemoryItem(concept_id=str(key), topic=str(item.get("topic", key)), paper_id=str(item.get("paper_id", "")), count=int(item.get("count", 0)), sources=[str(source) for source in item.get("sources", []) if str(source).strip()], last_seen=str(item.get("last_seen", ""))) for key, item in (payload.get("topics_studied", {}) or {}).items() if isinstance(item, dict)]
    quiz_performance = [QuizPerformanceSummaryItem(concept_id=str(key), topic=str(item.get("topic", key)), paper_id=str(item.get("paper_id", "")), attempts=int(item.get("attempts", 0)), correct=int(item.get("correct", 0)), incorrect=int(item.get("incorrect", 0)), accuracy=float(item.get("accuracy", 0.0)), last_attempt=str(item.get("last_attempt", ""))) for key, item in (payload.get("quiz_performance", {}) or {}).items() if isinstance(item, dict)]
    weak_topics = [WeakTopicItem(concept_id=str(key), concept=str(item.get("concept", key)), paper_id=str(item.get("paper_id", "")), severity=float(item.get("severity", 0.0)), reason=str(item.get("reason", "")), last_seen=str(item.get("last_seen", ""))) for key, item in (payload.get("weak_topics", {}) or {}).items() if isinstance(item, dict)]
    strong_topics = [StrongTopicItem(concept_id=str(key), concept=str(item.get("concept", key)), paper_id=str(item.get("paper_id", "")), confidence=float(item.get("confidence", 0.0)), reason=str(item.get("reason", "")), last_seen=str(item.get("last_seen", ""))) for key, item in (payload.get("strong_topics", {}) or {}).items() if isinstance(item, dict)]
    topics_studied.sort(key=lambda item: (item.count, item.last_seen), reverse=True)
    quiz_performance.sort(key=lambda item: (item.accuracy, item.attempts), reverse=True)
    weak_topics.sort(key=lambda item: item.severity, reverse=True)
    strong_topics.sort(key=lambda item: item.confidence, reverse=True)
    return UserLearningMemoryResponse(user_email=user_email, topics_studied=topics_studied, quiz_performance=quiz_performance, weak_topics=weak_topics, strong_topics=strong_topics, updated_at=str(payload.get("updated_at", datetime.now(UTC).isoformat())))
