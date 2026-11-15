"""Stores parsed documents in Postgres. Connection settings come from the PG* environment variables."""

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

## Schema
# Document metadata 
CREATE_DOCUMENTS = """
CREATE TABLE IF NOT EXISTS documents (
    id text PRIMARY KEY,
    row jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
)
"""

# Document fields
CREATE_RESUMES = """
CREATE TABLE IF NOT EXISTS resumes (
    document_id text PRIMARY KEY REFERENCES documents (id) ON DELETE CASCADE,
    email text,
    phone text,
    work_experience jsonb,
    education jsonb,
    certifications text[],
    skills text[],
    hard_skills text[],
    soft_skills text[],
    occupation text,
    seniority_level text,
    industry text,
    resume_format text,
    writing_style text,
    created_at timestamptz NOT NULL DEFAULT now()
)
"""

# Ingestion
UPSERT_DOCUMENT = """
INSERT INTO documents (id, row) VALUES (%s, %s)
ON CONFLICT (id) DO UPDATE SET row = EXCLUDED.row, created_at = now()
"""

UPSERT_RESUME = """
INSERT INTO resumes (
    document_id, email, phone, work_experience, education, certifications, skills, hard_skills, soft_skills,
    occupation, seniority_level, industry, resume_format, writing_style
) VALUES (
    %(id)s, %(email)s, %(phone)s, %(work_experience)s, %(education)s, %(certifications)s, %(skills)s,
    %(hard_skills)s, %(soft_skills)s, %(occupation)s, %(seniority_level)s, %(industry)s, %(resume_format)s,
    %(writing_style)s
)
ON CONFLICT (document_id) DO UPDATE SET
    email = EXCLUDED.email, phone = EXCLUDED.phone, work_experience = EXCLUDED.work_experience,
    education = EXCLUDED.education, certifications = EXCLUDED.certifications, skills = EXCLUDED.skills,
    hard_skills = EXCLUDED.hard_skills, soft_skills = EXCLUDED.soft_skills, occupation = EXCLUDED.occupation,
    seniority_level = EXCLUDED.seniority_level, industry = EXCLUDED.industry,
    resume_format = EXCLUDED.resume_format, writing_style = EXCLUDED.writing_style, created_at = now()
"""


def save_document(record: dict[str, Any]) -> None:
    """Store the v2 document contract without the legacy resume projection."""
    with psycopg.connect() as connection:
        connection.execute(CREATE_DOCUMENTS)
        connection.execute(UPSERT_DOCUMENT, (record["document_id"], Jsonb(record)))


def save_table(record: dict[str, Any]) -> None:
    with psycopg.connect() as connection:
        connection.execute(CREATE_DOCUMENTS)
        connection.execute(CREATE_RESUMES)
        connection.execute(UPSERT_DOCUMENT, (record["id"], Jsonb(record)))
        resume = {**record, "work_experience": Jsonb(record["work_experience"]), "education": Jsonb(record["education"])}
        connection.execute(UPSERT_RESUME, resume)


