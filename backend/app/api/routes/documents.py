"""
REST API routes (section 5 / Table 9 of the spec):
POST /api/v1/documents/process
GET  /api/v1/documents/{document_name}
GET  /api/v1/documents
GET  /api/v1/health
"""
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.repositories import document_repository
from app.schemas.document import DocumentType
from app.services import document_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "document-intelligence-api"}


@router.post("/documents/process")
async def process_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    db: Session = Depends(get_db),
):
    try:
        content = await file.read()
    except Exception as exc:
        logger.error("Failed to read uploaded file: %s", exc)
        raise HTTPException(status_code=400, detail={
            "error": {"code": "FILE_READ_ERROR", "message": "Could not read the uploaded file."}
        })

    try:
        result = document_service.process_document(
            db=db,
            filename=file.filename,
            document_type=document_type.value,
            content_type=file.content_type,
            content=content,
        )
    except Exception as exc:
        # Catch-all: never leak stack traces/secrets to the client.
        logger.exception("Unexpected error while processing '%s'", file.filename)
        raise HTTPException(status_code=500, detail={
            "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred while processing the document."}
        })

    return result


@router.get("/documents/{document_name}")
def get_document_by_name(document_name: str, db: Session = Depends(get_db)):
    record = document_repository.get_latest_by_name(db, document_name)
    if record is None:
        raise HTTPException(status_code=404, detail={
            "error": {"code": "NOT_FOUND", "message": f"No processed result found for '{document_name}'."}
        })
    return record.result_json


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    records = document_repository.list_all(db)
    return [
        {
            "document_name": r.document_name,
            "document_type": r.document_type,
            "processing_status": r.processing_status,
            "processed_at": r.created_at.isoformat() + "Z",
            "overall_confidence": r.overall_confidence,
        }
        for r in records
    ]
