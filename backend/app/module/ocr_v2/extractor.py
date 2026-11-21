"""Extract a PDF resume with Claude Sonnet 5.5, then build the application-owned envelope."""
import argparse
import base64
from pathlib import Path

import anthropic
from backend.app.core.llm.client import create_claude_client
from backend.app.core.llm.models import effort_for, model_for
from pydantic import Field
from ...schema.schema import ResumeDocument, SectionName, StrictModel
from backend.app.module.ocr_v2.prompts import OCR_PROMPT

class ExtractedEntry(StrictModel):
    project_name: str | None = None
    job_title: str | None
    company: str | None
    start_date: str | None
    end_date: str | None
    content: str


class ExtractedSection(StrictModel):
    section_name: SectionName
    entries: list[ExtractedEntry]
    content: str | None


class ExtractedResume(StrictModel):
    text: str = Field(min_length=1)
    sections: list[ExtractedSection]
    parsing_warnings: list[str]




def build_document(extracted: ExtractedResume, document_id: str, version: int):
    sections = []
    counts = {}
    for section in extracted.sections:
        name = section.section_name
        counts[name] = counts.get(name, 0) + 1
        # Repeat sections get distinct IDs without merging their contents.
        suffix = "" if counts[name] == 1 else f":{counts[name]:03d}"
        section_id = f"{document_id}:{name}{suffix}"
        item = {"section_id": section_id, "section_name": name}
        if section.entries:
            if section.content is not None:
                raise ValueError("Entry-based section also contains text; review extraction")
            item["entries"] = [
                {"entry_id": f"{section_id}:{i:03d}", **entry.model_dump()}
                for i, entry in enumerate(section.entries, 1)
            ]
        else:
            item["content"] = section.content or ""
        sections.append(item)
    if not sections:
        raise ValueError("No resume sections extracted; review the PDF")
    return ResumeDocument.model_validate({
        "schema_version": "2", "document_id": document_id,
        "document_version": version, "document_type": "resume",
        "text": extracted.text,
        "metadata": {"collection_method": "claude_pdf",
                     "review_status": "needs_review" if extracted.parsing_warnings else "pending"},
        "sections": sections, "parsing_warnings": extracted.parsing_warnings,
    })


def extract_resume(pdf_path: Path, document_id: str, version: int = 1, *, client=None):

    # Value Checks
    if not document_id.strip() or version < 1:
        raise ValueError("Provide a nonempty document ID and a positive version")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Input must be a PDF")
    # shortcut: cap PDFs at 10 MiB; add page limits and preprocessing for larger documents.
    if not 0 < pdf_path.stat().st_size <= 10 * 1024 * 1024:
        raise ValueError("PDF must be nonempty and no larger than 10 MiB")
    data = pdf_path.read_bytes()
    if b"%PDF-" not in data[:1024]:
        raise ValueError("File does not have a PDF header")

    if client is None:
        client = create_claude_client()
    effort = effort_for("ocr_v2")
    response = client.beta.messages.parse(
        model=model_for("ocr_v2"),
        max_tokens=16000,
        output_config={"effort": effort} if effort else anthropic.omit,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=OCR_PROMPT,
        messages=[{"role": "user", "content": [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                            "data": base64.standard_b64encode(data).decode("ascii")}},
            {"type": "text", "text": "Extract this resume using the supplied schema."},
        ]}],
        output_format=ExtractedResume,
    )
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        raise ValueError(f"Extraction stopped ({response.stop_reason}) or was unparseable; no output saved")
    return build_document(response.parsed_output, document_id, version)