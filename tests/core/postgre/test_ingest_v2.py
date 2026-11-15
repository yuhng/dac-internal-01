from unittest.mock import MagicMock

from mycareerai.core.postgre import ingest


def test_v2_document_is_stored_without_legacy_fields(monkeypatch):
    connection = MagicMock()
    connect = MagicMock()
    connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr(ingest.psycopg, "connect", connect)
    record = {"document_id": "CV_001", "schema_version": "2", "text": "Python", "sections": []}
    ingest.save_document(record)
    assert connection.execute.call_count == 2
    sql, params = connection.execute.call_args.args
    assert sql == ingest.UPSERT_DOCUMENT
    assert params[0] == "CV_001"
    assert params[1].obj == record
