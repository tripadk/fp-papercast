from typing import Literal
import logging

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import chat, learning_state, papers, revision, user
from app.routers.chat import _answer_question
from app.routers.chat import router as chat_router
from app.routers.content import router as content_router
from app.routers.events import router as events_router
from app.routers.learning import router as learning_router
from app.routers.learning_state import router as learning_state_router
from app.routers.papers import _build_upload_response, _get_paper_record, _process_upload
from app.routers.papers import router as papers_router
from app.routers.revision import router as revision_router
from app.routers.user import router as user_router
from app.schemas import ChatRequest, ChatResponse, UploadResponse
from app.services.event_ledger_service import init_event_ledger

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

app.include_router(papers.router)
app.include_router(user.router)
app.include_router(chat.router)
app.include_router(revision.router)
app.include_router(learning_state.router)
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
    return await _process_upload(
        file, podcast_length, podcast_style, study_goal, learning_mode, output_language, user_email
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
    return await _process_upload(
        file, podcast_length, podcast_style, study_goal, learning_mode, output_language, user_email
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
    return await _process_upload(
        file, podcast_length, podcast_style, study_goal, learning_mode, output_language, user_email
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_root(payload: ChatRequest) -> ChatResponse:
    return await _answer_question(payload)


@app.get("/status/{content_id}", response_model=UploadResponse)
async def status_root(content_id: str) -> UploadResponse:
    return _build_upload_response(_get_paper_record(content_id))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
