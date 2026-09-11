"""
Repository layer: the ONLY place that talks to the database directly.
Keeps persistence concerns out of services/API routes (separation of concerns
required by the spec).
"""
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.document import ProcessedDocument


def save_result(db: Session, document_name: str, document_type: str,
                 processing_status: str, overall_confidence, result_json: dict) -> ProcessedDocument:
    record = ProcessedDocument(
        document_name=document_name,
        document_type=document_type,
        processing_status=processing_status,
        overall_confidence=str(overall_confidence) if overall_confidence is not None else None,
        result_json=result_json,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_latest_by_name(db: Session, document_name: str) -> Optional[ProcessedDocument]:
    return (
        db.query(ProcessedDocument)
        .filter(ProcessedDocument.document_name == document_name)
        .order_by(desc(ProcessedDocument.created_at))
        .first()
    )


def list_all(db: Session) -> List[ProcessedDocument]:
    return (
        db.query(ProcessedDocument)
        .order_by(desc(ProcessedDocument.created_at))
        .all()
    )
