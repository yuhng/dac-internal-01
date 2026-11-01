"""Document API: turns an uploaded resume into a row matching data/schema.json."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import jsonschema
from fastapi import APIRouter, HTTPException, UploadFile, status

from mycareerai.ai.ocr import OcrError, build_record

MAX_UPLOAD_BYTES = 10_000_000
ROW_PATH = Path(__file__).resolve().parents[3] / "data" / "processed" / "row.json"

router = APIRouter(prefix="/documents", tags=["documents"])


# Not async: OCR blocks, so FastAPI needs to run this in its thread pool.
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

    ROW_PATH.parent.mkdir(parents=True, exist_ok=True)
    ROW_PATH.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record
