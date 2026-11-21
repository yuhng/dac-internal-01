from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class StrictModel(BaseModel):
    """OCR v2 and scoring v2: shared strict validation for resume and JD models."""
    model_config = ConfigDict(extra="forbid", strict=True)


# --------------------------------- OCR + Scoring -------------------------------------------
SectionName = Literal[
    "contact", "summary", "work_experience", "project_experience",
    "technical_skills", "certifications", "education", "other"
]

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
    section_name: SectionName
    entries: list[Entry]


class TextSection(StrictModel):
    """OCR v2 preserves plain sections; scoring v2 reads technical-skills content."""

    section_id: str = Field(min_length=1)
    section_name: SectionName
    content: str


class Metadata(StrictModel):
    """OCR v2 records extraction/review status; scoring v2 uses status to flag provisional scores."""

    collection_method: Literal["pdf_text_layer", "gpt4o_pdf", "gpt4o_image", "claude_pdf"]
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


# --------------------------------- Scoring -------------------------------------------

class SkillRequirement(StrictModel):
    """JD extraction produces one required/preferred skill; scoring v2 matches it against CV evidence."""

    requirement_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    importance: Literal["required", "preferred", "unspecified"]
    source_quote: str | None = Field(default=None, min_length=1)

class JobDescription(StrictModel):
    """JD extraction output and scoring v2 input: validates skills against the JD text."""

    job_id: str = Field(min_length=1)
    skills: list[SkillRequirement]
    source_text: str | None = Field(default=None, min_length=1)
    review_status: Literal["pending", "approved", "needs_review"] = "pending"
    parsing_warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_requirements(self):
        # Imported here: prepare_evidence imports this module, so a top-level import would be circular.
        from backend.app.module.scoring_v2.prepare_evidence import canonical_skill

        ids, skills = set(), set()
        for requirement in self.skills:
            if self.source_text is not None:
                if not requirement.source_quote or requirement.source_quote not in self.source_text:
                    raise ValueError(f"Skill {requirement.name!r}: source_quote must be an exact excerpt of source_text")
                name = " ".join(requirement.name.split()).casefold()
                quote = " ".join(requirement.source_quote.split()).casefold()
                if not name or name not in quote:
                    raise ValueError(f"Skill name must appear in its source_quote: {requirement.name!r}")
            skill = canonical_skill(requirement.name).casefold()
            if requirement.requirement_id in ids or skill in skills:
                raise ValueError("JD requirement IDs and canonical skills must be unique")
            ids.add(requirement.requirement_id)
            skills.add(skill)
        return self
