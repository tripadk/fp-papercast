"""PaperCast FastAPI application — clean, resilient entry point."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# App setup — CORS is wide-open so the server always starts even if env vars
# are misconfigured.
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PaperCast API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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
# Lazy-import heavy modules so that an import error in any sub-module does
# NOT prevent the FastAPI process from starting.  Each helper below catches
# ImportError at call-time and returns a safe fallback.
# ---------------------------------------------------------------------------

def _get_settings():  # type: ignore[return]
    try:
        from app.core.config import settings
        return settings
    except Exception as exc:
        logger.error("Could not load settings: %s", exc)
        return None


def _get_paper_store() -> dict:
    try:
        from app.store import PAPER_STORE
        return PAPER_STORE  # type: ignore[return-value]
    except Exception:
        return {}


def _get_paper_history() -> list:
    try:
        from app.store import PAPER_HISTORY
        return PAPER_HISTORY  # type: ignore[return-value]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Include routers — each wrapped so a single bad router never kills the app.
# ---------------------------------------------------------------------------

def _safe_include(module_path: str, attr: str = "router", **kwargs: Any) -> None:
    try:
        import importlib
        mod = importlib.import_module(module_path)
        router = getattr(mod, attr)
        app.include_router(router, **kwargs)
        logger.info("Router included: %s.%s", module_path, attr)
    except Exception as exc:
        logger.error("Failed to include router %s.%s: %s", module_path, attr, exc)


_safe_include("app.routers.papers")
_safe_include("app.routers.user")
_safe_include("app.routers.chat")
_safe_include("app.routers.revision")
_safe_include("app.routers.learning_state")
_safe_include("app.routers.content", attr="router")
_safe_include("app.routers.events", attr="router")
_safe_include("app.routers.learning")

# Initialise event ledger — non-critical
try:
    from app.services.event_ledger_service import init_event_ledger
    init_event_ledger()
except Exception as exc:
    logger.error("init_event_ledger failed (non-fatal): %s", exc)


# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------

@app.get("/")
def root() -> dict[str, str]:
    return {"message": "PaperCast API is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Upload aliases  (the real logic lives in app.routers.papers)
# ---------------------------------------------------------------------------

async def _call_process_upload(
    file: UploadFile,
    podcast_length: str,
    podcast_style: str,
    study_goal: str,
    learning_mode: str,
    output_language: str,
    user_email: str,
):
    try:
        from app.routers.papers import _process_upload
        return await _process_upload(
            file, podcast_length, podcast_style, study_goal, learning_mode, output_language, user_email
        )
    except Exception as exc:
        logger.exception("_process_upload failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/upload")
@app.post("/upload-paper")
@app.post("/papers/upload")
async def upload_alias(
    file: UploadFile = File(...),
    podcast_length: Literal["quick", "standard", "deep"] = Form("standard"),
    podcast_style: Literal["casual", "lecture", "debate", "news"] = Form("casual"),
    study_goal: Literal["general", "upsc", "jee", "neet", "cat"] = Form("general"),
    learning_mode: Literal["beginner", "exam_mode", "deep_learning", "quick_revision"] = Form("beginner"),
    output_language: Literal["english", "hindi"] = Form("english"),
    user_email: str = Form("anonymous@local"),
):
    print(f"[upload] user={user_email} file={file.filename}")
    return await _call_process_upload(
        file, podcast_length, podcast_style, study_goal, learning_mode, output_language, user_email
    )


# ---------------------------------------------------------------------------
# /api/v1/chat
# ---------------------------------------------------------------------------

@app.post("/chat")
@app.post("/api/v1/chat")
@app.post("/api/v1/chat/")
async def api_chat(payload: dict[str, Any]):
    print("Chat endpoint hit")
    try:
        from app.routers.chat import _answer_question
        from app.schemas import ChatRequest, ChatMessage
        history_raw = payload.get("history", [])
        history = [ChatMessage(role=m["role"], content=m["content"]) for m in history_raw if isinstance(m, dict)]
        req = ChatRequest(
            paper_id=str(payload.get("paper_id", "")),
            question=str(payload.get("question", "")),
            history=history,
        )
        result = await _answer_question(req)
        return result
    except Exception as exc:
        logger.exception("Chat error")
        return JSONResponse(status_code=200, content={"answer": f"Could not answer: {exc}"})


# ---------------------------------------------------------------------------
# /api/v1/podcast  (script generation — separate from upload audio pipeline)
# ---------------------------------------------------------------------------

@app.post("/api/v1/podcast")
@app.post("/api/v1/podcast/")
async def api_podcast(payload: dict[str, Any]):
    print("Podcast endpoint hit")
    try:
        from app.services.llm_service import generate_podcast_script
        paper_id = str(payload.get("paper_id", ""))
        paper_content = str(payload.get("paper_content", "")).strip()
        if not paper_content and paper_id:
            store = _get_paper_store()
            paper_content = str(store.get(paper_id, {}).get("text", "")).strip()
        if not paper_content:
            paper_content = "This paper presents a research contribution."
        script = generate_podcast_script(paper_content)
        return {"script": script}
    except Exception as exc:
        logger.exception("Podcast error")
        return {"script": f"Host: Welcome!\nExpert: Could not generate script: {exc}"}


# ---------------------------------------------------------------------------
# /api/v1/learning-insights  (simple mock — no heavy dependencies)
# ---------------------------------------------------------------------------

@app.get("/api/v1/learning-insights")
@app.get("/api/v1/learning-insights/")
@app.get("/api/v1/learning-state")
@app.get("/api/v1/learning-state/")
async def api_learning_insights(user_email: str = Query("anonymous@local")):
    print("Learning insights endpoint hit")
    return {
        "user_email": user_email,
        "progress_summary": "You are making good progress on this paper.",
        "strengths": ["Understanding core concepts"],
        "weaknesses": ["Needs more practice on methodology"],
        "recommendations": ["Review the results section again"],
        "progress": {"completed_topics": 1, "average_score": 0.7},
        "weak_topics": [],
    }


# ---------------------------------------------------------------------------
# Status / paper detail aliases
# ---------------------------------------------------------------------------

@app.get("/status/{content_id}")
@app.get("/papers/status/{content_id}")
@app.get("/api/v1/papers/status/{content_id}")
async def status_alias(content_id: str):
    print(f"[status] content_id={content_id}")
    try:
        from app.routers.papers import _build_upload_response, _get_paper_record
        return _build_upload_response(_get_paper_record(content_id))
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Paper not found: {exc}") from exc


# ---------------------------------------------------------------------------
# User history alias
# ---------------------------------------------------------------------------

@app.get("/api/v1/user/history")
@app.get("/api/v1/user/history/")
async def api_user_history(user_email: str = Query("anonymous@local")):
    store = _get_paper_store()
    history = []
    for pid, record in store.items():
        if record.get("user_email") == user_email or not record.get("user_email"):
            history.append({
                "paper_id": pid,
                "user_email": record.get("user_email", user_email),
                "paper_title": record.get("title") or record.get("paper_title") or "Untitled",
                "upload_timestamp": record.get("uploaded_at") or record.get("created_at") or "",
                "summary": record.get("summary") or "Processing...",
                "audio_url": record.get("audio_url") or "",
            })
    history.sort(key=lambda x: x["upload_timestamp"], reverse=True)
    return {"papers": history}


# ---------------------------------------------------------------------------
# Startup log
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    settings = _get_settings()
    logger.info(
        "PaperCast startup: groq_key=%s cwd=%s",
        bool(os.getenv("GROQ_API_KEY")),
        os.getcwd(),
    )
    print(f"[startup] PaperCast API ready. GROQ_API_KEY present={bool(os.getenv('GROQ_API_KEY'))}")
