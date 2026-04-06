from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas import ChatHistoryResponse, ChatRequest, ChatResponse
from app.services.llm_service import answer_question
from app.store import CHAT_HISTORY, PAPER_STORE, save_state

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
logger = logging.getLogger(__name__)

MOCK_PAPER_CONTENT = (
    "This paper presents a simple research method, tests it on sample data, "
    "and reports a main result with a few limitations."
)


async def _answer_question(payload: ChatRequest) -> ChatResponse:
    paper = PAPER_STORE.get(payload.paper_id, {})
    paper_text = str(paper.get("text", "")).strip() or MOCK_PAPER_CONTENT
    answer = answer_question(context=paper_text, question=payload.question, history=[message.model_dump() for message in payload.history])
    CHAT_HISTORY.setdefault(payload.paper_id or "mock-paper", []).append(
        {
            "paper_id": payload.paper_id or "mock-paper",
            "user_message": payload.question,
            "assistant_response": answer,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )
    save_state()
    return ChatResponse(answer=answer)


@router.post("", response_model=ChatResponse)
async def ask_question_root(payload: ChatRequest) -> ChatResponse:
    logger.info("Chat request received paper_id=%s", payload.paper_id)
    try:
        return await _answer_question(payload)
    except Exception as exc:
        logger.exception("Chat route failed")
        return JSONResponse(
            status_code=200,
            content={"answer": f"Not in paper. Error handled safely: {type(exc).__name__}"},
        )


@router.post("/ask", response_model=ChatResponse)
async def ask_question(payload: ChatRequest) -> ChatResponse:
    return await ask_question_root(payload)


@router.get("/history/{paper_id}", response_model=ChatHistoryResponse)
async def get_chat_history(paper_id: str) -> ChatHistoryResponse:
    return ChatHistoryResponse(messages=CHAT_HISTORY.get(paper_id, []))
