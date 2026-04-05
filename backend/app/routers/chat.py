from fastapi import APIRouter, HTTPException

from datetime import UTC, datetime
import time

from app.schemas import ChatHistoryResponse, ChatRequest, ChatResponse
from app.services.concept_service import normalize_concept
from app.services.event_ledger_service import record_learning_event
from app.services.learning_state_service import get_learning_state_report
from app.services.learning_efficiency_service import update_learning_efficiency
from app.services.confusion_detection_service import update_confusion_status
from app.services.llm_service import answer_question
from app.services.profile_service import get_user_goal
from app.services.spaced_repetition_service import record_strong_topic, record_topic_view, record_weak_area, update_revision_schedule
from app.services.translation_service import translate_text
from app.store import CHAT_HISTORY, CONFUSION_STORE, LEARNING_STORE, PAPER_STORE, save_state

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


async def _answer_question(payload: ChatRequest) -> ChatResponse:
    started = time.perf_counter()
    paper = PAPER_STORE.get(payload.paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found. Upload a paper first.")

    user_email = str(paper.get("user_email", "anonymous@local"))
    concept = normalize_concept(user_id=user_email, content_id=payload.paper_id, raw_text=payload.question)
    state_report = get_learning_state_report(learning_store=LEARNING_STORE, confusion_store=CONFUSION_STORE, user_id=user_email, goal_resolver=get_user_goal)
    topic_state = next((item for item in state_report.get("topics", []) if str(item.get("concept_id", "")) == concept["concept_id"]), {})
    if float(topic_state.get("confusion_level", 0.0)) >= 60:
        learning_mode = "beginner"
    elif float(topic_state.get("mastery_level", 0.0)) >= 80:
        learning_mode = "deep_learning"
    else:
        learning_mode = str(paper.get("learning_mode", "exam_mode"))

    goal = str(paper.get("study_goal", "general")).strip().lower() or get_user_goal(user_email)
    answer = answer_question(
        context=str(paper.get("text", "")),
        question=payload.question,
        history=[message.model_dump() for message in payload.history],
        goal=goal,
        learning_mode=learning_mode,
    )
    answer = translate_text(answer, paper.get("output_language", "english"))

    record_topic_view(store=LEARNING_STORE, user_email=user_email, topic=concept["label"], paper_id=payload.paper_id, confidence=3, source="chat")
    if "does not provide enough information" in answer.lower():
        record_weak_area(store=LEARNING_STORE, user_email=user_email, concept=concept["label"], paper_id=payload.paper_id, reason="insufficient clarity during chat", severity=3, concept_id=concept["concept_id"])
    else:
        record_strong_topic(store=LEARNING_STORE, user_email=user_email, concept=concept["label"], paper_id=payload.paper_id, reason="chat answer handled successfully", confidence=0.6, concept_id=concept["concept_id"])

    response_time_seconds = max(1.0, time.perf_counter() - started)
    inferred_correct = "does not provide enough information" not in answer.lower()
    inferred_accuracy = 1.0 if inferred_correct else 0.0
    record_learning_event(user_id=user_email, content_id=payload.paper_id, concept_id=concept["concept_id"], topic=concept["label"], event_type="chat", correctness=inferred_correct, response_time=response_time_seconds, mode_used=learning_mode)
    update_revision_schedule(store=LEARNING_STORE, user_email=user_email, topic=concept["label"], is_correct=inferred_correct, paper_id=payload.paper_id, accuracy=inferred_accuracy, concept_id=concept["concept_id"])
    update_learning_efficiency(store=LEARNING_STORE, user_id=user_email, topic=concept["label"], accuracy=inferred_accuracy, time_spent=int(round(response_time_seconds)), attempts=1, content_id=payload.paper_id, concept_id=concept["concept_id"])
    update_confusion_status(store=CONFUSION_STORE, paper_store=PAPER_STORE, user_email=user_email, content_id=payload.paper_id, topic=concept["label"], question=payload.question, is_correct=inferred_correct, response_time_seconds=response_time_seconds, concept_id=concept["concept_id"])
    CHAT_HISTORY.setdefault(payload.paper_id, []).append({"paper_id": payload.paper_id, "user_message": payload.question, "assistant_response": answer, "timestamp": datetime.now(UTC).isoformat()})
    save_state()
    get_learning_state_report(learning_store=LEARNING_STORE, confusion_store=CONFUSION_STORE, user_id=user_email, goal_resolver=get_user_goal)
    return ChatResponse(answer=answer)


@router.post("/ask", response_model=ChatResponse)
async def ask_question(payload: ChatRequest) -> ChatResponse:
    return await _answer_question(payload)


@router.get("/history/{paper_id}", response_model=ChatHistoryResponse)
async def get_chat_history(paper_id: str) -> ChatHistoryResponse:
    return ChatHistoryResponse(messages=CHAT_HISTORY.get(paper_id, []))
