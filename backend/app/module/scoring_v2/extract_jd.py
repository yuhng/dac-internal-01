from pathlib import Path
from typing import Literal

from pydantic import Field
from backend.app.schema.schema import StrictModel
from backend.app.core.llm.client import create_openai_client
from backend.app.core.llm.models import model_for
from backend.app.schema.schema import JobDescription
from .prompts import JD_EXTRACTION_PROMPT


class ExtractedSkill(StrictModel):
    name: str = Field(min_length=1)
    importance: Literal['required', 'preferred', 'unspecified']
    source_quote: str = Field(min_length=1)


class ExtractedJD(StrictModel):
    skills: list[ExtractedSkill]
    parsing_warnings: list[str]

def _build_jd(extracted: ExtractedJD, source_text: str, job_id: str):

    if not extracted.skills and not extracted.parsing_warnings:
        raise ValueError('No skills extracted and no explanation supplied')
    
    return JobDescription.model_validate({
        'job_id': job_id, 'source_text': source_text,
        'review_status': 'needs_review' if extracted.parsing_warnings or not extracted.skills else 'pending',
        'parsing_warnings': extracted.parsing_warnings,
        'skills': [{'requirement_id': f'{job_id}:skill:{i:03d}', **skill.model_dump()}
                   for i, skill in enumerate(extracted.skills, 1)],
    })


def extract_jd(text: str, job_id: str, *, client=None):
    print("Extracting JD...")

    if not text.strip() or not job_id.strip():
        raise ValueError('JD text and job ID must be nonempty')
    if len(text) > 100000:
        raise ValueError('JD exceeds the 100,000 character limit')
    
    if client is None:
        client = create_openai_client()
    response = client.responses.parse(
        model=model_for('scoring_jd'), store=False,
        input=[{'role': 'system', 'content': JD_EXTRACTION_PROMPT},
               {'role': 'user', 'content': text}],
        text_format=ExtractedJD, max_output_tokens=10000,
    )
    if response.status != 'completed' or response.output_parsed is None:
        raise ValueError('JD extraction was refused, incomplete or unparseable; no output saved')
    # Raises ValueError (pydantic ValidationError) if a quote is not an exact JD excerpt.
    return _build_jd(response.output_parsed, text, job_id)
