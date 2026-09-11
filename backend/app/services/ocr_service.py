"""
Stage 2: Text extraction / OCR (section 3 & 9 of the spec).

Strategy:
- Native PDFs: extract embedded text directly via PyMuPDF (fast, no OCR needed).
- Scanned PDFs (little/no embedded text) or images (JPG/PNG): rasterize and run
  Tesseract OCR (pytesseract) — fully free/local, no API key or rate limit.

Returns per-page text plus a flag indicating whether OCR was actually used,
which is surfaced later in processing_metadata.ocr_used.
"""
import io
import os
from typing import List, Tuple

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Point pytesseract at the tesseract binary explicitly if configured, or if
# the default Windows install location exists — avoids relying on PATH,
# which the Windows installer doesn't always set up correctly.
_DEFAULT_WINDOWS_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
elif os.name == "nt" and os.path.exists(_DEFAULT_WINDOWS_PATH):
    pytesseract.pytesseract.tesseract_cmd = _DEFAULT_WINDOWS_PATH

# Below this many characters of native text, we treat a PDF page as "scanned"
# and fall back to OCR rather than trusting a near-empty extraction.
MIN_NATIVE_TEXT_CHARS = 20


def extract_text(content_type: str, content: bytes) -> Tuple[str, bool, List[str]]:
    """
    Returns (full_text, ocr_used, per_page_text).
    full_text is all pages concatenated with page markers, used as LLM input.
    per_page_text lets the extraction step reference page numbers.
    """
    if content_type == "application/pdf":
        return _extract_from_pdf(content)
    else:
        return _extract_from_image(content)


def _extract_from_pdf(content: bytes) -> Tuple[str, bool, List[str]]:
    per_page_text: List[str] = []
    ocr_used = False

    with fitz.open(stream=content, filetype="pdf") as pdf:
        for page_index in range(pdf.page_count):
            page = pdf[page_index]
            native_text = page.get_text().strip()

            if len(native_text) >= MIN_NATIVE_TEXT_CHARS:
                per_page_text.append(native_text)
                continue

            # Likely a scanned page — rasterize and OCR it
            logger.info("Page %d has little/no native text; falling back to OCR", page_index + 1)
            ocr_used = True
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_text = pytesseract.image_to_string(img)
            per_page_text.append(ocr_text.strip())

    full_text = "\n\n".join(
        f"--- PAGE {i + 1} ---\n{text}" for i, text in enumerate(per_page_text)
    )
    return full_text, ocr_used, per_page_text


def _extract_from_image(content: bytes) -> Tuple[str, bool, List[str]]:
    img = Image.open(io.BytesIO(content))
    text = pytesseract.image_to_string(img).strip()
    full_text = f"--- PAGE 1 ---\n{text}"
    return full_text, True, [text]