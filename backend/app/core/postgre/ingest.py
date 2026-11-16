"""Stores parsed documents in Postgres. Connection settings come from the PG* environment variables."""

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from backend.app.schema.schema import ResumeDocument

## Schema
# One row per ResumeDocument; `row` holds the full validated document as JSON.
CREATE_DOCUMENTS = """
CREATE TABLE IF NOT EXISTS documents (
    id text PRIMARY KEY,
    row jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
)
"""

# Ingestion
UPSERT_DOCUMENT = """
INSERT INTO documents (id, row) VALUES (%s, %s)
ON CONFLICT (id) DO UPDATE SET row = EXCLUDED.row, created_at = now()
"""


def save_document(record: dict[str, Any]) -> None:
    """Store a v2 ResumeDocument; anything that does not match schema.py is rejected before writing."""
    ResumeDocument.model_validate(record)
    with psycopg.connect() as connection:
        connection.execute(CREATE_DOCUMENTS)
        connection.execute(UPSERT_DOCUMENT, (record["document_id"], Jsonb(record)))
