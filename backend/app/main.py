from typing import Literal
import logging
import os

from fastapi import FastAPI, File, Form, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.routers import chat, learning_state, papers, revision, user
from app.routers.chat import _answer_question
from app.routers.content import router as content_router
from app.routers.events import router as events_router
from app.routers.learning import router as learning_router
from app.routers.papers import _build_upload_response, _get_paper_record, _process_upload
from app.schemas import ChatRequest, ChatResponse, PodcastRequest, PodcastResponse, UploadResponse, PaperHistoryResponse, PaperHistoryItem, LearningInsightsResponse, LearningInsightsApiResponse
from app.services.event_ledger_service import init_event_ledger
from app.services.llm_service import generate_podcast_script
from app.store import PAPER_STORE

app = FastAPI(
    title="PaperCast API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
for origin in ("http://localhost:3000", "https://fp-papercast.vercel.app"):
    if origin not in cors_origins:
        cors_origins.append(origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def log_startup_diagnostics() -> None:
    logger.info(
        "Startup diagnostics: groq_api_key_present=%s upload_dir=%s transcript_dir=%s cwd=%s",
        bool(os.getenv("GROQ_API_KEY") or ""),
        settings.upload_dir,
        settings.transcript_dir,
        os.getcwd(),
    )

app.include_router(papers.router)
app.include_router(user.router)
app.include_router(chat.router)
app.include_router(revision.router)
app.include_router(learning_state.router)
app.include_router(learning_state.v1_router)
app.include_router(learning_state.insights_router)
app.include_router(content_router)
app.include_router(events_router)
app.include_router(learning_router)
init_event_ledger()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "API is running"}


@app.post("/upload", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...),
    podcast_length: Literal["quick", "standard", "deep"] = Form("standard"),
    podcast_style: Literal["casual", "lecture", "debate", "news"] = Form("casual"),
    study_goal: Literal["general", "upsc", "jee", "neet", "cat"] = Form("general"),
    learning_mode: Literal["beginner", "exam_mode", "deep_learning", "quick_revision"] = Form("beginner"),
    output_language: Literal["english", "hindi"] = Form("english"),
    user_email: str = Form("anonymous@local"),
) -> UploadResponse:
    logger.info("Upload request received for user=%s filename=%s", user_email, file.filename)
    print(
        f"[route:/upload] request received user_email={user_email} filename={file.filename} "
        f"content_type={file.content_type} podcast_length={podcast_length} podcast_style={podcast_style} "
        f"study_goal={study_goal} learning_mode={learning_mode} output_language={output_language}"
    )
    try:
        return await _process_upload(
            file, podcast_length, podcast_style, study_goal, learning_mode, output_language, user_email
        )
    except Exception as exc:
        logger.exception("Unhandled error in /upload")
        print(f"[route:/upload][error] {type(exc).__name__}: {exc}")
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(
            status_code=status_code,
            content={"error": "upload_failed", "detail": detail, "route": "/upload"},
        )


@app.post("/upload-paper")
async def upload_paper_root(
    file: UploadFile = File(...),
    podcast_length: Literal["quick", "standard", "deep"] = Form("standard"),
    podcast_style: Literal["casual", "lecture", "debate", "news"] = Form("casual"),
    study_goal: Literal["general", "upsc", "jee", "neet", "cat"] = Form("general"),
    learning_mode: Literal["beginner", "exam_mode", "deep_learning", "quick_revision"] = Form("beginner"),
    output_language: Literal["english", "hindi"] = Form("english"),
    user_email: str = Form("anonymous@local"),
) -> UploadResponse:
    print(
        f"[route:/upload-paper] request received user_email={user_email} filename={file.filename} "
        f"content_type={file.content_type}"
    )
    try:
        return await _process_upload(
            file, podcast_length, podcast_style, study_goal, learning_mode, output_language, user_email
        )
    except Exception as exc:
        logger.exception("Unhandled error in /upload-paper")
        print(f"[route:/upload-paper][error] {type(exc).__name__}: {exc}")
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(
            status_code=status_code,
            content={"error": "upload_failed", "detail": detail, "route": "/upload-paper"},
        )


@app.post("/papers/upload", response_model=UploadResponse)
async def upload_paper_alias(
    file: UploadFile = File(...),
    podcast_length: Literal["quick", "standard", "deep"] = Form("standard"),
    podcast_style: Literal["casual", "lecture", "debate", "news"] = Form("casual"),
    study_goal: Literal["general", "upsc", "jee", "neet", "cat"] = Form("general"),
    learning_mode: Literal["beginner", "exam_mode", "deep_learning", "quick_revision"] = Form("beginner"),
    output_language: Literal["english", "hindi"] = Form("english"),
    user_email: str = Form("anonymous@local"),
) -> UploadResponse:
    print(
        f"[route:/papers/upload] request received user_email={user_email} filename={file.filename} "
        f"content_type={file.content_type}"
    )
    try:
        return await _process_upload(
            file, podcast_length, podcast_style, study_goal, learning_mode, output_language, user_email
        )
    except Exception as exc:
        logger.exception("Unhandled error in /papers/upload")
        print(f"[route:/papers/upload][error] {type(exc).__name__}: {exc}")
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(
            status_code=status_code,
            content={"error": "upload_failed", "detail": detail, "route": "/papers/upload"},
        )


