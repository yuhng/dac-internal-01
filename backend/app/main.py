"""Usage: uv run uvicorn backend.app.main:app --reload"""

from dotenv import load_dotenv
from fastapi import FastAPI

from ..api.ocr import router as ocr_router
from ..api.scoring import router as scoring_router

# Reads the PG* database settings from .env. Variables already set, as in a deployment, are kept.
load_dotenv()

app = FastAPI(title="MyCareerAI")
app.include_router(ocr_router, prefix="/api")
app.include_router(scoring_router, prefix="/api")
