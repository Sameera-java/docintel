"""
Stage 1: Document validation (section 4.1 of the spec).
Runs BEFORE OCR/extraction. Checks file type, integrity, and page count.
This is deliberately the input-control layer only — it does NOT try to
guess the document type (that's selected by the user in the frontend).
"""
import io

import fitz  # PyMuPDF
from PIL import Image

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.document import FileValidationResult

logger = get_logger(__name__)
settings = get_settings()


class ValidationError(Exception):
    """Raised when a file fails validation; caught by the API layer."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_file(filename: str, content_type: str, content: bytes) -> FileValidationResult:
    """
    Validates an uploaded file end to end.
    Returns a FileValidationResult on success, raises ValidationError on failure
    (the API layer converts that into a graceful error response).
    """
    logger.info("Validating file '%s' (declared content_type=%s, size=%d bytes)",
                filename, content_type, len(content))

    if not content:
        raise ValidationError("EMPTY_FILE", "The uploaded file is empty.")

    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise ValidationError(
            "FILE_TOO_LARGE",
            f"File exceeds the maximum allowed size of {settings.MAX_FILE_SIZE_MB} MB.",
        )

    if content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            "UNSUPPORTED_FILE_TYPE",
            "Only PDF / JPG / PNG documents are supported.",
        )

    page_count = 1
    is_readable = True

    if content_type == "application/pdf":
        try:
            with fitz.open(stream=content, filetype="pdf") as pdf:
                page_count = pdf.page_count
                if page_count == 0:
                    raise ValidationError("CORRUPTED_FILE", "The PDF has no pages.")
                # touch the first page to confirm the file is actually readable
                _ = pdf[0].get_text()
        except ValidationError:
            raise
        except Exception as exc:
            logger.warning("Failed to open PDF '%s': %s", filename, exc)
            raise ValidationError("CORRUPTED_FILE", "The PDF file is corrupted or unreadable.")
    else:
        # image types
        try:
            img = Image.open(io.BytesIO(content))
            img.verify()
            page_count = 1
        except Exception as exc:
            logger.warning("Failed to open image '%s': %s", filename, exc)
            raise ValidationError("CORRUPTED_FILE", "The image file is corrupted or unreadable.")

    if page_count > settings.MAX_PAGES:
        raise ValidationError(
            "PAGE_LIMIT_EXCEEDED",
            f"Document has {page_count} pages; only up to {settings.MAX_PAGES} pages are supported.",
        )

    logger.info("File '%s' passed validation (pages=%d)", filename, page_count)
    return FileValidationResult(
        file_type=content_type,
        is_supported=True,
        is_readable=is_readable,
        page_count=page_count,
        status="PASS",
    )
