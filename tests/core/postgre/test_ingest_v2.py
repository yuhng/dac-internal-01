from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from backend.app.core.postgre import ingest


def record():
    return {
        "schema_version": "2", "document_id": "CV_001", "document_version": 1,
        "document_type": "resume", "text": "Python",
        "metadata": {"collection_method": "claude_pdf", "review_status": "pending"},
        "sections": [{"section_id": "CV_001:technical_skills", "section_name": "technical_skills",
                      "content": "Python"}],
        "parsing_warnings": [],
    }


@pytest.fixture
def connection(monkeypatch):
    connection = MagicMock()
    connect = MagicMock()
    connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr(ingest.psycopg, "connect", connect)
    return connection


def test_v2_document_is_stored_as_one_json_row(connection):
    ingest.save_document(record())
    assert connection.execute.call_count == 2
    sql, params = connection.execute.call_args.args
    assert sql == ingest.UPSERT_DOCUMENT
    assert params[0] == "CV_001"
    assert params[1].obj == record()


def test_invalid_document_is_rejected_before_connecting(connection):
    bad = record()
    bad["sections"][0]["section_name"] = "skills"
    with pytest.raises(ValidationError):
        ingest.save_document(bad)
    connection.execute.assert_not_called()
