"""Scoring API: compares a CV with a job description."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from mycareerai.ai.scoring import ScoringError, analyze

MAX_TEXT_CHARS = 50_000

router = APIRouter(prefix="/scoring", tags=["scoring"])


class ScoreInput(BaseModel):
    title: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=200)
    jd: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    cv: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)


# Not async: scoring is CPU work, so FastAPI needs to run this in its thread pool.
@router.post("/analyze")
def analyze_match(data: ScoreInput) -> dict[str, Any]:
    try:
        return analyze(data.title, data.company, data.jd, data.cv)
    except ScoringError as err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(err)) from err
