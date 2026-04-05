from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.services.concept_service import normalize_concept
from app.store import KNOWLEDGE_GRAPH_STORE, save_state

RELATION_PATTERNS: dict[str, str] = {
    "requires": r"\brequires\b",
    "depends_on": r"\bdepends on\b",
    "related_to": r"\brelated to\b",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "with",
}


def generate_knowledge_graph(raw_text: str, content_id: str = "", user_id: str = "system") -> dict[str, Any]:
    normalized = _normalize_text(raw_text)
    if not normalized:
        return {"topics": []}

    sections = _split_into_sections(normalized)
    if not sections:
        sections = [("Core Content", normalized)]

    topics: list[dict[str, Any]] = []
    for name, section_text in sections[:8]:
        concepts = _extract_key_concepts(section_text, limit=10)
        subtopics = _extract_subtopics(section_text, limit=8)
        dependencies = _extract_dependencies(section_text)
        concept_items: list[dict[str, Any]] = []
        for concept in concepts:
            normalized_concept = normalize_concept(user_id=user_id, content_id=content_id or "graph", raw_text=concept)
            prereqs = []
            for edge in dependencies:
                source = _normalize_concept_fragment(str(edge.get("source", "")))
                target = _normalize_concept_fragment(str(edge.get("target", "")))
                if source.lower() == concept.lower():
                    prereq = normalize_concept(user_id=user_id, content_id=content_id or "graph", raw_text=target)
                    prereqs.append(prereq["concept_id"])
            concept_items.append(
                {
                    "concept_id": normalized_concept["concept_id"],
                    "label": normalized_concept["label"],
                    "difficulty_level": _difficulty_for_concept(concept, section_text),
                    "prerequisites": sorted(set(prereqs)),
                }
            )

        topics.append(
            {
                "name": name,
                "subtopics": subtopics,
                "concepts": concepts,
                "concept_items": concept_items,
                "dependencies": dependencies,
                "prerequisites": sorted({item for concept in concept_items for item in concept.get("prerequisites", [])}),
                "difficulty_level": _difficulty_for_section(section_text),
            }
        )

    return {"topics": topics}


def store_knowledge_graph(content_id: str, graph: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "content_id": content_id,
        "graph": graph,
        "navigation": build_navigation(graph),
        "learning_path": generate_learning_path(graph),
    }
    KNOWLEDGE_GRAPH_STORE[content_id] = payload
    save_state()
    return payload


def generate_and_store_knowledge_graph(content_id: str, raw_text: str, user_id: str = "system") -> dict[str, Any]:
    graph = generate_knowledge_graph(content_id=content_id, raw_text=raw_text, user_id=user_id)
    return store_knowledge_graph(content_id, graph)


def get_knowledge_graph(content_id: str) -> dict[str, Any] | None:
    record = KNOWLEDGE_GRAPH_STORE.get(content_id)
    return record if isinstance(record, dict) else None


def build_navigation(graph: dict[str, Any]) -> list[dict[str, Any]]:
    topics = graph.get("topics", []) if isinstance(graph, dict) else []
    navigation: list[dict[str, Any]] = []
    for topic in topics:
        if not isinstance(topic, dict):
            continue
        navigation.append(
            {
                "topic": str(topic.get("name", "")).strip(),
                "subtopics": [str(item).strip() for item in topic.get("subtopics", []) if str(item).strip()],
                "concept_count": len([item for item in topic.get("concepts", []) if str(item).strip()]),
                "difficulty_level": str(topic.get("difficulty_level", "medium")),
            }
        )
    return navigation


def generate_learning_path(graph: dict[str, Any]) -> list[dict[str, Any]]:
    topics = graph.get("topics", []) if isinstance(graph, dict) else []
    path: list[dict[str, Any]] = []

    for topic in topics:
        if not isinstance(topic, dict):
            continue

        concept_items = topic.get("concept_items", [])
        concepts = [str(item.get("concept_id", "")).strip() for item in concept_items if isinstance(item, dict)]
        prereq_map = {
            str(item.get("concept_id", "")).strip(): [str(entry).strip() for entry in item.get("prerequisites", []) if str(entry).strip()]
            for item in concept_items
            if isinstance(item, dict) and str(item.get("concept_id", "")).strip()
        }
        ordered = _topological_order(concepts, prereq_map)

        path.append(
            {
                "topic": str(topic.get("name", "")).strip(),
                "sequence": ordered,
                "prerequisites": prereq_map,
            }
        )
    return path


