from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}
DEFAULT_STEPS = 5


@dataclass
class RelatedPaperResult:
    title: str
    authors: str
    summary: str
    link: str
    score: float


def find_related_papers(text: str, max_results: int = DEFAULT_STEPS) -> list[dict[str, str]]:
    title, abstract = extract_title_and_abstract(text)
    query_terms = _query_terms(title, abstract)
    candidates = _fetch_arxiv_candidates(query_terms, search_limit=12)
    if not candidates:
        return []

    ranked = _rank_by_similarity(title, abstract, candidates)
    top_matches = ranked[: max(3, min(max_results, 5))]
    return [
        {
            "title": item.title,
            "authors": item.authors,
            "summary": item.summary,
            "link": item.link,
        }
        for item in top_matches
    ]


def extract_title_and_abstract(text: str) -> tuple[str, str]:
    normalized = re.sub(r"\r", "\n", text or "").strip()
    if not normalized:
        return ("Untitled Paper", "No abstract could be extracted from the uploaded paper.")

    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    title = "Untitled Paper"
    for line in lines[:10]:
        if len(line) >= 20 and not line.lower().startswith(("abstract", "keywords")):
            title = line
            break

    abstract_match = re.search(
        r"(?is)\babstract\b[:\s\-]*(.+?)(?=\n\s*(?:1\.|i\.|introduction|keywords)\b)",
        normalized,
    )
    if abstract_match:
        abstract = _compact(abstract_match.group(1))[:1800]
    else:
        abstract = _compact("\n".join(lines[1:25]))[:1800]

    if not abstract:
        abstract = "No abstract could be extracted from the uploaded paper."
    return (title[:220], abstract)


def _query_terms(title: str, abstract: str) -> str:
    source = f"{title} {abstract}".lower()
    tokens = re.findall(r"[a-z][a-z0-9\-]{3,}", source)
    stopwords = {
        "this",
        "that",
        "with",
        "from",
        "have",
        "into",
        "paper",
        "method",
        "using",
        "study",
        "results",
        "based",
        "their",
        "these",
        "than",
        "such",
        "analysis",
        "approach",
        "proposed",
    }
    ranked = [token for token, _ in Counter(tokens).most_common(20) if token not in stopwords]
    return " ".join(ranked[:8]) or title


def _fetch_arxiv_candidates(query_terms: str, search_limit: int) -> list[dict[str, str]]:
    query = quote_plus(query_terms)
    url = f"{ARXIV_API_URL}?search_query=all:{query}&start=0&max_results={search_limit}"
    request = Request(url=url, headers={"User-Agent": "PaperCast/1.0"})
    try:
        with urlopen(request, timeout=15) as response:
            xml_bytes = response.read()
    except Exception:
        return []

    root = ET.fromstring(xml_bytes)
    entries = []
    for entry in root.findall("atom:entry", namespaces=ATOM_NAMESPACE):
        title = _compact(entry.findtext("atom:title", default="", namespaces=ATOM_NAMESPACE))
        summary = _compact(entry.findtext("atom:summary", default="", namespaces=ATOM_NAMESPACE))
        authors = [
            _compact(author.findtext("atom:name", default="", namespaces=ATOM_NAMESPACE))
            for author in entry.findall("atom:author", namespaces=ATOM_NAMESPACE)
        ]
        link = _compact(entry.findtext("atom:id", default="", namespaces=ATOM_NAMESPACE))
        if title and summary and link:
            entries.append(
                {
                    "title": title,
                    "authors": ", ".join([name for name in authors if name]) or "Unknown",
                    "summary": summary,
                    "link": link,
                }
            )
    return entries


def _rank_by_similarity(title: str, abstract: str, candidates: list[dict[str, str]]) -> list[RelatedPaperResult]:
    source_doc = f"{title}\n{abstract}".strip()
    candidate_docs = [f"{item['title']}\n{item['summary']}".strip() for item in candidates]

    embedding_scores = _embedding_similarity(source_doc, candidate_docs)
    if not embedding_scores:
        embedding_scores = [_token_cosine(source_doc, doc) for doc in candidate_docs]

    scored: list[RelatedPaperResult] = []
    for idx, item in enumerate(candidates):
        scored.append(
            RelatedPaperResult(
                title=item["title"],
                authors=item["authors"],
                summary=item["summary"][:480],
                link=item["link"],
                score=embedding_scores[idx],
            )
        )
    scored.sort(key=lambda entry: entry.score, reverse=True)
    return scored


def _embedding_similarity(source: str, candidates: list[str]) -> list[float]:
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except Exception:
        return []

    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        vectors = model.encode([source, *candidates], normalize_embeddings=True)
    except Exception:
        return []

    source_vector = vectors[0]
    scores = []
    for vector in vectors[1:]:
        score = float(sum(float(a) * float(b) for a, b in zip(source_vector, vector, strict=False)))
        scores.append(score)
    return scores


def _token_cosine(source: str, target: str) -> float:
    source_counts = Counter(_tokenize(source))
    target_counts = Counter(_tokenize(target))
    if not source_counts or not target_counts:
        return 0.0

    common = set(source_counts).intersection(target_counts)
    numerator = sum(source_counts[token] * target_counts[token] for token in common)
    source_norm = math.sqrt(sum(value * value for value in source_counts.values()))
    target_norm = math.sqrt(sum(value * value for value in target_counts.values()))
    if source_norm == 0.0 or target_norm == 0.0:
        return 0.0
    return float(numerator / (source_norm * target_norm))


def _tokenize(text: str) -> Iterable[str]:
    cleaned = re.sub(r"[^a-z0-9\s\-]", " ", (text or "").lower())
    for token in cleaned.split():
        if len(token) > 2:
            yield token


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()
