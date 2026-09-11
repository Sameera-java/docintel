import io
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_docintel.db")

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db

init_db()  # TestClient doesn't reliably fire startup/lifespan events
client = TestClient(app)


def test_health_check():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_unsupported_file_type_returns_error():
    file_bytes = io.BytesIO(b"hello world")
    res = client.post(
        "/api/v1/documents/process",
        files={"file": ("notes.txt", file_bytes, "text/plain")},
        data={"document_type": "invoice"},
    )
    # Our service catches this as a graceful FAILED result, not an HTTP error
    assert res.status_code == 200
    body = res.json()
    assert body["processing_status"] == "FAILED"
    assert body["file_validation"]["status"] == "FAILED"


def test_list_documents_endpoint_returns_list():
    res = client.get("/api/v1/documents")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_get_nonexistent_document_returns_404():
    res = client.get("/api/v1/documents/does-not-exist.pdf")
    assert res.status_code == 404
