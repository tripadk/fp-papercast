"""
PaperCast API - minimal, self-contained entry point.
All heavy sub-module imports happen INSIDE handlers (lazy) so that any
broken dependency can never prevent the server from starting.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PaperCast API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory paper store (shared across handlers via lazy import fallback)
# ---------------------------------------------------------------------------
_FALLBACK_STORE: dict[str, Any] = {}


def _paper_store() -> dict[str, Any]:
    try:
        from app.store import PAPER_STORE  # type: ignore
        return PAPER_STORE
    except Exception:
        return _FALLBACK_STORE


# ---------------------------------------------------------------------------
# Safe router loader - won't crash the app if a router fails to import
# ---------------------------------------------------------------------------
def _include(module: str, attr: str = "router", **kw: Any) -> None:
    try:
        import importlib
        mod = importlib.import_module(module)
        app.include_router(getattr(mod, attr), **kw)
        logger.info("✓ router: %s", module)
    except Exception as exc:
        logger.warning("✗ router skipped (%s): %s", module, exc)


_include("app.routers.papers")
_include("app.routers.user")
_include("app.routers.chat")
_include("app.routers.revision")
_include("app.routers.learning_state")
_include("app.routers.content", attr="router")
_include("app.routers.events",   attr="router")
_include("app.routers.learning")

try:
    from app.services.event_ledger_service import init_event_ledger
    init_event_ledger()
except Exception as exc:
    logger.warning("event_ledger skipped: %s", exc)


# ---------------------------------------------------------------------------
# Core health endpoints
# ---------------------------------------------------------------------------
@app.get("/", tags=["health"])
def root() -> dict:
    return {"message": "PaperCast API is running", "docs": "/docs"}


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/v1/chat
# ---------------------------------------------------------------------------
@app.post("/api/v1/chat", tags=["chat"])
@app.post("/api/v1/chat/", tags=["chat"], include_in_schema=False)
@app.post("/chat", tags=["chat"], include_in_schema=False)
async def api_chat(payload: dict[str, Any]) -> dict:
    print("Chat endpoint hit")
    question = str(payload.get("question", "")).strip()
    paper_id = str(payload.get("paper_id", "")).strip()

    try:
        from app.routers.chat import _answer_question  # type: ignore
        from app.schemas import ChatMessage, ChatRequest  # type: ignore

        history_raw = payload.get("history", [])
        history = [
            ChatMessage(role=m["role"], content=m["content"])
            for m in history_raw
            if isinstance(m, dict) and m.get("role") in ("user", "assistant")
        ]
        req = ChatRequest(paper_id=paper_id or "unknown", question=question or "hello", history=history)
        result = await _answer_question(req)
        return result if isinstance(result, dict) else result.dict()
    except Exception as exc:
        logger.warning("Chat LLM failed, returning mock: %s", exc)
        return {"answer": f"Mock answer for: {question or '(empty)'}"}


# ---------------------------------------------------------------------------
# POST /api/v1/podcast
# ---------------------------------------------------------------------------
@app.post("/api/v1/podcast", tags=["podcast"])
@app.post("/api/v1/podcast/", tags=["podcast"], include_in_schema=False)
async def api_podcast(payload: dict[str, Any]) -> dict:
    print("Podcast endpoint hit")
    paper_id = str(payload.get("paper_id", "")).strip()
    paper_content = str(payload.get("paper_content", "")).strip()

    # Try real LLM script generation
    try:
        from app.services.llm_service import generate_podcast_script  # type: ignore
        if not paper_content and paper_id:
            store = _paper_store()
            paper_content = str(store.get(paper_id, {}).get("text", "")).strip()
        if not paper_content:
            paper_content = "This paper presents a novel research contribution in the field of AI."
        script = generate_podcast_script(paper_content)
        return {"script": script}
    except Exception as exc:
        logger.warning("Podcast LLM failed, returning mock: %s", exc)
        return {
            "script": (
                "Host: Welcome to PaperCast!\n"
                "Expert: Today we're breaking down an exciting research paper.\n"
                "Host: What's the main idea?\n"
                "Expert: The paper introduces a novel approach and demonstrates clear results.\n"
                "Host: Great — thanks for the breakdown!\n"
                "Expert: Happy listening!"
            )
        }


# ---------------------------------------------------------------------------
# GET /api/v1/papers/history
# ---------------------------------------------------------------------------
@app.get("/api/v1/papers/history", tags=["papers"])
@app.get("/api/v1/papers/history/", tags=["papers"], include_in_schema=False)
@app.get("/api/v1/user/history", tags=["papers"], include_in_schema=False)
@app.get("/api/v1/user/history/", tags=["papers"], include_in_schema=False)
async def api_papers_history(user_email: str = Query("anonymous@local")) -> dict:
    print(f"Papers history endpoint hit: user={user_email}")
    store = _paper_store()
    papers = []
    for pid, rec in store.items():
        if not isinstance(rec, dict):
            continue
        rec_email = str(rec.get("user_email", "")).strip()
        if rec_email == user_email or rec_email == "" or user_email == "anonymous@local":
            papers.append({
                "paper_id": pid,
                "id": pid,
                "user_email": rec_email or user_email,
                "paper_title": rec.get("title") or rec.get("paper_title") or "Untitled",
                "title": rec.get("title") or rec.get("paper_title") or "Untitled",
                "upload_timestamp": rec.get("uploaded_at") or rec.get("created_at") or "",
                "summary": rec.get("summary") or "Processing…",
                "audio_url": rec.get("audio_url") or "",
            })
    papers.sort(key=lambda x: x["upload_timestamp"], reverse=True)
    return {"papers": papers}


# ---------------------------------------------------------------------------
# GET /api/v1/learning-insights  (lightweight mock, no heavy deps)
# ---------------------------------------------------------------------------
@app.get("/api/v1/learning-insights", tags=["learning"])
@app.get("/api/v1/learning-insights/", tags=["learning"], include_in_schema=False)
@app.get("/api/v1/learning-state", tags=["learning"], include_in_schema=False)
@app.get("/api/v1/learning-state/", tags=["learning"], include_in_schema=False)
async def api_learning_insights(user_email: str = Query("anonymous@local")) -> dict:
    print(f"Learning insights endpoint hit: user={user_email}")
    return {
        "user_email": user_email,
        "progress_summary": "You are making solid progress.",
        "strengths": ["Grasping core concepts", "Consistent engagement"],
        "weaknesses": ["Methodology depth"],
        "recommendations": ["Re-read the results section", "Try the quiz"],
        "progress": {"completed_topics": 1, "average_score": 0.75},
        "weak_topics": [],
    }


# ---------------------------------------------------------------------------
# Status aliases  (used by frontend polling)
# ---------------------------------------------------------------------------
@app.get("/status/{content_id}", tags=["papers"], include_in_schema=False)
@app.get("/papers/status/{content_id}", tags=["papers"], include_in_schema=False)
@app.get("/api/v1/papers/status/{content_id}", tags=["papers"])
async def api_status(content_id: str) -> Any:
    print(f"Status endpoint hit: content_id={content_id}")
    try:
        from app.routers.papers import _build_upload_response, _get_paper_record  # type: ignore
        return _build_upload_response(_get_paper_record(content_id))
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Paper {content_id} not found") from exc


# ---------------------------------------------------------------------------
# Upload aliases  (actual logic lives in app.routers.papers)
# ---------------------------------------------------------------------------
@app.post("/upload", tags=["papers"], include_in_schema=False)
@app.post("/upload-paper", tags=["papers"], include_in_schema=False)
@app.post("/papers/upload", tags=["papers"], include_in_schema=False)
async def upload_alias(
    file: UploadFile = File(...),
    podcast_length: str = Form("standard"),
    podcast_style: str = Form("casual"),
    study_goal: str = Form("general"),
    learning_mode: str = Form("beginner"),
    output_language: str = Form("english"),
    user_email: str = Form("anonymous@local"),
) -> Any:
    print(f"[upload] user={user_email} file={file.filename}")
    try:
        from app.routers.papers import _process_upload  # type: ignore
        return await _process_upload(
            file, podcast_length, podcast_style, study_goal, learning_mode, output_language, user_email
        )
    except Exception as exc:
        logger.exception("upload failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Startup log
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup() -> None:
    key_present = bool(os.getenv("GROQ_API_KEY", ""))
    print(f"[startup] PaperCast API ready. GROQ_API_KEY={key_present} CWD={os.getcwd()}")
    logger.info("startup complete. groq_key_present=%s", key_present)
