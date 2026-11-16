"""Scoring API: scores a structured CV against a job description with scoring v2."""

import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from openai import OpenAIError
from pydantic import BaseModel, Field
from typesafe_sdk import TypeSafeError

from backend.app.module.scoring_v2.extract_jd import extract_jd
from backend.app.module.scoring_v2.overall_score import score_application
from backend.app.schema.schema import ResumeDocument

MAX_TEXT_CHARS = 50_000
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scoring", tags=["scoring"])


class ScoreInput(BaseModel):
    title: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=200)
    jd: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    # The structured CV returned by /api/documents/extract; FastAPI validates it against schema.py.
    document: ResumeDocument


# Not async: this makes slow, blocking model calls, so FastAPI runs it in its thread pool.
@router.post("/analyze")
def analyze_match(data: ScoreInput) -> dict[str, Any]:
    try:
        jd = extract_jd(data.jd, job_id=f"JD_{uuid4().hex}")
        result = score_application(data.document, jd)
    except ValueError as err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(err)) from err
    except (OpenAIError, TypeSafeError, RuntimeError) as err:
        logger.exception("Scoring v2 failed")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "The scoring service is unavailable. Try again in a moment.") from err
    return {"title": data.title, "company": data.company, **result}
