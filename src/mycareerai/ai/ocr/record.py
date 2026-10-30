"""Builds a schema-valid table row from a resume PDF."""

import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema

from .extract import extract_text
from .resume import parse_resume

SCHEMA_PATH = Path(__file__).resolve().parents[4] / "data" / "schema.json"


def validate_record(record: dict[str, Any], schema_path: Path = SCHEMA_PATH) -> None:
    jsonschema.validate(record, json.loads(schema_path.read_text()))


def build_record(
    path: Path,
    *,
    source: str | None = None,
    license: str = "unknown",
    force_ocr: bool = False,
) -> dict[str, Any]:
    document = extract_text(path, force_ocr=force_ocr)
    fields = parse_resume(document.text)

    record = {
        # Hashing the file keeps the id stable when the same document is processed again.
        "id": hashlib.sha256(path.read_bytes()).hexdigest(),
        "document_type": "resume",
        "text": document.text,
        "work_experience": fields["work_experience"],
        "education": fields["education"],
        "certifications": fields["certifications"],
        "skills": fields["skills"],
        # Job description fields.
        "responsibilities": None,
        "requirements": None,
        "qualifications": None,
        "hard_skills": fields["hard_skills"],
        "soft_skills": fields["soft_skills"],
        # These need judgement, so they stay null until a model or a reviewer fills them in.
        "occupation": None,
        "seniority_level": None,
        "industry": None,
        "resume_format": None,
        "writing_style": None,
        "source": source or path.name,
        "collection_method": document.method,
        "license": license,
        "annotation_method": "rule_based",
        "review_status": "pending",
    }
    validate_record(record)
    return record
