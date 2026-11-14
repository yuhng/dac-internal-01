"""Expose extracted resume text in the improvement loader's document format."""

from typing import Any

from .resume import HEADINGS

SECTION_NAMES = {
    "summary": "professional_summary",
    "experience": "work_experience",
    "skills": "technical_skills",
}


def to_improvement_document(record: dict[str, Any]) -> dict[str, Any]:
    """Adapt a resume record without reconstructing evidence from parsed fields."""
    if record["document_type"] != "resume":
        raise ValueError("The OCR adapter only supports resumes.")
    if not record["id"] or not record["text"].strip():
        raise ValueError("A resume must have an ID and nonempty text.")

    sections = []
    name = "unclassified"
    lines: list[str] = []

    def finish_section() -> None:
        content = "\n".join(lines)
        if content.strip():
            sections.append({
                "section_id": f"{record['id']}:section:{len(sections) + 1:03d}",
                "section_name": SECTION_NAMES.get(name, name),
                "content": content,
            })
        lines.clear()

    for line in record["text"].splitlines():
        heading = HEADINGS.get(line.strip().rstrip(":").casefold())
        if heading:
            finish_section()
            name = heading
        # Retain headings too, so section content remains an exact source excerpt.
        lines.append(line)
    finish_section()

    return {
        "document_id": record["id"],
        "document_type": record["document_type"],
        "text": record["text"],
        "metadata": {
            "collection_method": record["collection_method"],
            "review_status": record["review_status"],
        },
        "sections": sections,
    }
