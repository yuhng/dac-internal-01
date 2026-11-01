import io
import json

import jsonschema
import pypdfium2
import pytest
from fastapi.testclient import TestClient

from mycareerai.ai.ocr import OcrError, validate_record
from mycareerai.api import documents
from mycareerai.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def row_path(tmp_path, monkeypatch):
    path = tmp_path / "processed" / "row.json"
    monkeypatch.setattr(documents, "ROW_PATH", path)
    return path


@pytest.fixture
def blank_pdf():
    document = pypdfium2.PdfDocument.new()
    document.new_page(612, 792)
    buffer = io.BytesIO()
    document.save(buffer)
    document.close()
    return buffer.getvalue()


def post(name: str, content: bytes):
    return client.post("/api/documents/extract", files={"file": (name, content, "application/pdf")})


def fail_with(monkeypatch, error: Exception):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(documents, "build_record", fail)


def test_writes_a_valid_row_and_returns_it(monkeypatch, row_path, blank_pdf):
    monkeypatch.setattr("mycareerai.ai.ocr.extract._ocr_page", lambda page: "Scanned text")

    response = post("Scan.PDF", blank_pdf)

    assert response.status_code == 200
    row = json.loads(row_path.read_text())
    assert response.json() == row
    assert row["text"] == "Scanned text"
    assert row["source"] == "Scan.PDF"
    assert row["license"] == "user-provided"
    validate_record(row)


def test_a_new_upload_replaces_the_row(monkeypatch, row_path, blank_pdf):
    row_path.parent.mkdir()
    row_path.write_text("old row")
    monkeypatch.setattr("mycareerai.ai.ocr.extract._ocr_page", lambda page: "Scanned text")

    post("scan.pdf", blank_pdf)

    assert json.loads(row_path.read_text())["text"] == "Scanned text"


def test_rejects_other_file_types(row_path):
    response = post("cv.docx", b"not a pdf")

    assert response.status_code == 415
    assert response.json()["detail"] == "Only PDF files can be read."
    assert not row_path.exists()


def test_rejects_large_files(monkeypatch, row_path):
    monkeypatch.setattr(documents, "MAX_UPLOAD_BYTES", 4)

    assert post("cv.pdf", b"12345").status_code == 413
    assert not row_path.exists()


def test_damaged_pdf_gets_a_readable_error(row_path):
    response = post("my cv.pdf", b"not a pdf")

    assert response.status_code == 422
    assert response.json()["detail"] == "document.pdf could not be opened as a PDF."
    assert not row_path.exists()


def test_reports_ocr_errors(monkeypatch, row_path):
    fail_with(monkeypatch, OcrError("No text was found in document.pdf."))

    assert post("cv.pdf", b"x").json()["detail"] == "No text was found in document.pdf."
    assert not row_path.exists()


def test_invalid_row_is_not_written(monkeypatch, row_path):
    fail_with(monkeypatch, jsonschema.ValidationError("bad row"))

    response = post("cv.pdf", b"x")

    assert response.status_code == 422
    assert response.json()["detail"] == "The resume could not be parsed."
    assert not row_path.exists()
