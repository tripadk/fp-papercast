from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import settings

_STORE_LOCK = Lock()
_STATE_PATH = Path(settings.app_state_path)

_DEFAULT_STATE: dict[str, Any] = {
    "paper_store": {},
    "paper_history": [],
    "chat_history": {},
    "content_store": {},
    "learning_store": {},
    "knowledge_graph_store": {},
    "confusion_store": {},
}


def _ensure_state_file() -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _STATE_PATH.exists():
        _STATE_PATH.write_text(json.dumps(_DEFAULT_STATE, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_state() -> dict[str, Any]:
    _ensure_state_file()
    try:
        payload = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return dict(_DEFAULT_STATE)
        state = dict(_DEFAULT_STATE)
        for key, default_value in _DEFAULT_STATE.items():
            value = payload.get(key, default_value)
            state[key] = value if isinstance(value, type(default_value)) else default_value
        return state
    except Exception:
        return dict(_DEFAULT_STATE)


def _save_state(state: dict[str, Any]) -> None:
    _ensure_state_file()
    _STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


_STATE = _load_state()

PAPER_STORE: dict[str, dict] = _STATE["paper_store"]
PAPER_HISTORY: list[dict] = _STATE["paper_history"]
CHAT_HISTORY: dict[str, list[dict]] = _STATE["chat_history"]
CONTENT_STORE: dict[str, dict] = _STATE["content_store"]
LEARNING_STORE: dict[str, dict] = _STATE["learning_store"]
KNOWLEDGE_GRAPH_STORE: dict[str, dict] = _STATE["knowledge_graph_store"]
CONFUSION_STORE: dict[str, dict] = _STATE["confusion_store"]


def save_state() -> None:
    with _STORE_LOCK:
        _save_state(
            {
                "paper_store": PAPER_STORE,
                "paper_history": PAPER_HISTORY,
                "chat_history": CHAT_HISTORY,
                "content_store": CONTENT_STORE,
                "learning_store": LEARNING_STORE,
                "knowledge_graph_store": KNOWLEDGE_GRAPH_STORE,
                "confusion_store": CONFUSION_STORE,
            }
        )
