"""
Stage 3: AI-based field & table extraction (section 4.2/4.3 of the spec).
Sends OCR/text-extracted content to Gemini and gets back structured JSON:
fields (with value + source_text + page_number) and tables.
"""
import json
import re
from typing import Any, Dict

import google.generativeai as genai

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.extraction import build_extraction_prompt

logger = get_logger(__name__)
settings = get_settings()

_configured = False


class ExtractionError(Exception):
    pass


def _ensure_configured():
    global _configured
    if not _configured:
        if not settings.GEMINI_API_KEY:
            raise ExtractionError("GEMINI_API_KEY is not configured on the server.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _configured = True


def _strip_code_fences(text: str) -> str:
    """Gemini sometimes wraps JSON in ```json ... ``` even when asked not to."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_fields_and_tables(document_type: str, source_text: str) -> Dict[str, Any]:
    """
    Calls the LLM once with the full document text and returns a dict:
    {"fields": {...}, "tables": {...}}
    Raises ExtractionError on API failure or unparsable output — callers must
    handle this and fail the request gracefully rather than crash.
    """
    _ensure_configured()
    prompt = build_extraction_prompt(document_type, source_text)

    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        raw = response.text
    except Exception as exc:
        logger.error("Gemini extraction call failed: %s", exc)
        raise ExtractionError(f"LLM extraction failed: {exc}")

    cleaned = _strip_code_fences(raw)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Could not parse LLM JSON output: %s | raw=%s", exc, raw[:500])
        raise ExtractionError("LLM returned output that could not be parsed as JSON.")

    parsed.setdefault("fields", {})
    parsed.setdefault("tables", {})
    return parsed
