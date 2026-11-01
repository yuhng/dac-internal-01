"""Usage: uv run uvicorn mycareerai.main:app --reload"""

from fastapi import FastAPI

from .api.documents import router as documents_router

app = FastAPI(title="MyCareerAI")
app.include_router(documents_router, prefix="/api")
