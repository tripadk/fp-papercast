import re
from io import BytesIO
from typing import Any, List

from pypdf import PdfReader

try:
    import fitz  # type: ignore
except Exception:
    fitz = None

try:
    import pdfplumber  # type: ignore
except Exception:
    pdfplumber = None

try:
    import pytesseract  # type: ignore
except Exception:
    pytesseract = None

try:
    from PIL import Image  # type: ignore
except Exception:
    Image = None

MIN_PAGE_TEXT_CHARS = 25
MIN_TOTAL_TEXT_CHARS = 50
OCR_DPI = 200


def _clean_page_text(text: str) -> str:
    if not text:
        return ""

    cleaned = text.replace("\r", "\n")
    cleaned = re.sub(r"(?<=\w)-\n(?=\w)", "", cleaned)
    cleaned = re.sub(r"(?<!\n)\n(?!\n)", " ", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _extract_page_text_fitz(doc: Any, page_index: int) -> str:
    if doc is None:
        return ""
    try:
        return doc.load_page(page_index).get_text("text") or ""
    except Exception:
        return ""


def _extract_page_text_pdfplumber(pdf: Any, page_index: int) -> str:
    if pdf is None:
        return ""
    try:
        return pdf.pages[page_index].extract_text() or ""
    except Exception:
        return ""


def _extract_page_text_pypdf(reader: PdfReader, page_index: int) -> str:
    try:
        return reader.pages[page_index].extract_text() or ""
    except Exception:
        return ""


def _ocr_page_with_fitz(doc: Any, page_index: int) -> str:
    if doc is None or pytesseract is None or Image is None:
        return ""
    try:
        page = doc.load_page(page_index)
        pix = page.get_pixmap(dpi=OCR_DPI, alpha=False)
        image_bytes = pix.tobytes("png")
        image = Image.open(BytesIO(image_bytes))
        return pytesseract.image_to_string(image) or ""
    except Exception:
        return ""


def _ocr_page_with_pdfplumber(pdf: Any, page_index: int) -> str:
    if pdf is None or pytesseract is None:
        return ""
    try:
        page_image = pdf.pages[page_index].to_image(resolution=OCR_DPI).original
        return pytesseract.image_to_string(page_image) or ""
    except Exception:
        return ""


def _safe_page_count(reader: PdfReader, fitz_doc: Any, plumber_pdf: Any) -> int:
    if fitz_doc is not None:
        try:
            return fitz_doc.page_count
        except Exception:
            pass
    if plumber_pdf is not None:
        try:
            return len(plumber_pdf.pages)
        except Exception:
            pass
    return len(reader.pages)


def extract_text_by_page(path: str) -> List[str]:
    reader = PdfReader(path)
    fitz_doc = None
    plumber_pdf = None

    if fitz is not None:
        try:
            fitz_doc = fitz.open(path)
        except Exception:
            fitz_doc = None

    if pdfplumber is not None:
        try:
            plumber_pdf = pdfplumber.open(path)
        except Exception:
            plumber_pdf = None

    pages: List[str] = []
    try:
        page_count = _safe_page_count(reader, fitz_doc, plumber_pdf)
        for page_index in range(page_count):
            direct_text = _extract_page_text_fitz(fitz_doc, page_index)
            if not direct_text:
                direct_text = _extract_page_text_pdfplumber(plumber_pdf, page_index)
            if not direct_text:
                direct_text = _extract_page_text_pypdf(reader, page_index)

            cleaned_direct = _clean_page_text(direct_text)
            if len(cleaned_direct) >= MIN_PAGE_TEXT_CHARS:
                pages.append(cleaned_direct)
                continue

            ocr_text = _ocr_page_with_fitz(fitz_doc, page_index)
            if not ocr_text:
                ocr_text = _ocr_page_with_pdfplumber(plumber_pdf, page_index)
            cleaned_ocr = _clean_page_text(ocr_text)

            if cleaned_direct and cleaned_ocr:
                pages.append(f"{cleaned_direct}\n{cleaned_ocr}".strip())
            elif cleaned_ocr:
                pages.append(cleaned_ocr)
            else:
                pages.append(cleaned_direct)
    finally:
        if fitz_doc is not None:
            fitz_doc.close()
        if plumber_pdf is not None:
            plumber_pdf.close()

    return pages


def extract_text_from_pdf(path: str) -> str:
    page_texts = extract_text_by_page(path)
    combined = "\n\n".join(text for text in page_texts if text).strip()

    if len(combined) < MIN_TOTAL_TEXT_CHARS:
        raise ValueError("Could not extract sufficient readable text from the PDF.")

    return combined
