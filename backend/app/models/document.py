"""
SQLAlchemy ORM model for a processed document.
We store the full structured JSON response (extracted_data + validation +
metadata) as a JSON column so the API can return exactly what was computed,
while also keeping a few columns indexed/queryable for the dashboard list view.
"""
import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON
from app.core.database import Base


class ProcessedDocument(Base):
    __tablename__ = "processed_documents"

    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String, index=True, nullable=False)
    document_type = Column(String, nullable=False)
    processing_status = Column(String, nullable=False)  # PASS / FAILED
    overall_confidence = Column(String, nullable=True)  # stored as string; optional
    result_json = Column(JSON, nullable=False)  # the full structured response
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