@app.post("/chat", response_model=ChatResponse)
async def chat_root(payload: ChatRequest) -> ChatResponse:
    print(f"[route:/chat] request received paper_id={payload.paper_id} history_items={len(payload.history)}")
    try:
        return await _answer_question(payload)
    except Exception as exc:
        logger.exception("Unhandled error in /chat")
        print(f"[route:/chat][error] {type(exc).__name__}: {exc}")
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(
            status_code=status_code,
            content={"error": "chat_failed", "detail": detail, "route": "/chat"},
        )


@app.post("/api/v1/chat", response_model=ChatResponse)
@app.post("/api/v1/chat/", response_model=ChatResponse)
async def api_v1_chat(payload: ChatRequest) -> ChatResponse:
    print(f"[route:/api/v1/chat] request received paper_id={payload.paper_id} history_items={len(payload.history)}")
    try:
        return await _answer_question(payload)
    except Exception as exc:
        logger.exception("Unhandled error in /api/v1/chat")
        print(f"[route:/api/v1/chat][error] {type(exc).__name__}: {exc}")
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(
            status_code=status_code,
            content={"error": "chat_failed", "detail": detail, "route": "/api/v1/chat"},
        )


@app.post("/api/v1/podcast", response_model=PodcastResponse)
@app.post("/api/v1/podcast/", response_model=PodcastResponse)
async def podcast_root(payload: PodcastRequest) -> PodcastResponse:
    print(f"[route:/api/v1/podcast] request received paper_id={payload.paper_id}")
    try:
        record = PAPER_STORE.get(payload.paper_id, {}) if payload.paper_id else {}
        paper_content = str(payload.paper_content or record.get("text", "")).strip()
        if not paper_content:
            paper_content = "Mock paper content: This paper explains a method, a result, and a practical takeaway."
        return PodcastResponse(script=generate_podcast_script(paper_content))
    except Exception as exc:
        logger.exception("Unhandled error in /api/v1/podcast")
        print(f"[route:/api/v1/podcast][error] {type(exc).__name__}: {exc}")
        return PodcastResponse(
            script="Host: We could not generate the podcast right now.\nExpert: Please try again in a moment."
        )


@app.get("/status/{content_id}", response_model=UploadResponse)
@app.get("/papers/status/{content_id}", response_model=UploadResponse)
async def status_root(content_id: str) -> UploadResponse:
    print(f"[route:/status] request received content_id={content_id}")
    try:
        return _build_upload_response(_get_paper_record(content_id))
    except Exception as exc:
        logger.exception("Unhandled error in /status/%s", content_id)
        print(f"[route:/status][error] {type(exc).__name__}: {exc}")
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(
            status_code=status_code,
            content={"error": "status_failed", "detail": detail, "route": f"/status/{content_id}"},
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/api/v1/user/history", response_model=PaperHistoryResponse)
@app.get("/api/v1/user/history/", response_model=PaperHistoryResponse)
async def fallback_get_user_history(user_email: str = Query(...)) -> PaperHistoryResponse:
    history = []
    for pid, record in PAPER_STORE.items():
        if record.get("user_email") == user_email or user_email == "anonymous@local":
            history.append(PaperHistoryItem(
                paper_id=pid,
                user_email=record.get("user_email", "anonymous@local"),
                paper_title=record.get("paper_title") or "Untitled",
                upload_timestamp=record.get("created_at") or "",
                summary=record.get("summary") or "Processing...",
                audio_url=record.get("audio_url") or ""
            ))
    history.sort(key=lambda x: x.upload_timestamp, reverse=True)
    return PaperHistoryResponse(papers=history)

from app.routers.learning_state import get_learning_insights, get_learning_insights_api

@app.get("/api/v1/learning-state", response_model=LearningInsightsResponse)
@app.get("/api/v1/learning-state/", response_model=LearningInsightsResponse)
async def fallback_learning_state_get(user_email: str = Query(...)) -> LearningInsightsResponse:
    return await get_learning_insights(user_email)

@app.get("/api/v1/learning-insights", response_model=LearningInsightsApiResponse)
@app.get("/api/v1/learning-insights/", response_model=LearningInsightsApiResponse)
async def fallback_learning_insights_get(user_email: str = Query(...)) -> LearningInsightsApiResponse:
    return await get_learning_insights_api(user_email)
