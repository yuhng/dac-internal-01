"""Shared OCR v2 output and scoring v2 input models.

Improvement consumes serialized section data rather than importing these models.
Legacy OCR uses its separate YAML schema. Requires pydantic>=2,<3.
"""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class StrictModel(BaseModel):
    """OCR v2 and scoring v2: shared strict validation for resume and JD models."""

    model_config = ConfigDict(extra="forbid", strict=True)


class Entry(StrictModel):
    """OCR v2 produces one job/project; scoring v2 reads its content as evidence."""

    project_name: str | None = None
    entry_id: str = Field(min_length=1)
    job_title: str | None
    company: str | None
    start_date: str | None
    end_date: str | None
    content: str


class EntriesSection(StrictModel):
    """OCR v2 groups jobs/projects; scoring v2 and OCR review iterate the entries."""

    section_id: str = Field(min_length=1)
    section_name: str = Field(min_length=1)
    entries: list[Entry]


class TextSection(StrictModel):
    """OCR v2 preserves plain sections; scoring v2 reads technical-skills content."""

    section_id: str = Field(min_length=1)
    section_name: str = Field(min_length=1)
    content: str


class Metadata(StrictModel):
    """OCR v2 records extraction/review status; scoring v2 uses status to flag provisional scores."""

    collection_method: Literal["pdf_text_layer", "gpt4o_pdf", "gpt4o_image"]
    review_status: Literal["pending", "approved", "needs_review"]


class ResumeDocument(StrictModel):
    """OCR v2/API output and scoring v2 input: validates the full resume and its IDs."""

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

