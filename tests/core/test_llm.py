from unittest.mock import Mock

import pytest

from mycareerai.core import llm
from mycareerai.module.improvement.src.cv_improvement import CVRecommendationEngine
from mycareerai.module.improvement.src.gap_analysis import EvidenceAssessor
from mycareerai.module.ocr_v2 import extractor


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    monkeypatch.setattr(llm, "load_dotenv", Mock())


def test_shared_client_configuration(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    constructor = Mock()
    monkeypatch.setattr(llm.openai, "OpenAI", constructor)
    assert llm.create_llm_client() is constructor.return_value
    constructor.assert_called_once_with(api_key="test-key", timeout=120.0, max_retries=2)
    llm.create_llm_client(timeout=30, max_retries=0)
    constructor.assert_called_with(api_key="test-key", timeout=30, max_retries=0)
    assert llm.load_dotenv.call_count == 2


@pytest.mark.parametrize("key", [None, "", "  "])
def test_missing_key_fails_before_sdk_construction(monkeypatch, key):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    if key is not None:
        monkeypatch.setenv("OPENAI_API_KEY", key)
    constructor = Mock()
    monkeypatch.setattr(llm.openai, "OpenAI", constructor)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        llm.create_llm_client()
    constructor.assert_not_called()


@pytest.mark.parametrize("engine", [EvidenceAssessor, CVRecommendationEngine])
def test_improvement_uses_shared_factory_and_accepts_injection(monkeypatch, engine):
    factory = Mock()
    monkeypatch.setattr(f"{engine.__module__}.create_llm_client", factory)
    assert engine().client is factory.return_value
    factory.assert_called_once_with()
    injected = Mock()
    assert engine(client=injected).client is injected
    factory.assert_called_once_with()


def test_ocr_uses_factory_and_accepts_injection(monkeypatch, tmp_path):
    pdf = tmp_path / "cv.pdf"
    pdf.write_bytes(b"%PDF-1.7\nfixture")
    extracted = extractor.ExtractedResume.model_validate({
        "text": "Python", "sections": [
            {"section_name": "technical_skills", "entries": [], "content": "Python"}
        ], "parsing_warnings": [],
    })
    client = Mock()
    client.responses.parse.return_value.status = "completed"
    client.responses.parse.return_value.output_parsed = extracted
    factory = Mock(return_value=client)
    monkeypatch.setattr(extractor, "create_llm_client", factory)
    assert extractor.extract_resume(pdf, "CV_001").text == "Python"
    factory.assert_called_once_with()
    assert extractor.extract_resume(pdf, "CV_002", client=client).text == "Python"
    factory.assert_called_once_with()
