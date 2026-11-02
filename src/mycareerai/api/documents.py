"""Document API: turns an uploaded resume into a row matching data/schema.json."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import jsonschema
import psycopg
from fastapi import APIRouter, HTTPException, UploadFile, status

from mycareerai.ai.ocr import OcrError, build_record
from mycareerai.core.postgre.ingest import save_document

MAX_UPLOAD_BYTES = 10_000_000
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# OCR and Postgres Ingestion module
@router.post("/extract")
def extract(file: UploadFile) -> dict[str, Any]:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF files can be read.")

    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "That file is larger than 10 MB.")

    # A fixed name keeps the client's file name out of the path, and it appears in OcrError messages.
    with TemporaryDirectory() as directory:
        path = Path(directory) / "document.pdf"
        path.write_bytes(content)
        try:
            record = build_record(path, source=file.filename, license="user-provided")
        except OcrError as err:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(err)) from err
        except jsonschema.ValidationError as err:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The resume could not be parsed.") from err

    try:
        save_document(record)
    except psycopg.Error as err:
        logger.exception("Saving the document failed")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The resume could not be saved. Try again in a moment.") from err
    return record
