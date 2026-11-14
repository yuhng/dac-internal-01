import json

import pytest

from mycareerai.module.ocr import ExtractedDocument, Page, build_record, to_improvement_document
from mycareerai.module.improvement.src.data_loader import load_documents


TEXT = """Sam Example
SUMMARY
Data analyst with Python experience.
WORK EXPERIENCE
An unconventional role header without dates
- Built Python pipelines and
  improved reporting.
PROJECTS
Community dashboard
- Visualized local data.
SKILLS
SQL, Tableau
PROJECTS
Another project
- Preserved separately.
"""


def record(text=TEXT):
    return {
        "id": "cv-hash", "document_type": "resume", "text": text,
        "collection_method": "pdf_text_layer", "review_status": "pending",
    }


def test_preserves_sections_and_exact_text_without_rebuilding_skills():
    adapted = to_improvement_document(record())
    sections = adapted["sections"]
    assert adapted["text"] == TEXT
    assert adapted["document_id"] == "cv-hash"
    assert [s["section_name"] for s in sections] == [
        "unclassified", "professional_summary", "work_experience",
        "projects", "technical_skills", "projects",
    ]
    assert len({s["section_id"] for s in sections}) == len(sections)
    assert all(s["content"] in TEXT for s in sections)
    assert "- Built Python pipelines and\n  improved reporting." in sections[2]["content"]
    assert sections[4]["content"] == "SKILLS\nSQL, Tableau"
    assert to_improvement_document(record()) == adapted


def test_unheaded_text_is_preserved():
    adapted = to_improvement_document(record("Unrecognized layout\nSome experience"))
    assert adapted["sections"] == [{
        "section_id": "cv-hash:section:001", "section_name": "unclassified",
        "content": "Unrecognized layout\nSome experience",
    }]


@pytest.mark.parametrize("text", ["", " \n\t"])
def test_rejects_empty_evidence(text):
    with pytest.raises(ValueError, match="nonempty text"):
        to_improvement_document(record(text))


def test_build_record_output_loads_as_improvement_documents(tmp_path, monkeypatch):
    pdf = tmp_path / "cv.pdf"
    pdf.write_bytes(b"fixture")
    monkeypatch.setattr(
        "mycareerai.module.ocr.record.extract_text",
        lambda *args, **kwargs: ExtractedDocument((Page(1, TEXT, "text_layer"),)),
    )
    result = build_record(pdf)
    assert result["text"] == TEXT
    assert result["work_experience"] == []
    assert result["document_id"] == result["id"]
    (tmp_path / "cv.json").write_text(json.dumps(result))
    documents = load_documents(str(tmp_path))
    assert len(documents) == len(result["sections"])
    assert [d.page_content for d in documents] == [s["content"] for s in result["sections"]]
    assert all(d.metadata["document_id"] == result["id"] for d in documents)
    assert "projects" in {d.metadata["section_name"] for d in documents}
