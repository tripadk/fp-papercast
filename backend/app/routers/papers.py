from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import re
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.request import Request, urlopen

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.schemas import IngestContentResponse, PaperHistoryResponse, SimplifiedExplanationResponse, UnifiedContent, UploadResponse
from app.schemas import KnowledgeGraphResponse
from app.services.audio_service import generate_podcast_audio
from app.services.knowledge_graph_service import generate_and_store_knowledge_graph, get_knowledge_graph
from app.services.llm_service import (
    explain_like_twelve,
    generate_learning_bundle,
    infer_methodology_steps,
    methodology_steps_to_mermaid,
)
from app.services.learning_state_service import initialize_learning_state_for_content
from app.services.pdf_export_service import generate_pdf
from app.services.pdf_service import extract_text_from_pdf
from app.services.podcast_service import generate_podcast_chapters, generate_timestamped_sentences
from app.services.profile_service import get_user_goal
from app.services.related_papers_service import extract_title_and_abstract, find_related_papers
from app.services.research_toolkit_service import extract_top_citations
from app.services.spaced_repetition_service import record_topic_view
from app.services.translation_service import (
    translate_list,
    translate_related_papers,
    translate_study_notes,
    translate_text,
)
from app.store import CONTENT_STORE, KNOWLEDGE_GRAPH_STORE, LEARNING_STORE, PAPER_HISTORY, PAPER_STORE, save_state

router = APIRouter(prefix="/api/v1/papers", tags=["papers"])
logger = logging.getLogger(__name__)

SECTION_HEADINGS = {
    "abstract": {"abstract"},
    "introduction": {"introduction"},
    "methodology": {"methodology", "methods", "materials and methods", "approach"},
    "conclusion": {"conclusion", "conclusions"},
}


def _cache_dir() -> str:
    base_dir = Path(settings.upload_dir).parent
    cache_dir = os.path.join(str(base_dir), "cache")
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    return cache_dir


def _cache_path(paper_id: str) -> str:
    return os.path.join(_cache_dir(), f"{paper_id}.json")


def _save_cache(record: dict) -> None:
    path = _cache_path(record["paper_id"])
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False)


