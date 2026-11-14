"""Step 1: validate the resume document contract. Requires pydantic>=2,<3."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Entry(StrictModel):
    project_name: str | None = None
    entry_id: str = Field(min_length=1)
    job_title: str | None
    company: str | None
    start_date: str | None
    end_date: str | None
    content: str


class EntriesSection(StrictModel):
    section_id: str = Field(min_length=1)
    section_name: str = Field(min_length=1)
    entries: list[Entry]


class TextSection(StrictModel):
    section_id: str = Field(min_length=1)
    section_name: str = Field(min_length=1)
    content: str


class Metadata(StrictModel):
    collection_method: Literal["pdf_text_layer", "gpt4o_pdf", "gpt4o_image"]
    review_status: Literal["pending", "approved", "needs_review"]


class ResumeDocument(StrictModel):
    schema_version: Literal["1", "2"]
    document_id: str = Field(min_length=1)
    document_version: int = Field(ge=1)
    document_type: Literal["resume"]
    text: str = Field(min_length=1)
    metadata: Metadata
    sections: list[EntriesSection | TextSection]
    parsing_warnings: list[str]

    @model_validator(mode="after")
    def validate_ids(self):
        seen = {self.document_id}
        for section in self.sections:
            if not section.section_id.startswith(self.document_id + ":"):
                raise ValueError("Section ID must belong to its document")
            ids = [section.section_id]
            if isinstance(section, EntriesSection):
                for entry in section.entries:
                    if not entry.entry_id.startswith(section.section_id + ":"):
                        raise ValueError("Entry ID must belong to its section")
                    ids.append(entry.entry_id)
            for identifier in ids:
                if identifier in seen:
                    raise ValueError("Duplicate section or entry ID")
                seen.add(identifier)
        return self


def self_check():
    sample = {
        "schema_version": "1", "document_id": "CV_001",
        "document_version": 1, "document_type": "resume",
        "text": "WORK EXPERIENCE\nBuilt Python ETL pipelines...",
        "metadata": {"collection_method": "pdf_text_layer", "review_status": "pending"},
        "sections": [
            {"section_id": "CV_001:experience", "section_name": "work_experience",
             "entries": [{"entry_id": "CV_001:experience:001",
                          "job_title": "Data Analyst Intern", "company": "Schneider Electric",
                          "start_date": "June 2025", "end_date": "December 2025",
                          "content": "Built Python ETL pipelines..."}]},
            {"section_id": "CV_001:skills", "section_name": "technical_skills",
             "content": "Python, SQL, Tableau"}
        ],
        "parsing_warnings": []
    }
    document = ResumeDocument.model_validate(sample)
    assert document.model_dump(exclude_unset=True) == sample
    for change in (
        {"document_version": 0},
        {"unexpected_field": True},
        {"sections": [sample["sections"][0], sample["sections"][0]]},
        {"document_id": "CV_002"},
    ):
        try:
            ResumeDocument.model_validate({**sample, **change})
        except ValidationError:
            continue
        raise AssertionError(f"Invalid input accepted: {change}")
    print("Passed: sample round-trip and four invalid-input checks.")


if __name__ == "__main__":
    self_check()
