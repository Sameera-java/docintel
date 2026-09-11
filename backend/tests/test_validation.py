import io
import fitz
import pytest

from app.services.document_validation_service import validate_file, ValidationError


def _make_pdf_bytes(num_pages=1):
    doc = fitz.open()
    for _ in range(num_pages):
        page = doc.new_page()
        page.insert_text((72, 72), "Sample text")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_empty_file_rejected():
    with pytest.raises(ValidationError) as exc:
        validate_file("empty.pdf", "application/pdf", b"")
    assert exc.value.code == "EMPTY_FILE"


def test_unsupported_type_rejected():
    with pytest.raises(ValidationError) as exc:
        validate_file("doc.txt", "text/plain", b"hello")
    assert exc.value.code == "UNSUPPORTED_FILE_TYPE"


def test_valid_pdf_passes():
    content = _make_pdf_bytes(num_pages=1)
    result = validate_file("sample.pdf", "application/pdf", content)
    assert result.status == "PASS"
    assert result.page_count == 1


def test_page_limit_exceeded():
    content = _make_pdf_bytes(num_pages=4)
    with pytest.raises(ValidationError) as exc:
        validate_file("big.pdf", "application/pdf", content)
    assert exc.value.code == "PAGE_LIMIT_EXCEEDED"


def test_corrupted_pdf_rejected():
    with pytest.raises(ValidationError) as exc:
        validate_file("corrupt.pdf", "application/pdf", b"not a real pdf")
    assert exc.value.code == "CORRUPTED_FILE"
