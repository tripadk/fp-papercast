from __future__ import annotations

import logging
from app.services.llm_utils import groq_chat
from app.store import PAPER_STORE

logger = logging.getLogger(__name__)

MOCK_PAPER_CONTENT = """
Sample Research Paper: Machine Learning for Medical Diagnosis.

Abstract: This paper proposes a novel deep learning model for early disease detection using chest X-rays. 
The model achieves 95% accuracy on benchmark datasets, outperforming traditional methods by 12%. 
Key contributions: lightweight architecture, real-time inference, and robust handling of noisy data.
"""

SYSTEM_PROMPT_CHAT = """
You are a research assistant that answers questions based ONLY on the provided research paper content.

Rules:
1. Answer ONLY using information from the paper text below
2. If the paper does not contain the answer, clearly say: "The paper does not provide enough information about this."
3. Keep answers concise (2-4 paragraphs max)
4. Use simple language suitable for students
5. Use bullet points for lists/comparisons
6. Be precise - no speculation or external knowledge
"""


def get_paper_content(paper_id: str) -> str:
    """Get paper text, mock if missing."""
    paper = PAPER_STORE.get(paper_id, {})
    content = paper.get("text", "").strip()
    if not content:
        logger.warning(f"No content for paper_id={paper_id}, using mock")
        content = MOCK_PAPER_CONTENT
    return content[:12000]  # Truncate for tokens


def chat(paper_id: str, question: str) -> str:
    """
    Chat service: paper_id + question -> concise paper-based answer
    """
    try:
        paper_content = get_paper_content(paper_id)
        prompt = f"Paper content:\\n{paper_content}\\n\\nQuestion: {question}"
        answer = groq_chat(prompt, SYSTEM_PROMPT_CHAT, max_tokens=800)
        logger.info(f"Chat generated for paper_id={paper_id}, question_len={len(question)}")
        return answer.strip()
    except Exception as e:
        logger.error(f"Chat service error paper_id={paper_id}: {str(e)}")
        return "The chat service is temporarily unavailable. Please try again."

