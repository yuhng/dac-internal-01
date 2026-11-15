import base64
from types import SimpleNamespace

import httpx
import psycopg
import pytest
from fastapi.testclient import TestClient
from openai import APIConnectionError

from mycareerai.api import documents
from mycareerai.main import app
from mycareerai.module.ocr_v2.extractor import ExtractedResume
from mycareerai.module.ocr_v2.schema import ResumeDocument

client = TestClient(app)
PDF = b"%PDF-1.7\nfixture"


@pytest.fixture(autouse=True)
def saved(monkeypatch):
    rows = []
    monkeypatch.setattr(documents, "save_document", rows.append)
    return rows


@pytest.fixture(autouse=True)
def extraction(monkeypatch):
    calls = []
    extracted = ExtractedResume.model_validate({
        "text": "SUMMARY\nPython analyst",
        "sections": [{"section_name": "summary", "entries": [], "content": "Python analyst"}],
        "parsing_warnings": ["Verify dates"],
    })

    def parse(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status="completed", output_parsed=extracted)

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: SimpleNamespace(responses=SimpleNamespace(parse=parse)))
    return calls


def post(name="cv.pdf", content=PDF):
    return client.post("/api/documents/extract", files={"file": (name, content, "application/pdf")})


def fail_with(monkeypatch, error, name="extract_resume"):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(documents, name, fail)


def test_upload_runs_v2_and_saves_full_contract(saved, extraction):
    response = post("Scan.PDF")
    assert response.status_code == 200
    row = response.json()
    ResumeDocument.model_validate(row)
    assert saved == [row]
    assert row["schema_version"] == "2"
    assert row["text"] == "SUMMARY\nPython analyst"
    assert row["metadata"] == {"collection_method": "gpt4o_pdf", "review_status": "needs_review"}
    assert row["parsing_warnings"] == ["Verify dates"]
    assert row["sections"][0]["section_id"] == row["document_id"] + ":summary"
    assert "id" not in row
    assert extraction[0]["store"] is False
    uploaded = extraction[0]["input"][1]["content"][0]["file_data"]
    assert base64.b64decode(uploaded.split(",", 1)[1]) == PDF


def test_database_failure(monkeypatch):
    fail_with(monkeypatch, psycopg.OperationalError("down"), "save_document")
    assert post().status_code == 503


@pytest.mark.parametrize("content", [b"", b"not a pdf"])
def test_invalid_pdf_does_not_call_model(content, saved, extraction):
    assert post(content=content).status_code == 422
    assert not saved and not extraction


def test_rejects_other_file_types(saved, extraction):
    assert post("cv.docx").status_code == 415
    assert not saved and not extraction


def test_rejects_large_files(monkeypatch, saved, extraction):
    monkeypatch.setattr(documents, "MAX_UPLOAD_BYTES", 4)
    assert post().status_code == 413
    assert not saved and not extraction


def test_invalid_extraction_is_not_saved(monkeypatch, saved):
    fail_with(monkeypatch, ValueError("provider details"))
    response = post()
    assert response.status_code == 422
    assert "provider details" not in response.text
    assert not saved


def test_missing_key_is_service_error(monkeypatch, saved):
    monkeypatch.setattr("mycareerai.core.llm.load_dotenv", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY")
    assert post().status_code == 503
    assert not saved


def test_provider_error_is_service_error(monkeypatch, saved):
    fail_with(monkeypatch, APIConnectionError(request=httpx.Request("POST", "https://example.com")))
    assert post().status_code == 503
    assert not saved
