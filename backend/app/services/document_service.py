"""
Orchestrates the full pipeline (Table 3 of the spec):
Validate -> OCR/text extraction -> LLM field/table extraction ->
Financial validation -> Store result -> Return structured JSON.

This is the only place that calls multiple services together; each individual
service stays independently testable and single-purpose.
"""
import datetime
import time

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.repositories import document_repository
from app.services import (
    document_validation_service as validation_service,
    ocr_service,
    extraction_service,
    financial_validation_service,
)

logger = get_logger(__name__)


def process_document(db: Session, filename: str, document_type: str,
                      content_type: str, content: bytes) -> dict:
    start = time.time()

    # --- Stage 1: file validation ---
    try:
        file_validation = validation_service.validate_file(filename, content_type, content)
    except validation_service.ValidationError as exc:
        logger.warning("Validation failed for '%s': %s", filename, exc.message)
        result = {
            "document_name": filename,
            "document_type": document_type,
            "processing_status": "FAILED",
            "overall_confidence": None,
            "file_validation": {
                "file_type": content_type,
                "is_supported": exc.code != "UNSUPPORTED_FILE_TYPE",
                "is_readable": exc.code not in ("CORRUPTED_FILE", "EMPTY_FILE"),
                "page_count": None,
                "status": "FAILED",
                "reason": exc.message,
            },
            "extracted_data": {},
            "validation": {"checks": [], "overall_status": "NOT_APPLICABLE", "issues": []},
            "processing_metadata": {
                "ocr_used": False,
                "processed_at": datetime.datetime.utcnow().isoformat() + "Z",
                "processing_time_ms": int((time.time() - start) * 1000),
            },
            "error_code": exc.code,
        }
        document_repository.save_result(db, filename, document_type, "FAILED", None, result)
        return result

    # --- Stage 2: text extraction / OCR ---
    ocr_used = False
    try:
        full_text, ocr_used, _ = ocr_service.extract_text(content_type, content)
    except Exception as exc:
        logger.error("OCR/text extraction failed for '%s': %s", filename, exc)
        return _fail_result(db, filename, document_type, content_type, file_validation,
                             "OCR_FAILED", f"Text extraction failed: {exc}", start)

    # --- Stage 3: AI-based field & table extraction ---
    try:
        extracted = extraction_service.extract_fields_and_tables(document_type, full_text)
    except extraction_service.ExtractionError as exc:
        logger.error("LLM extraction failed for '%s': %s", filename, exc)
        return _fail_result(db, filename, document_type, content_type, file_validation,
                             "EXTRACTION_FAILED", str(exc), start)

    fields = extracted.get("fields", {})
    tables = extracted.get("tables", {})

    # --- Stage 4: financial validation ---
    validation_result = financial_validation_service.run_validation(document_type, fields, tables)

    # Design decision (documented in README "Known limitations"): processing_status
    # reflects whether the PIPELINE completed successfully (file validated, text
    # extracted, LLM extraction succeeded). A financial validation FAIL is a real,
    # important finding, but it is reported inside `validation.overall_status`,
    # not conflated with pipeline failure — otherwise a single miscalculated
    # invoice would look identical to a corrupted/unreadable file in the dashboard.
    processing_status = "PASS"

    result = {
        "document_name": filename,
        "document_type": document_type,
        "processing_status": processing_status,
        "overall_confidence": None,
        "file_validation": file_validation.model_dump(),
        "extracted_data": {**fields, **{f"table:{k}": v for k, v in tables.items()}},
        "validation": validation_result,
        "processing_metadata": {
            "ocr_used": ocr_used,
            "processed_at": datetime.datetime.utcnow().isoformat() + "Z",
            "processing_time_ms": int((time.time() - start) * 1000),
        },
    }
    document_repository.save_result(db, filename, document_type, processing_status, None, result)
    return result


def _fail_result(db, filename, document_type, content_type, file_validation, code, message, start):
    result = {
        "document_name": filename,
        "document_type": document_type,
        "processing_status": "FAILED",
        "overall_confidence": None,
        "file_validation": file_validation.model_dump(),
        "extracted_data": {},
        "validation": {"checks": [], "overall_status": "NOT_APPLICABLE", "issues": []},
        "processing_metadata": {
            "ocr_used": False,
            "processed_at": datetime.datetime.utcnow().isoformat() + "Z",
            "processing_time_ms": int((time.time() - start) * 1000),
        },
        "error_code": code,
        "error_message": message,
    }
    document_repository.save_result(db, filename, document_type, "FAILED", None, result)
    return result
