"""
Stage 2: Text extraction / OCR (section 3 & 9 of the spec).

Strategy:
- Native PDFs: extract embedded text directly via PyMuPDF (fast, no OCR needed).
- Scanned PDFs (little/no embedded text) or images (JPG/PNG): send the page
  image directly to Gemini's vision capability and ask it to transcribe the
  visible text. This reuses the same Gemini API key already used for field
  extraction (Stage 3), so no separate OCR service/API key is needed.

Why not a dedicated local OCR engine (e.g. Tesseract): this service is meant
to run identically on a developer's laptop AND on a hosting platform (e.g.
Render's free tier), and many hosting platforms' standard runtimes do not
allow installing system-level binaries. Using the LLM we already depend on
for OCR too keeps local and deployed behavior identical with one less
moving part.

Returns per-page text plus a flag indicating whether OCR was actually used,
which is surfaced later in processing_metadata.ocr_used.
"""
from typing import List, Tuple

import fitz  # PyMuPDF
import google.generativeai as genai

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Below this many characters of native text, we treat a PDF page as "scanned"
# and fall back to OCR rather than trusting a near-empty extraction.
MIN_NATIVE_TEXT_CHARS = 20

_configured = False


class OcrError(Exception):
    pass


def _ensure_configured():
    global _configured
    if not _configured:
        if not settings.GEMINI_API_KEY:
            raise OcrError("GEMINI_API_KEY is not configured on the server.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _configured = True


def _gemini_transcribe_image(image_bytes: bytes, mime_type: str) -> str:
    """Sends one image to Gemini and asks it to transcribe all visible text."""
    _ensure_configured()
    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content([
            {"mime_type": mime_type, "data": image_bytes},
            "Transcribe ALL visible text in this image exactly as it appears, "
            "preserving line breaks and the layout of tables/columns as plain "
            "text. Do not summarize, translate, or explain anything — output "
            "ONLY the raw transcribed text, nothing else.",
        ])
        return (response.text or "").strip()
    except Exception as exc:
        logger.error("Gemini OCR transcription failed: %s", exc)
        raise OcrError(f"OCR (via Gemini) failed: {exc}")


def extract_text(content_type: str, content: bytes) -> Tuple[str, bool, List[str]]:
    """
    Returns (full_text, ocr_used, per_page_text).
    full_text is all pages concatenated with page markers, used as LLM input.
    per_page_text lets the extraction step reference page numbers.
    """
    if content_type == "application/pdf":
        return _extract_from_pdf(content)
    else:
        return _extract_from_image(content, content_type)


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

            # Likely a scanned page — rasterize and transcribe it via Gemini
            logger.info("Page %d has little/no native text; falling back to OCR", page_index + 1)
            ocr_used = True
            pix = page.get_pixmap(dpi=300)
            png_bytes = pix.tobytes("png")
            ocr_text = _gemini_transcribe_image(png_bytes, "image/png")
            per_page_text.append(ocr_text)

    full_text = "\n\n".join(
        f"--- PAGE {i + 1} ---\n{text}" for i, text in enumerate(per_page_text)
    )
    return full_text, ocr_used, per_page_text


def _extract_from_image(content: bytes, content_type: str) -> Tuple[str, bool, List[str]]:
    text = _gemini_transcribe_image(content, content_type)
    full_text = f"--- PAGE 1 ---\n{text}"
    return full_text, True, [text]