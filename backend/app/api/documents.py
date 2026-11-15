"""Document API: extract and store the OCR v2 resume contract."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, UploadFile, status
from openai import OpenAIError
from uuid import uuid4

from app.module.ocr_v2.extractor import extract_resume
from backend.app.schema.schema import ResumeDocument
from app.core.postgre.ingest import save_document

MAX_UPLOAD_BYTES = 10_000_000
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# OCR and Postgres Ingestion module
@router.post("/extract", response_model=ResumeDocument)
def extract(file: UploadFile) -> dict[str, Any]:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF files can be read.")

    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "That file is larger than 10 MB.")

    # A fixed name keeps the client's file name out of the path.
    with TemporaryDirectory() as directory:
        path = Path(directory) / "document.pdf"
        path.write_bytes(content)
        try:
            document = extract_resume(path, document_id=f"CV_{uuid4().hex}")
            record = document.model_dump()
        except ValueError as err:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The resume could not be read. Upload a readable resume PDF and try again.") from err
        except (OpenAIError, RuntimeError) as err:
            logger.exception("Resume extraction service failed")
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The resume extraction service is unavailable. Try again in a moment.") from err

    try:
        save_document(record)
    except psycopg.Error as err:
        logger.exception("Saving the document failed")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The resume could not be saved. Try again in a moment.") from err
    return record
