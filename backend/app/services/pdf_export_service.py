from __future__ import annotations

import os
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def generate_pdf(title: str, content: str, output_dir: str, filename_stem: str) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    pdf_path = os.path.join(output_dir, f"{filename_stem}.pdf")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    margin_x = 0.8 * inch
    margin_top = height - 0.9 * inch
    line_height = 15

    y = margin_top
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_x, y, _safe(title, 90))
    y -= 26

    c.setFont("Helvetica", 11)
    lines = _prepare_lines(content)
    for line in lines:
        if y <= 0.9 * inch:
            c.showPage()
            y = margin_top
            c.setFont("Helvetica", 11)

        if _is_heading(line):
            c.setFont("Helvetica-Bold", 12)
            c.drawString(margin_x, y, line)
            c.setFont("Helvetica", 11)
        else:
            c.drawString(margin_x, y, line)
        y -= line_height

    c.save()
    return pdf_path


def _prepare_lines(content: str) -> list[str]:
    normalized = re.sub(r"\r", "\n", content or "")
    chunks = []
    for raw in normalized.splitlines():
        line = raw.strip()
        if not line:
            chunks.append("")
            continue
        wrapped = _wrap_text(line, width=95)
        chunks.extend(wrapped)
    return chunks


def _wrap_text(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _is_heading(line: str) -> bool:
    return bool(re.match(r"^[A-Z][A-Za-z ]{2,40}:?$", line)) and len(line.split()) <= 5


def _safe(text: str, limit: int) -> str:
    return (text or "").strip()[:limit] or "PaperCast Document"
