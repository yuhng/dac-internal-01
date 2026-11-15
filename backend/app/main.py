"""Usage: uv run uvicorn mycareerai.main:app --reload"""

from dotenv import load_dotenv
from fastapi import FastAPI

from .api.documents import router as documents_router
from .api.scoring import router as scoring_router

# Reads the PG* database settings from .env. Variables already set, as in a deployment, are kept.
load_dotenv()

app = FastAPI(title="MyCareerAI")
app.include_router(documents_router, prefix="/api")
app.include_router(scoring_router, prefix="/api")
