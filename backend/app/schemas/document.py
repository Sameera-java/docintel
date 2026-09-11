"""
Pydantic schemas: request/response contracts for the API.
Keeping these separate from the DB model (app/models) is intentional —
the API shape and the storage shape are allowed to evolve independently.
"""
from enum import Enum
from typing import Optional, List, Any, Dict
from pydantic import BaseModel


class DocumentType(str, Enum):
    invoice = "invoice"
    balance_sheet = "balance_sheet"
    profit_and_loss = "profit_and_loss"
    cash_flow_statement = "cash_flow_statement"


class ProcessingStatus(str, Enum):
    PASS = "PASS"
    FAILED = "FAILED"


class FileValidationResult(BaseModel):
    file_type: str
    is_supported: bool
    is_readable: bool
    page_count: Optional[int] = None
    status: str  # PASS / FAILED
    reason: Optional[str] = None  # populated only on FAILED


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ProcessingMetadata(BaseModel):
    ocr_used: bool
    processed_at: str
    processing_time_ms: int


class DocumentListItem(BaseModel):
    document_name: str
    document_type: str
    processing_status: str
    processed_at: str
    overall_confidence: Optional[float] = None

    class Config:
        from_attributes = True


class DocumentProcessResponse(BaseModel):
    """The mandatory structured JSON response shape (section 5.2 of the spec)."""
    document_name: str
    document_type: str
    processing_status: str
    overall_confidence: Optional[float] = None
    file_validation: FileValidationResult
    extracted_data: Dict[str, Any] = {}
    validation: Dict[str, Any] = {}
    processing_metadata: Optional[ProcessingMetadata] = None
