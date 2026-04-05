from __future__ import annotations

import hashlib
import re
from typing import Any

from app.store import LEARNING_STORE, PAPER_STORE


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", (text or "").lower()))


def _concept_hash(content_id: str, label: str) -> str:
    digest = hashlib.sha1(f"{content_id}:{label.lower()}".encode("utf-8")).hexdigest()
    return digest[:16]


def _registry_bucket() -> dict[str, dict[str, Any]]:
    return LEARNING_STORE.setdefault("_concept_registry", {})


def _content_candidates(content_id: str) -> list[dict[str, str]]:
    paper = PAPER_STORE.get(content_id, {})
    candidates: list[dict[str, str]] = []

    for topic in paper.get("knowledge_graph", {}).get("topics", []):
        if not isinstance(topic, dict):
            continue
        concept_items = topic.get("concept_items", [])
        if isinstance(concept_items, list):
            for item in concept_items:
                if not isinstance(item, dict):
                    continue
                concept_id = str(item.get("concept_id", "")).strip()
                label = str(item.get("label", "")).strip()
                if concept_id and label:
                    candidates.append({"concept_id": concept_id, "label": label})
        for raw in topic.get("concepts", []):
            label = str(raw).strip()
            if label:
                candidates.append({"concept_id": _concept_hash(content_id, label), "label": label})
        topic_name = str(topic.get("name", "")).strip()
        if topic_name:
            candidates.append({"concept_id": _concept_hash(content_id, topic_name), "label": topic_name})
    return candidates


def normalize_concept(
    user_id: str,
    content_id: str,
    raw_text: str,
    aliases: list[str] | None = None,
) -> dict[str, str]:
    source = " ".join([raw_text, *(aliases or [])]).strip()
    label = raw_text.strip() or "General Revision"
    source_tokens = _tokenize(source)

    best_match: dict[str, str] | None = None
    best_score = 0.0
    for candidate in _content_candidates(content_id):
        candidate_tokens = _tokenize(candidate["label"])
        if not candidate_tokens or not source_tokens:
            continue
        score = len(source_tokens.intersection(candidate_tokens)) / len(source_tokens.union(candidate_tokens))
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_match and best_score >= 0.25:
        concept_id = best_match["concept_id"]
        label = best_match["label"]
    else:
        concept_id = _concept_hash(content_id, label)

    registry = _registry_bucket()
    registry[concept_id] = {
        "concept_id": concept_id,
        "label": label,
        "content_id": content_id,
        "user_id": user_id,
        "aliases": sorted(
            {
                label,
                *(entry.strip() for entry in aliases or [] if entry and entry.strip()),
                *(entry.strip() for entry in [raw_text] if entry and entry.strip()),
            }
        ),
    }
    return {"concept_id": concept_id, "label": label}


def get_concept_label(concept_id: str, fallback: str = "") -> str:
    registry = _registry_bucket()
    record = registry.get(concept_id, {})
    label = str(record.get("label", "")).strip()
    return label or fallback or concept_id