def _load_cache(paper_id: str) -> dict | None:
    path = _cache_path(paper_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _normalize_for_prompt(text: str) -> str:
    normalized = (text or "").replace("\r", "\n")
    heading_pattern = re.compile(
        r"(?im)^\s*(?:\d+[\.\)]\s*)?"
        r"(abstract|introduction|methodology|methods|materials and methods|approach|conclusion|conclusions|references|bibliography)\s*:?\s*$"
    )
    matches = list(heading_pattern.finditer(normalized))
    if not matches:
        return re.sub(r"\s+", " ", normalized).strip()[:6000]

    selected: list[str] = []
    for idx, match in enumerate(matches):
        heading = match.group(1).lower()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(normalized)
        section_text = normalized[start:end].strip()
        if not section_text:
            continue
        if any(heading in values for values in SECTION_HEADINGS.values()):
            selected.append(section_text[:2200])

    if not selected:
        return re.sub(r"\s+", " ", normalized).strip()[:6000]
    return "\n\n".join(selected)[:6000]


def _load_or_extract_text(pdf_path: str, text_cache_path: str) -> str:
    try:
        if os.path.exists(text_cache_path):
            with open(text_cache_path, "r", encoding="utf-8") as cached:
                return cached.read()

        text = extract_text_from_pdf(pdf_path)
        with open(text_cache_path, "w", encoding="utf-8") as cached:
            cached.write(text)
        return text
    except Exception as exc:
        logger.exception("PDF extraction/OCR failed for path=%s", pdf_path)
        print(f"[upload][pdf-extraction] {type(exc).__name__}: {exc}")
        raise


def _extract_text_from_html(document: str) -> str:
    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", " ", document or "")
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", " ", cleaned)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _fetch_url_text(url: str) -> tuple[str, str]:
    normalized = (url or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="URL is required for source_type=url.")
    if not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"

    try:
        request = Request(
            url=normalized,
            headers={"User-Agent": "PaperCast/1.0 (+content-ingestion)"},
        )
        with urlopen(request, timeout=15) as response:
            payload = response.read()
            content_type = response.headers.get("Content-Type", "").lower()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not fetch URL content: {exc}") from exc

    if "application/pdf" in content_type:
        raise HTTPException(status_code=400, detail="URL points to a PDF. Upload PDF directly through file input.")

    try:
        document = payload.decode("utf-8", errors="ignore")
    except Exception:
        document = payload.decode(errors="ignore")
    text = _extract_text_from_html(document)
    if not text:
        raise HTTPException(status_code=400, detail="No readable text could be extracted from the URL.")
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", document)
    title = re.sub(r"\s+", " ", html.unescape(title_match.group(1))).strip() if title_match else "Web Content"
    return text, (title or "Web Content")


def _build_unified_content(
    paper_id: str,
    title: str,
    raw_text: str,
    source_type: Literal["pdf", "text", "url"],
    created_at: str,
) -> dict:
    return {
        "id": paper_id,
        "title": title,
        "raw_text": raw_text,
        "source_type": source_type,
        "created_at": created_at,
    }


def _quiz_difficulty_for_mode(learning_mode: str) -> str:
    normalized = (learning_mode or "beginner").strip().lower()
    mapping = {
        "beginner": "easy",
        "exam_mode": "medium-hard",
        "deep_learning": "hard",
        "quick_revision": "easy-medium",
    }
    difficulty = mapping.get(normalized, "medium")
    if not difficulty:
        return "medium"
    return str(difficulty)


def _resolve_study_goal(user_email: str, requested_goal: str) -> str:
    valid_goals = {"general", "upsc", "jee", "neet", "cat"}
    normalized = (requested_goal or "general").strip().lower()
    if normalized not in valid_goals:
        normalized = "general"

    if normalized != "general":
        return normalized

    try:
        profile_goal = get_user_goal(user_email)
    except Exception:
        profile_goal = "general"
    profile_goal = (profile_goal or "general").strip().lower()
    return profile_goal if profile_goal in valid_goals else "general"


def _default_study_notes() -> dict[str, str]:
    return {
        "core_idea": "",
        "key_concepts": "",
        "key_points": "",
        "important_results": "",
        "limitations": "",
        "applications": "",
        "quick_revision": "",
    }


def _default_importance_extraction() -> dict[str, list[str]]:
    return {
        "must_know": [],
        "important": [],
        "optional": [],
    }


def _default_knowledge_graph_payload() -> dict[str, Any]:
    return {
        "graph": {"topics": []},
        "navigation": [],
        "learning_path": [],
    }


def _initial_task_status() -> dict[str, str]:
    return {
        "summary": "completed",
        "notes": "pending",
        "flashcards": "pending",
        "transcript": "pending",
        "audio": "pending",
    }


async def _process_upload(
    file: UploadFile,
    podcast_length: Literal["quick", "standard", "deep"] = "standard",
    podcast_style: Literal["casual", "lecture", "debate", "news"] = "casual",
    study_goal: Literal["general", "upsc", "jee", "neet", "cat"] = "general",
    learning_mode: Literal["beginner", "exam_mode", "deep_learning", "quick_revision"] = "beginner",
    output_language: Literal["english", "hindi"] = "english",
    user_email: str = "anonymous@local",
) -> UploadResponse:
    def _raise_upload_error(step: str, exc: Exception) -> None:
        logger.exception("Upload step failed (%s) for filename=%s", step, file.filename)
        print(f"[upload][{step}] {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail=f"{step}: {type(exc).__name__}: {exc}") from exc

    try:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")

        paper_id = str(uuid.uuid4())
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(settings.audio_dir).mkdir(parents=True, exist_ok=True)
        Path(settings.transcript_dir).mkdir(parents=True, exist_ok=True)

        pdf_path = os.path.join(settings.upload_dir, f"{paper_id}.pdf")
        text_cache_path = os.path.join(settings.upload_dir, f"{paper_id}.txt")

        try:
            with open(pdf_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as exc:
            _raise_upload_error("file_handling", exc)

        try:
            text = _load_or_extract_text(pdf_path, text_cache_path)
        except Exception as exc:
            _raise_upload_error("pdf_extraction_or_ocr", exc)

        try:
            title_from_text, _ = extract_title_and_abstract(text)
            paper_title = title_from_text
            return await _process_content(
                paper_id=paper_id,
                raw_text=text,
                title=paper_title,
                source_type="pdf",
                user_email=user_email,
                podcast_length=podcast_length,
                podcast_style=podcast_style,
                study_goal=study_goal,
                learning_mode=learning_mode,
                output_language=output_language,
                text_cache_path=text_cache_path,
            )
        except Exception as exc:
            _raise_upload_error("content_processing", exc)
    except HTTPException:
        logger.exception("Upload failed with HTTPException for filename=%s", file.filename)
        raise
    except Exception as exc:
        _raise_upload_error("unexpected_upload_error", exc)


async def _process_content(
    paper_id: str,
    raw_text: str,
    title: str,
    source_type: Literal["pdf", "text", "url"],
    user_email: str = "anonymous@local",
    podcast_length: Literal["quick", "standard", "deep"] = "standard",
    podcast_style: Literal["casual", "lecture", "debate", "news"] = "casual",
    study_goal: Literal["general", "upsc", "jee", "neet", "cat"] = "general",
    learning_mode: Literal["beginner", "exam_mode", "deep_learning", "quick_revision"] = "beginner",
    output_language: Literal["english", "hindi"] = "english",
    text_cache_path: str = "",
) -> UploadResponse:
    Path(settings.audio_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.transcript_dir).mkdir(parents=True, exist_ok=True)
    text = (raw_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="No readable text was provided for ingestion.")
    study_goal = _resolve_study_goal(user_email=user_email, requested_goal=study_goal)

    limited_text = _normalize_for_prompt(text)
    title_from_text, _ = extract_title_and_abstract(text)
    paper_title = (title or "").strip() or title_from_text or "Untitled Content"
    precomputed_bundle = await asyncio.to_thread(
        generate_learning_bundle,
        limited_text,
        podcast_length,
        podcast_style,
        study_goal,
        learning_mode,
    )
    summary_text = str(precomputed_bundle.get("summary", "")).strip()
    summary_text = translate_text(summary_text, output_language)

    created_at = datetime.now(UTC).isoformat()
    unified_content = _build_unified_content(
        paper_id=paper_id,
        title=paper_title,
        raw_text=text,
        source_type=source_type,
        created_at=created_at,
    )
    CONTENT_STORE[paper_id] = unified_content
    graph_payload = generate_and_store_knowledge_graph(paper_id, text, user_id=user_email)
    if not isinstance(graph_payload, dict):
        graph_payload = _default_knowledge_graph_payload()

    PAPER_STORE[paper_id] = {
        "paper_id": paper_id,
        "title": paper_title,
        "content": unified_content,
        "source_type": source_type,
        "user_email": user_email,
        "text": text,
        "limited_text": limited_text,
        "text_cache_path": text_cache_path,
        "summary": summary_text,
        "key_insights": [],
        "transcript": "",
        "transcript_path": "",
        "audio_path": "",
        "audio_ready": False,
        "audio_url": "",
        "transcript_pdf_path": "",
        "script_pdf_path": "",
        "notes_pdf_path": "",
        "podcast_length": podcast_length,
        "podcast_style": podcast_style,
        "study_goal": study_goal,
        "learning_mode": learning_mode,
        "quiz_difficulty": _quiz_difficulty_for_mode(learning_mode),
        "output_language": output_language,
        "chapters": [],
        "transcript_sentences": [],
        "methodology_steps": [],
        "mermaid_diagram": "flowchart LR\nA[Processing] --> B[Pending]",
        "related_papers": [],
        "top_citations": [],
        "study_notes": _default_study_notes(),
        "importance_extraction": _default_importance_extraction(),
        "precomputed_bundle": precomputed_bundle if isinstance(precomputed_bundle, dict) else {},
        "knowledge_graph": graph_payload.get("graph", {"topics": []}),
        "knowledge_navigation": graph_payload.get("navigation", []),
        "learning_path": graph_payload.get("learning_path", []),
        "generated_flashcards": [],
        "task_status": _initial_task_status(),
        "processing_status": [
            "Processing Paper...",
            "Summary Ready",
            "Notes Pending",
            "Flashcards Pending",
            "Transcript Pending",
            "Audio Pending",
        ],
        "uploaded_at": created_at,
    }
    initialize_learning_state_for_content(
        learning_store=LEARNING_STORE,
        user_id=user_email,
        content_id=paper_id,
        graph_payload=graph_payload,
        goal_resolver=get_user_goal,
    )
    _save_cache(PAPER_STORE[paper_id])
    save_state()

    history_item = {
        "paper_id": paper_id,
        "user_email": user_email,
        "paper_title": paper_title,
        "upload_timestamp": PAPER_STORE[paper_id]["uploaded_at"],
        "summary": summary_text,
        "audio_url": "",
    }
    PAPER_HISTORY.append(history_item)
    save_state()

    asyncio.create_task(_run_background_processing(paper_id))

    return _build_upload_response(PAPER_STORE[paper_id])


async def _run_background_processing(paper_id: str) -> None:
    record = PAPER_STORE.get(paper_id)
    if not isinstance(record, dict):
        return

    def set_status(part: str, value: str) -> None:
        status = record.setdefault("task_status", _initial_task_status())
        status[part] = value
        _save_cache(record)
        save_state()

    try:
        limited_text = str(record.get("limited_text", ""))
        text = str(record.get("text", ""))
        output_language = str(record.get("output_language", "english"))
        podcast_length = str(record.get("podcast_length", "standard"))
        podcast_style = str(record.get("podcast_style", "casual"))
        study_goal = str(record.get("study_goal", "general"))
        learning_mode = str(record.get("learning_mode", "beginner"))

        cached_bundle = record.pop("precomputed_bundle", {})
        if isinstance(cached_bundle, dict) and cached_bundle:
            bundle_result = cached_bundle
            top_citations_result, related_papers_result = await asyncio.gather(
                asyncio.to_thread(extract_top_citations, text, 10),
                asyncio.to_thread(find_related_papers, limited_text),
                return_exceptions=True,
            )
        else:
            bundle_result, top_citations_result, related_papers_result = await asyncio.gather(
                asyncio.to_thread(
                    generate_learning_bundle,
                    limited_text,
                    podcast_length,
                    podcast_style,
                    study_goal,
                    learning_mode,
                ),
                asyncio.to_thread(extract_top_citations, text, 10),
                asyncio.to_thread(find_related_papers, limited_text),
                return_exceptions=True,
            )

        if isinstance(bundle_result, Exception):
            logger.exception("Background bundle failed for paper_id=%s", paper_id)
            return

        study_notes = bundle_result.get("study_notes", {})
        if not isinstance(study_notes, dict):
            study_notes = _default_study_notes()
        study_notes = translate_study_notes(study_notes, output_language)

        flashcards = bundle_result.get("flashcards", [])
        if not isinstance(flashcards, list):
            flashcards = []
        translated_flashcards: list[dict[str, str]] = []
        for card in flashcards:
            if not isinstance(card, dict):
                continue
            translated_flashcards.append(
                {
                    "concept": translate_text(str(card.get("concept", "")).strip(), output_language),
                    "question": translate_text(str(card.get("question", "")).strip(), output_language),
                    "answer": translate_text(str(card.get("answer", "")).strip(), output_language),
                    "hint": translate_text(str(card.get("hint", "")).strip(), output_language),
                }
            )

        transcript = translate_text(str(bundle_result.get("transcript", "")).strip(), output_language)
        if not transcript:
            transcript = f"Host: Let's review this paper.\nExpert: {str(record.get('summary', ''))[:600]}"

        methodology_steps = translate_list(
            [str(item) for item in infer_methodology_steps(limited_text)],
            output_language,
        )
        mermaid_diagram = methodology_steps_to_mermaid(methodology_steps)
        top_citations = top_citations_result if isinstance(top_citations_result, list) else []
        related_papers = related_papers_result if isinstance(related_papers_result, list) else []
        top_citations = translate_list([str(item) for item in top_citations], output_language)
        related_papers = translate_related_papers(related_papers, output_language)

        key_insights = [str(card.get("concept", "")).strip() for card in translated_flashcards if str(card.get("concept", "")).strip()][:6]
        importance_extraction = {
            "must_know": [str(card.get("answer", "")).strip() for card in translated_flashcards[:3] if str(card.get("answer", "")).strip()],
            "important": [str(card.get("answer", "")).strip() for card in translated_flashcards[3:6] if str(card.get("answer", "")).strip()],
            "optional": [str(card.get("answer", "")).strip() for card in translated_flashcards[6:9] if str(card.get("answer", "")).strip()],
        }

        record["study_notes"] = study_notes
        record["generated_flashcards"] = translated_flashcards
        record["key_insights"] = key_insights
        record["importance_extraction"] = importance_extraction
        record["methodology_steps"] = methodology_steps
        record["mermaid_diagram"] = mermaid_diagram
        record["top_citations"] = top_citations
        record["related_papers"] = related_papers
        set_status("notes", "completed")
        set_status("flashcards", "completed")

        chapters = await asyncio.to_thread(generate_podcast_chapters, transcript)
        transcript_sentences = await asyncio.to_thread(generate_timestamped_sentences, transcript)
        transcript_file_path = os.path.join(settings.transcript_dir, f"{paper_id}.txt")
        with open(transcript_file_path, "w", encoding="utf-8") as transcript_file:
            transcript_file.write(transcript)

        notes_content = (
            f"Core Idea\n{study_notes.get('core_idea', '')}\n\n"
            f"Key Concepts\n{study_notes.get('key_concepts', '')}\n\n"
            f"Key Points\n{study_notes.get('key_points', '')}\n\n"
            f"Important Results\n{study_notes.get('important_results', '')}\n\n"
            f"Limitations\n{study_notes.get('limitations', '')}\n\n"
            f"Applications\n{study_notes.get('applications', '')}\n\n"
            f"Quick Revision\n{study_notes.get('quick_revision', '')}"
        )

        transcript_pdf_path = generate_pdf("PaperCast Transcript", transcript, settings.transcript_dir, f"{paper_id}_transcript")
        script_pdf_path = generate_pdf("PaperCast Podcast Script", transcript, settings.transcript_dir, f"{paper_id}_script")
        notes_pdf_path = generate_pdf("PaperCast Study Notes", notes_content, settings.transcript_dir, f"{paper_id}_notes")

        record["transcript"] = transcript
        record["transcript_path"] = transcript_file_path
        record["transcript_sentences"] = transcript_sentences
        record["chapters"] = chapters
        record["transcript_pdf_path"] = transcript_pdf_path
        record["script_pdf_path"] = script_pdf_path
        record["notes_pdf_path"] = notes_pdf_path
        set_status("transcript", "completed")

        try:
            audio_filename = await asyncio.to_thread(generate_podcast_audio, transcript, settings.audio_dir)
            record["audio_path"] = os.path.join(settings.audio_dir, audio_filename)
            record["audio_url"] = f"/api/v1/papers/audio/{audio_filename}"
            record["audio_ready"] = True
        except Exception:
            logger.exception("Audio generation failed for paper_id=%s", paper_id)
            record["audio_ready"] = False
        set_status("audio", "completed")

        status = record.get("task_status", {})
        record["processing_status"] = [
            "Summary Ready" if status.get("summary") == "completed" else "Summary Pending",
            "Notes Ready" if status.get("notes") == "completed" else "Notes Pending",
            "Flashcards Ready" if status.get("flashcards") == "completed" else "Flashcards Pending",
            "Transcript Ready" if status.get("transcript") == "completed" else "Transcript Pending",
            "Audio Ready" if status.get("audio") == "completed" and record.get("audio_ready") else "Audio Pending",
        ]
        _save_cache(record)
    except Exception:
        logger.exception("Unexpected background processing failure for paper_id=%s", paper_id)


def _build_upload_response(record: dict) -> UploadResponse:
    study_notes = record.get("study_notes", {}) or {}
    importance_extraction = record.get("importance_extraction", {}) or {}
    transcript_file = os.path.basename(str(record.get("transcript_path", "")).strip()) if str(record.get("transcript_path", "")).strip() else ""
    audio_file = os.path.basename(str(record.get("audio_path", "")).strip()) if str(record.get("audio_path", "")).strip() else ""
    transcript_pdf = os.path.basename(str(record.get("transcript_pdf_path", "")).strip()) if str(record.get("transcript_pdf_path", "")).strip() else ""
    script_pdf = os.path.basename(str(record.get("script_pdf_path", "")).strip()) if str(record.get("script_pdf_path", "")).strip() else ""
    notes_pdf = os.path.basename(str(record.get("notes_pdf_path", "")).strip()) if str(record.get("notes_pdf_path", "")).strip() else ""
    graph_payload = get_knowledge_graph(str(record.get("paper_id", "")).strip()) or {}
    knowledge_graph = record.get("knowledge_graph", graph_payload.get("graph", {"topics": []}))
    knowledge_navigation = record.get("knowledge_navigation", graph_payload.get("navigation", []))
    learning_path = record.get("learning_path", graph_payload.get("learning_path", []))
    quiz_difficulty = str(record.get("quiz_difficulty", "medium") or "").strip()
    if not quiz_difficulty:
        quiz_difficulty = "medium"
    return UploadResponse(
        paper_id=record.get("paper_id", ""),
        summary=record.get("summary", ""),
        transcript_path=f"/api/v1/papers/transcript/{transcript_file}" if transcript_file else "",
        audio_path=f"/api/v1/papers/audio/{audio_file}" if audio_file else "",
        audio_url=record.get("audio_url"),
        audio_ready=bool(record.get("audio_ready", False)),
        transcript_download_url=f"/api/v1/papers/download/{transcript_pdf}" if transcript_pdf else "",
        podcast_script_download_url=f"/api/v1/papers/download/{script_pdf}" if script_pdf else "",
        notes_download_url=f"/api/v1/papers/download/{notes_pdf}" if notes_pdf else "",
        podcast_length=record.get("podcast_length", "standard"),
        podcast_style=record.get("podcast_style", "casual"),
        study_goal=record.get("study_goal", "general"),
        learning_mode=record.get("learning_mode", "beginner"),
        quiz_difficulty=quiz_difficulty,
        output_language=record.get("output_language", "english"),
        chapters=record.get("chapters", []),
        transcript_sentences=record.get("transcript_sentences", []),
        methodology_steps=record.get("methodology_steps", []),
        mermaid_diagram=record.get("mermaid_diagram", "flowchart LR\nA[Problem] --> B[Approach] --> C[Results]"),
        related_papers=record.get("related_papers", []),
        top_citations=record.get("top_citations", []),
        study_notes={
            "core_idea": study_notes.get("core_idea", ""),
            "key_concepts": study_notes.get("key_concepts", ""),
            "key_points": study_notes.get("key_points", ""),
            "important_results": study_notes.get("important_results", ""),
            "limitations": study_notes.get("limitations", ""),
            "applications": study_notes.get("applications", ""),
            "quick_revision": study_notes.get("quick_revision", ""),
        },
        importance_extraction={
            "must_know": [str(item) for item in importance_extraction.get("must_know", []) if str(item).strip()],
            "important": [str(item) for item in importance_extraction.get("important", []) if str(item).strip()],
            "optional": [str(item) for item in importance_extraction.get("optional", []) if str(item).strip()],
        },
        knowledge_graph=knowledge_graph if isinstance(knowledge_graph, dict) else {"topics": []},
        knowledge_navigation=knowledge_navigation if isinstance(knowledge_navigation, list) else [],
        learning_path=learning_path if isinstance(learning_path, list) else [],
        task_status={str(key): str(value) for key, value in (record.get("task_status", {}) or {}).items()},
        processing_status=record.get("processing_status", []),
    )


def _get_paper_record(paper_id: str) -> dict:
    paper = PAPER_STORE.get(paper_id)
    if not paper:
        paper = _load_cache(paper_id)
        if paper:
            PAPER_STORE[paper_id] = paper
            save_state()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return paper


def _build_unified_content_response(record: dict) -> UnifiedContent:
    content = record.get("content")
    if isinstance(content, dict):
        return UnifiedContent(
            id=str(content.get("id", record.get("paper_id", ""))),
            title=str(content.get("title", record.get("title", ""))),
            raw_text=str(content.get("raw_text", record.get("text", ""))),
            source_type=str(content.get("source_type", record.get("source_type", "pdf"))),
            created_at=str(content.get("created_at", record.get("uploaded_at", ""))),
        )
    return UnifiedContent(
        id=str(record.get("paper_id", "")),
        title=str(record.get("title", "")),
        raw_text=str(record.get("text", "")),
        source_type=str(record.get("source_type", "pdf")),
        created_at=str(record.get("uploaded_at", "")),
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_paper(
    file: UploadFile = File(...),
    podcast_length: Literal["quick", "standard", "deep"] = Form("standard"),
    podcast_style: Literal["casual", "lecture", "debate", "news"] = Form("casual"),
    study_goal: Literal["general", "upsc", "jee", "neet", "cat"] = Form("general"),
    learning_mode: Literal["beginner", "exam_mode", "deep_learning", "quick_revision"] = Form("beginner"),
    output_language: Literal["english", "hindi"] = Form("english"),
    user_email: str = Form("anonymous@local"),
) -> UploadResponse:
    logger.info(
        "Paper upload route hit user_email=%s filename=%s content_type=%s",
        user_email,
        file.filename,
        file.content_type,
    )
    print(
        f"[route:/api/v1/papers/upload] request received user_email={user_email} filename={file.filename} "
        f"content_type={file.content_type}"
    )
    try:
        return await _process_upload(
            file, podcast_length, podcast_style, study_goal, learning_mode, output_language, user_email
        )
    except Exception as exc:
        logger.exception("Unhandled error in /api/v1/papers/upload")
        print(f"[route:/api/v1/papers/upload][error] {type(exc).__name__}: {exc}")
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(
            status_code=status_code,
            content={"error": "paper_upload_failed", "detail": detail, "route": "/api/v1/papers/upload"},
        )


@router.post("/ingest", response_model=IngestContentResponse)
async def ingest_content(
    file: UploadFile | None = File(None),
    raw_text: str = Form(""),
    source_url: str = Form(""),
    title: str = Form(""),
    podcast_length: Literal["quick", "standard", "deep"] = Form("standard"),
    podcast_style: Literal["casual", "lecture", "debate", "news"] = Form("casual"),
    study_goal: Literal["general", "upsc", "jee", "neet", "cat"] = Form("general"),
    learning_mode: Literal["beginner", "exam_mode", "deep_learning", "quick_revision"] = Form("beginner"),
    output_language: Literal["english", "hindi"] = Form("english"),
    user_email: str = Form("anonymous@local"),
) -> IngestContentResponse:
    sources_selected = int(file is not None) + int(bool(raw_text.strip())) + int(bool(source_url.strip()))
    if sources_selected != 1:
        raise HTTPException(status_code=400, detail="Provide exactly one input source: file, raw_text, or source_url.")

    paper_id = str(uuid.uuid4())
    text_cache_path = ""
    source_type: Literal["pdf", "text", "url"]
    source_text = ""
    resolved_title = title.strip()

    if file is not None:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported for file ingestion.")
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
        pdf_path = os.path.join(settings.upload_dir, f"{paper_id}.pdf")
        text_cache_path = os.path.join(settings.upload_dir, f"{paper_id}.txt")
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        source_text = _load_or_extract_text(pdf_path, text_cache_path)
        source_type = "pdf"
    elif raw_text.strip():
        source_text = raw_text.strip()
        source_type = "text"
    else:
        source_text, fetched_title = _fetch_url_text(source_url)
        source_type = "url"
        if not resolved_title:
            resolved_title = fetched_title

    upload_response = await _process_content(
        paper_id=paper_id,
        raw_text=source_text,
        title=resolved_title,
        source_type=source_type,
        user_email=user_email,
        podcast_length=podcast_length,
        podcast_style=podcast_style,
        study_goal=study_goal,
        learning_mode=learning_mode,
        output_language=output_language,
        text_cache_path=text_cache_path,
    )
    paper_record = _get_paper_record(paper_id)
    return IngestContentResponse(content=_build_unified_content_response(paper_record), analysis=upload_response)


@router.get("/history", response_model=PaperHistoryResponse)
async def get_history(user_email: str = Query(...)) -> PaperHistoryResponse:
    logger.info("Paper history requested user_email=%s", user_email)
    print(f"[route:/api/v1/papers/history] request received user_email={user_email}")
    try:
        papers = [item for item in PAPER_HISTORY if item.get("user_email") == user_email]
        papers.sort(key=lambda item: item.get("upload_timestamp", ""), reverse=True)
        return PaperHistoryResponse(papers=papers)
    except Exception as exc:
        logger.exception("Unhandled error in /api/v1/papers/history for user_email=%s", user_email)
        print(f"[route:/api/v1/papers/history][error] {type(exc).__name__}: {exc}")
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(
            status_code=status_code,
            content={"error": "paper_history_failed", "detail": detail, "route": "/api/v1/papers/history"},
        )


@router.get("/{paper_id}", response_model=UploadResponse)
async def get_paper_detail(paper_id: str, user_email: str = Query("")) -> UploadResponse:
    print(f"[route:/api/v1/papers/{{paper_id}}] request received paper_id={paper_id} user_email={user_email}")
    try:
        paper = _get_paper_record(paper_id)
        effective_user_email = user_email.strip() or str(paper.get("user_email", "")).strip()
        if effective_user_email:
            record_topic_view(
                store=LEARNING_STORE,
                user_email=effective_user_email,
                topic=str(paper.get("title", "paper detail view")).strip() or "paper detail view",
                paper_id=paper_id,
                confidence=4,
                source="content_view",
            )
        return _build_upload_response(paper)
    except Exception as exc:
        logger.exception("Unhandled error in /api/v1/papers/%s", paper_id)
        print(f"[route:/api/v1/papers/{{paper_id}}][error] {type(exc).__name__}: {exc}")
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(
            status_code=status_code,
            content={"error": "paper_detail_failed", "detail": detail, "route": f"/api/v1/papers/{paper_id}"},
        )


@router.get("/status/{content_id}", response_model=UploadResponse)
async def get_processing_status(content_id: str) -> UploadResponse:
    print(f"[route:/api/v1/papers/status/{{content_id}}] request received content_id={content_id}")
    try:
        paper = _get_paper_record(content_id)
        return _build_upload_response(paper)
    except Exception as exc:
        logger.exception("Unhandled error in /api/v1/papers/status/%s", content_id)
        print(f"[route:/api/v1/papers/status/{{content_id}}][error] {type(exc).__name__}: {exc}")
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(
            status_code=status_code,
            content={
                "error": "paper_status_failed",
                "detail": detail,
                "route": f"/api/v1/papers/status/{content_id}",
            },
        )


@router.get("/{content_id}/knowledge-graph", response_model=KnowledgeGraphResponse)
async def get_content_knowledge_graph(content_id: str) -> KnowledgeGraphResponse:
    _get_paper_record(content_id)
    payload = KNOWLEDGE_GRAPH_STORE.get(content_id)
    if not isinstance(payload, dict):
        payload = _default_knowledge_graph_payload()
    return KnowledgeGraphResponse(
        content_id=content_id,
        knowledge_graph=payload.get("graph", {"topics": []}),
        knowledge_navigation=payload.get("navigation", []),
        learning_path=payload.get("learning_path", []),
    )


@router.post("/{paper_id}/explain-like-im-12", response_model=SimplifiedExplanationResponse)
async def explain_paper_like_twelve(paper_id: str) -> SimplifiedExplanationResponse:
    paper = _get_paper_record(paper_id)
    explanation = await asyncio.to_thread(explain_like_twelve, paper.get("text", ""), paper.get("summary", ""))
    explanation = translate_text(explanation, paper.get("output_language", "english"))
    paper["simple_explanation"] = explanation
    _save_cache(paper)
    return SimplifiedExplanationResponse(paper_id=paper_id, explanation=explanation)


@router.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = os.path.join(settings.audio_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(path=file_path, filename=filename)


@router.get("/transcript/{filename}")
async def get_transcript(filename: str):
    file_path = os.path.join(settings.transcript_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Transcript file not found.")
    return FileResponse(path=file_path, media_type="text/plain; charset=utf-8", filename=filename)


@router.get("/download/{filename}")
async def download_pdf(filename: str):
    file_path = os.path.join(settings.transcript_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF file not found.")
    return FileResponse(path=file_path, media_type="application/pdf", filename=filename)
