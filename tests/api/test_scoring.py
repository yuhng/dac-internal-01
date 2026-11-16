import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from openai import APIConnectionError
import httpx2
from typesafe_sdk import SystemOneResponse

from backend.app.api import scoring
from backend.app.main import app
from backend.app.module.scoring_v2 import score_relevance
from backend.app.schema.schema import JobDescription

client = TestClient(app)
JD_TEXT = "Requires Python."


def cv():
    return {
        "schema_version": "2", "document_id": "CV_001", "document_version": 1,
        "document_type": "resume", "text": "Built Python services.\nSkills: Python",
        "metadata": {"collection_method": "claude_pdf", "review_status": "approved"},
        "sections": [
            {"section_id": "CV_001:summary", "section_name": "summary", "content": "Built Python services."},
            {"section_id": "CV_001:technical_skills", "section_name": "technical_skills", "content": "Skills: Python"},
        ],
        "parsing_warnings": [],
    }


def jev_response():
    answer = {"type": "score", "score": 1.5, "confidence": 0.8,
              "probabilities": {0: 0.1, 1: 0.3, 2: 0.6},
              "legend": dict(enumerate(score_relevance.RUBRIC))}
    return SystemOneResponse.model_validate_json(json.dumps({
        "model": "jev-test", "usage": {"input_tokens": 20, "output_tokens": 5},
        "answers": {"experience_relevance": answer},
    }))


@pytest.fixture(autouse=True)
def models(monkeypatch):
    """Replace both model calls; everything between them runs for real."""
    def fake_extract_jd(text, job_id):
        return JobDescription(job_id=job_id, source_text=text, review_status="approved", skills=[
            {"requirement_id": f"{job_id}:skill:001", "name": "Python",
             "importance": "required", "source_quote": "Requires Python"}])
    monkeypatch.setattr(scoring, "extract_jd", fake_extract_jd)
    jev = MagicMock()
    jev.return_value.__enter__.return_value.system_one.return_value = jev_response()
    monkeypatch.setattr(score_relevance, "create_jev_client", jev)


def post(**overrides):
    return client.post("/api/scoring/analyze",
                       json={"title": "Data Engineer", "company": "Acme", "jd": JD_TEXT, "document": cv(), **overrides})


def test_scores_document_against_jd():
    response = post()
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Data Engineer" and body["company"] == "Acme"
    # Python matched (skill 100) and Jev 1.5/2 (relevance 75): 0.40*100 + 0.60*75.
    assert body["overall"]["overall_score_100"] == 85
    assert body["overall"]["method"] == "weighted_skills_and_relevance"
    assert body["overall"]["provisional"] is False
    assert body["skill_scores"]["skills"][0]["matched"] is True


def test_invalid_document_is_rejected_before_scoring():
    bad = cv()
    bad["sections"][1]["section_name"] = "skills"
    assert post(document=bad).status_code == 422


def test_unscoreable_jd_returns_422(monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("No skills extracted and no explanation supplied")
    monkeypatch.setattr(scoring, "extract_jd", fail)
    response = post()
    assert response.status_code == 422
    assert "No skills extracted" in response.json()["detail"]


def test_model_outage_returns_503(monkeypatch):
    def fail(*args, **kwargs):
        raise APIConnectionError(request=httpx2.Request("POST", "https://api.openai.com"))
    monkeypatch.setattr(scoring, "extract_jd", fail)
    response = post()
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]
