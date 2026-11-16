from types import SimpleNamespace

import pytest

from backend.app.schema.schema import ResumeDocument
from backend.app.module.scoring_v2.extract_jd import ExtractedJD, build_jd, extract_jd
from backend.app.module.scoring_v2.prepare_evidence import prepare_evidence, skill_mentions
from backend.app.module.scoring_v2.score_skills import score_skills
from backend.app.schema.schema import JobDescription


SOURCE = 'Required: Python, PyTorch and PostgreSQL.'


def extracted(quote=SOURCE):
    return ExtractedJD(skills=[
        {'name': name, 'importance': 'required', 'source_quote': quote}
        for name in ['Python', 'PyTorch', 'PostgreSQL']
    ], parsing_warnings=[])


def test_extraction_roundtrip_and_scoring_handoff():
    client = SimpleNamespace(responses=SimpleNamespace(parse=lambda **kwargs: SimpleNamespace(
        status='completed', output_parsed=extracted())))
    jd = extract_jd(SOURCE, 'JD_001', client=client)
    jd = JobDescription.model_validate_json(jd.model_dump_json())
    assert jd.source_text == SOURCE
    assert jd.skills[1].source_quote == SOURCE
    assert jd.review_status == 'pending'
    resume = ResumeDocument.model_validate({
        'schema_version': '2', 'document_id': 'CV_001', 'document_version': 1,
        'document_type': 'resume', 'text': 'PyTorch, Postgres',
        'metadata': {'collection_method': 'gpt4o_pdf', 'review_status': 'approved'},
        'sections': [{'section_id': 'CV_001:skills', 'section_name': 'technical_skills',
                      'content': 'PyTorch, Postgres'}], 'parsing_warnings': [],
    })
    result = score_skills(prepare_evidence(resume), jd)
    assert [s['matched'] for s in result['skills']] == [False, True, True]
    assert result['skills'][1]['matching_method'] == 'exact_name'
    assert result['skills'][2]['matching_method'] == 'exact_name_with_known_aliases'
    assert result['coverage']['required']['percent'] == 66.67
    assert result['provisional'] is True


def test_fabricated_quote_is_rejected():
    with pytest.raises(ValueError, match='exact excerpt'):
        build_jd(extracted('Invented Python PyTorch PostgreSQL'), SOURCE, 'JD_001')


def test_skill_must_appear_in_quote():
    with pytest.raises(ValueError, match='name must appear'):
        build_jd(extracted('Required: Python'), SOURCE, 'JD_001')


def test_duplicate_aliases_are_rejected():
    with pytest.raises(ValueError, match='must be unique'):
        JobDescription(job_id='JD', skills=[
            {'requirement_id': str(i), 'name': name, 'importance': 'required'}
            for i, name in enumerate(['Postgres', 'PostgreSQL'])
        ])


def test_existing_minimal_jd_still_loads():
    assert JobDescription(job_id='JD', skills=[]).review_status == 'pending'


def test_unknown_skill_matching_respects_word_boundaries():
    assert not list(skill_mentions('PyTorchish', ['PyTorch']))
    assert list(skill_mentions('Uses PyTorch.', ['PyTorch']))


def test_empty_extraction_with_warning_is_retained():
    jd = build_jd(ExtractedJD(skills=[], parsing_warnings=['No technical skills']), SOURCE, 'JD')
    assert jd.review_status == 'needs_review'
    assert jd.parsing_warnings == ['No technical skills']


def test_wrapped_skill_name_preserves_exact_quote():
    source = 'Required: Power\nBI'
    item = ExtractedJD(skills=[{'name': 'Power BI', 'importance': 'required', 'source_quote': source}], parsing_warnings=[])
    assert build_jd(item, source, 'JD').skills[0].source_quote == source


def test_invalid_evidence_is_corrected_once():
    from unittest.mock import Mock
    invalid = extracted()
    invalid.skills[0].name = 'Invented skill'
    parse = Mock(side_effect=[
        SimpleNamespace(status='completed', output_parsed=invalid),
        SimpleNamespace(status='completed', output_parsed=extracted()),
    ])
    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    assert extract_jd(SOURCE, 'JD', client=client).skills[0].name == 'Python'
    assert parse.call_count == 2
    assert 'Invented skill' in parse.call_args.kwargs['input'][-1]['content']
    assert len(parse.call_args_list[0].kwargs['input']) == 2


def test_invalid_correction_stops_with_skill_name():
    from unittest.mock import Mock
    invalid = extracted()
    invalid.skills[0].name = 'Invented skill'
    parse = Mock(return_value=SimpleNamespace(status='completed', output_parsed=invalid))
    with pytest.raises(ValueError, match='after correction:.*Invented skill'):
        extract_jd(SOURCE, 'JD', client=SimpleNamespace(responses=SimpleNamespace(parse=parse)))
    assert parse.call_count == 2


def test_unknown_section_name_is_rejected():
    # Scoring reads sections by name, so a misspelt name must fail loudly instead of scoring 0%.
    from pydantic import ValidationError
    from backend.app.schema.schema import ResumeDocument
    from test_relevance import document

    record = document().model_dump()
    record["sections"][0]["section_name"] = "skills"
    with pytest.raises(ValidationError):
        ResumeDocument.model_validate(record)
