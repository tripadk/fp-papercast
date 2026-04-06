from __future__ import annotations

import os
import time
import uuid

from gtts import gTTSError
from gtts import gTTS


def synthesize_audio(transcript: str, output_dir: str, filename_stem: str) -> str:
    os.makedirs(output_dir, exist_ok=True)

    final_path = os.path.join(output_dir, f"{filename_stem}.mp3")
    chunks = _split_text(transcript, max_chars=3800)
    temp_paths: list[str] = []

    try:
        for index, chunk in enumerate(chunks):
            temp_path = os.path.join(output_dir, f"{filename_stem}.part{index}.mp3")
            _save_chunk_with_retries(chunk, temp_path)
            temp_paths.append(temp_path)

        with open(final_path, "wb") as final_file:
            for temp_path in temp_paths:
                with open(temp_path, "rb") as part_file:
                    final_file.write(part_file.read())
    finally:
        for temp_path in temp_paths:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    return final_path


def _save_chunk_with_retries(text: str, path: str, retries: int = 3, backoff_seconds: float = 1.0) -> None:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            tts = gTTS(text)
            tts.save(path)
            return
        except (gTTSError, OSError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(backoff_seconds * (attempt + 1))
    if last_error is not None:
        raise RuntimeError(f"gTTS failed after {retries} attempts: {last_error}") from last_error
    raise RuntimeError("gTTS failed unexpectedly.")


def _split_text(text: str, max_chars: int = 3800) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return [""]

    chunks: list[str] = []
    start = 0
    text_length = len(normalized)

    while start < text_length:
        end = min(start + max_chars, text_length)
        if end < text_length:
            split_at = normalized.rfind(" ", start, end)
            if split_at > start:
                end = split_at
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end + 1

    return chunks or [normalized[:max_chars]]


def generate_podcast_audio(transcript: str, audio_dir: str) -> str:
    filename_stem = str(uuid.uuid4())
    filepath = synthesize_audio(transcript, audio_dir, filename_stem)
    return os.path.basename(filepath)
