import io

import jsonschema
import psycopg
import pypdfium2
import pytest
from fastapi.testclient import TestClient

from mycareerai.module.ocr import OcrError, validate_record
from mycareerai.api import documents
from mycareerai.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def saved(monkeypatch):
    rows = []
    monkeypatch.setattr(documents, "save_table", rows.append)
    return rows


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


def fail_with(monkeypatch, error: Exception, name: str = "build_record"):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(documents, name, fail)


def test_saves_and_returns_a_valid_row(monkeypatch, saved, blank_pdf):
    monkeypatch.setattr("mycareerai.module.ocr.extract._ocr_page", lambda page: "Scanned text")

    response = post("Scan.PDF", blank_pdf)

    assert response.status_code == 200
    row = response.json()
    assert saved == [row]
    assert row["text"] == "Scanned text"
    assert row["source"] == "Scan.PDF"
    assert row["license"] == "user-provided"
    validate_record(row)


def test_a_database_error_is_reported(monkeypatch, blank_pdf):
    monkeypatch.setattr("mycareerai.module.ocr.extract._ocr_page", lambda page: "Scanned text")
    fail_with(monkeypatch, psycopg.OperationalError("down"), "save_table")

    response = post("scan.pdf", blank_pdf)

    assert response.status_code == 503
    assert response.json()["detail"] == "The resume could not be saved. Try again in a moment."


def test_rejects_other_file_types(saved):
    response = post("cv.docx", b"not a pdf")

    assert response.status_code == 415
    assert response.json()["detail"] == "Only PDF files can be read."
    assert not saved


def test_rejects_large_files(monkeypatch):
    monkeypatch.setattr(documents, "MAX_UPLOAD_BYTES", 4)

    assert post("cv.pdf", b"12345").status_code == 413


def test_damaged_pdf_gets_a_readable_error():
    response = post("my cv.pdf", b"not a pdf")

    assert response.status_code == 422
    assert response.json()["detail"] == "document.pdf could not be opened as a PDF."


def test_reports_ocr_errors(monkeypatch):
    fail_with(monkeypatch, OcrError("No text was found in document.pdf."))

    assert post("cv.pdf", b"x").json()["detail"] == "No text was found in document.pdf."


def test_invalid_row_gets_a_readable_error(monkeypatch):
    fail_with(monkeypatch, jsonschema.ValidationError("bad row"))

    response = post("cv.pdf", b"x")

    assert response.status_code == 422
    assert response.json()["detail"] == "The resume could not be parsed."
