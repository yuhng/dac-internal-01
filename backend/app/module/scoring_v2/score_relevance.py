import json
import math
from pathlib import Path

from dotenv import load_dotenv
from typesafe_sdk import Score, TypeSafeError

from backend.app.core.llm.client import create_jev_client
from backend.app.core.llm.models import model_for
from backend.app.schema.schema import ResumeDocument
from backend.app.schema.schema import JobDescription
from backend.app.module.scoring_v2.prompts import SCORE_RELEVANCE_RUBRIC, SCORE_RELEVANCE_INSTRUCTIONS

def validate_answer(response):
    """Check the returned score against the requested rubric."""
    try:
        answer = response.answers['experience_relevance']
        probabilities = answer.probabilities
        levels = range(len(SCORE_RELEVANCE_RUBRIC))
        values = [probabilities[i] for i in levels]
        numbers = [answer.score, answer.confidence, *values]

        if any(type(n) not in (int, float) or not math.isfinite(n) for n in numbers):
            raise ValueError('Non-finite or nonnumeric score')
        if answer.type != 'score' or set(probabilities) != set(levels):
            raise ValueError('Wrong answer type or levels')
        if not 0 <= answer.score <= len(SCORE_RELEVANCE_RUBRIC) - 1 or any(not 0 <= p <= 1 for p in values):
            raise ValueError('Score or probabilities out of range')
        if not 0 <= answer.confidence <= 1 or abs(sum(values) - 1) > 0.01:
            raise ValueError('Invalid confidence or probability sum')
        if abs(answer.score - sum(i * p for i, p in enumerate(values))) > 0.02:
            raise ValueError('Score disagrees with probabilities')
        if answer.legend != dict(enumerate(SCORE_RELEVANCE_RUBRIC)):
            raise ValueError('Unexpected rubric legend')
        if not isinstance(response.model, str) or not response.model.strip():
            raise ValueError('Missing returned model')
        for count in (response.usage.input_tokens, response.usage.output_tokens):
            if count is not None and (type(count) is not int or count < 0):
                raise ValueError('Invalid usage')
        return answer
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f'Invalid JEV response: {error}') from None

def score_cv_jd(client, cv, jd):
    """Evaluate one CV-JD text pair; missing text yields an unscored result."""

    response = client.system_one(
        state={'cv': cv, 'jd': jd},
        questions={
            'experience_relevance': Score(
                instructions=SCORE_RELEVANCE_INSTRUCTIONS,
                criteria=SCORE_RELEVANCE_RUBRIC,
            )
        },
    )

    result = validate_answer(response)
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    return {
        'model': response.model,
        'jev_score': result.score,
        'jev_score_100': result.score / (len(SCORE_RELEVANCE_RUBRIC) - 1) * 100,
        # Confidence measures probability concentration, not matching accuracy.
        'jev_confidence': result.confidence,
        'jev_probabilities': result.probabilities,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': input_tokens + output_tokens
        if input_tokens is not None and output_tokens is not None else None,
    }

def score_relevance(document: ResumeDocument, jd: JobDescription, *, model=model_for('scoring_relevance'), client=None):
    """Score structured CV sections without the separately scored skills list."""
    print("Scoring Relevance...")    
    sections = [section.model_dump() for section in document.sections
                if section.section_name != 'technical_skills']
    if not sections:
        raise ValueError('Resume must contain sections other than technical_skills')
    
    # Raw document.text also contains the skills list; never fall back to it.
    cv = json.dumps(sections, ensure_ascii=False)
    if client is None:
        with create_jev_client(model=model) as owned_client:
            scores = score_cv_jd(owned_client, cv, jd.source_text)
    else:
        scores = score_cv_jd(client, cv, jd.source_text)
    return {
        'scoring_version': 'relevance-3', 'rubric_version': 'fit-3-level-v1',
        'job_id': jd.job_id, 'document_id': document.document_id,
        'document_version': document.document_version,
        'provisional': document.metadata.review_status != 'approved' or jd.review_status != 'approved',
        'requested_model': model,
        'rubric': SCORE_RELEVANCE_RUBRIC, 'aggregation': 'whole_cv_jd',
        'excluded_sections': ['technical_skills'], **scores,
        'warnings': document.parsing_warnings + jd.parsing_warnings + [
            'Confidence is returned by JEV; it is not a measured extraction or matching accuracy.',
        ],
    }