def _normalize_text(raw_text: str) -> str:
    return re.sub(r"[ \t]+", " ", (raw_text or "")).strip()


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    lines = [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]
    if not lines:
        return []

    heading_candidates: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        if _is_heading(line):
            heading_candidates.append((idx, _normalize_heading(line)))

    if not heading_candidates:
        chunk_size = max(1, len(lines) // 4)
        chunks: list[tuple[str, str]] = []
        for i in range(0, len(lines), chunk_size):
            chunk = " ".join(lines[i : i + chunk_size]).strip()
            if chunk:
                chunks.append((f"Topic {len(chunks) + 1}", chunk))
            if len(chunks) >= 6:
                break
        return chunks

    sections: list[tuple[str, str]] = []
    for pos, (line_idx, heading) in enumerate(heading_candidates):
        next_idx = heading_candidates[pos + 1][0] if pos + 1 < len(heading_candidates) else len(lines)
        content = " ".join(lines[line_idx + 1 : next_idx]).strip()
        if content:
            sections.append((heading, content))
    return sections


def _is_heading(line: str) -> bool:
    cleaned = re.sub(r"^\d+(?:\.\d+)*[\.\)]?\s*", "", line).strip()
    if not cleaned:
        return False
    words = cleaned.split()
    if len(words) > 8 or len(cleaned) > 80 or re.search(r"[.!?]$", cleaned):
        return False
    upper_ratio = sum(1 for ch in cleaned if ch.isupper()) / max(1, sum(1 for ch in cleaned if ch.isalpha()))
    title_case = sum(1 for w in words if w[:1].isupper()) >= max(1, len(words) - 1)
    return title_case or upper_ratio > 0.7


def _normalize_heading(line: str) -> str:
    cleaned = re.sub(r"^\d+(?:\.\d+)*[\.\)]?\s*", "", line).strip(" :")
    return re.sub(r"\s+", " ", cleaned).strip()


def _extract_key_concepts(text: str, limit: int = 10) -> list[str]:
    phrases = re.findall(r"\b[A-Z][a-zA-Z0-9\-]+(?:\s+[A-Z][a-zA-Z0-9\-]+){0,3}\b", text)
    acronyms = re.findall(r"\b[A-Z]{2,}\b", text)
    tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9\-]{3,}\b", text.lower())

    freq = Counter(token for token in tokens if token not in STOPWORDS)
    ranked_tokens = [token.title() for token, _ in freq.most_common(limit * 2)]
    merged = [*phrases, *acronyms, *ranked_tokens]

    deduped: list[str] = []
    seen: set[str] = set()
    for item in merged:
        concept = re.sub(r"\s+", " ", str(item)).strip(" -,:;.")
        key = concept.lower()
        if not concept or key in seen or len(concept) < 3:
            continue
        seen.add(key)
        deduped.append(concept)
        if len(deduped) >= limit:
            break
    return deduped


def _extract_subtopics(text: str, limit: int = 8) -> list[str]:
    lines = [line.strip(" -\t") for line in re.split(r"[\r\n]+", text) if line.strip()]
    candidates: list[str] = []
    for line in lines:
        if len(line.split()) <= 10 and len(line) <= 90 and not re.search(r"[.!?]$", line):
            candidates.append(line)

    if not candidates:
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            sentence = sentence.strip()
            if 4 <= len(sentence.split()) <= 9:
                candidates.append(sentence.rstrip(".!?"))

    deduped: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        normalized = re.sub(r"\s+", " ", item).strip(" -,:;.")
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
        if len(deduped) >= limit:
            break
    return deduped


def _extract_dependencies(text: str) -> list[dict[str, str]]:
    dependencies: list[dict[str, str]] = []
    sentences = [entry.strip() for entry in re.split(r"(?<=[.!?])\s+", text) if entry.strip()]

    for sentence in sentences:
        for relation, pattern in RELATION_PATTERNS.items():
            match = re.search(
                rf"(?i)(?P<src>[^.;:,\n]{{3,120}}?)\s+{pattern}\s+(?P<tgt>[^.;:,\n]{{3,120}})",
                sentence,
            )
            if not match:
                continue
            source = _normalize_concept_fragment(match.group("src"))
            target = _normalize_concept_fragment(match.group("tgt"))
            if not source or not target:
                continue
            dependencies.append({"source": source, "target": target, "relation": relation})

    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in dependencies:
        key = (item["source"].lower(), item["target"].lower(), item["relation"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:20]


def _normalize_concept_fragment(fragment: str) -> str:
    words = re.findall(r"[A-Za-z0-9\-]+", fragment)
    if not words:
        return ""
    filtered = [word for word in words if word.lower() not in STOPWORDS]
    if not filtered:
        filtered = words
    compact = " ".join(filtered[-4:])
    return re.sub(r"\s+", " ", compact).strip()


def _difficulty_for_section(text: str) -> str:
    length = len(re.findall(r"\w+", text))
    if length > 900:
        return "hard"
    if length > 450:
        return "medium"
    return "easy"


def _difficulty_for_concept(concept: str, text: str) -> str:
    concept_tokens = len(re.findall(r"\w+", concept))
    density = len(re.findall(re.escape(concept), text, flags=re.IGNORECASE))
    score = concept_tokens + density
    if score >= 6:
        return "hard"
    if score >= 3:
        return "medium"
    return "easy"


def _topological_order(concepts: list[str], prereq_map: dict[str, list[str]]) -> list[str]:
    remaining = set(concepts)
    completed: set[str] = set()
    ordered: list[str] = []

    while remaining:
        available = sorted([concept for concept in remaining if set(prereq_map.get(concept, [])) <= completed])
        if not available:
            ordered.extend(sorted(remaining))
            break
        for concept in available:
            ordered.append(concept)
            completed.add(concept)
            remaining.remove(concept)
    return ordered
