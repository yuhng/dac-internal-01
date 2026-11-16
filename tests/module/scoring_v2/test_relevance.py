import json
from unittest.mock import Mock

import pytest
from typesafe_sdk import SystemOneResponse

from backend.app.module.scoring_v2 import score_relevance as scoring
from backend.app.schema.schema import JobDescription
from backend.app.schema.schema import ResumeDocument


def response(**overrides):
    answer = {'type': 'score', 'score': 1.5, 'confidence': 0.8,
              'probabilities': {0: 0.1, 1: 0.3, 2: 0.6},
              'legend': dict(enumerate(scoring.RUBRIC))}
    answer.update(overrides)
    return SystemOneResponse.model_validate_json(json.dumps({
        'model': 'jev-test', 'usage': {'input_tokens': 20, 'output_tokens': 5},
        'answers': {'experience_relevance': answer},
    }))


def document():
    return ResumeDocument(
        schema_version='2', document_id='CV_001', document_version=1,
        document_type='resume', text='Built Python services.',
        metadata={'collection_method': 'pdf_text_layer', 'review_status': 'approved'},
        sections=[{'section_id': 'CV_001:summary', 'section_name': 'summary',
                   'content': 'Built Python services.'}], parsing_warnings=[],
    )


def test_whole_pair_uses_rubric_and_normalizes_score():
    client = Mock(system_one=Mock(return_value=response()))
    result = scoring.score_cv_jd(client, 'Built Python services.', 'Build APIs.')
    assert result['jev_score_100'] == 75
    assert result['total_tokens'] == 25
    assert result['model'] == 'jev-test'
    assert result['jev_probabilities'] == {0: 0.1, 1: 0.3, 2: 0.6}
    client.system_one.assert_called_once()
    request = client.system_one.call_args.kwargs
    assert request['state'] == {'cv': 'Built Python services.', 'jd': 'Build APIs.'}
    assert request['questions']['experience_relevance'].criteria == scoring.RUBRIC


@pytest.mark.parametrize('missing', [None, float('nan'), '', '   '])
@pytest.mark.parametrize('side', ['cv', 'jd'])
def test_missing_text_does_not_call_api(missing, side):
    client = Mock()
    inputs = {'cv': 'CV', 'jd': 'JD', side: missing}
    assert all(value is None for value in scoring.score_cv_jd(client, **inputs).values())
    client.system_one.assert_not_called()


def test_missing_usage_remains_unknown():
    result = response().model_copy(update={'usage': response().usage.model_copy(
        update={'input_tokens': None})})
    scores = scoring.score_cv_jd(Mock(system_one=Mock(return_value=result)), 'CV', 'JD')
    assert scores['input_tokens'] is None
    assert scores['total_tokens'] is None
    assert scores['output_tokens'] == 5


@pytest.mark.parametrize('changes', [
    {'score': 1.9},
    {'legend': {0: 'Wrong', 1: 'Rubric', 2: 'Here'}},
    {'probabilities': {0: 0.1, 1: 0.3}},
    {'probabilities': {0: 0.5, 1: 0.5, 2: 0.5}},
])
def test_invalid_response_is_rejected(changes):
    with pytest.raises(ValueError, match='Invalid JEV response'):
        scoring.validate_answer(response(**changes))


def test_structured_inputs_keep_metadata_without_responsibilities():
    client = Mock(system_one=Mock(return_value=response()))
    jd = JobDescription(job_id='JD', skills=[], source_text='Build APIs.')
    result = scoring.score_relevance(document(), jd, client=client)
    assert result['document_id'] == 'CV_001'
    assert result['job_id'] == 'JD'
    assert result['provisional'] is True
    assert result['aggregation'] == 'whole_cv_jd'
    assert result['jev_score_100'] == 75
    assert json.loads(client.system_one.call_args.kwargs['state']['cv']) == [
        section.model_dump() for section in document().sections]


def test_technical_skills_and_raw_text_are_excluded():
    data = document().model_dump()
    data['text'] += '\nTECHNICAL SKILLS: SQL, Kubernetes\nRAW_ONLY'
    data['sections'].append({'section_id': 'CV_001:skills',
                             'section_name': 'technical_skills',
                             'content': 'SQL, Kubernetes'})
    client = Mock(system_one=Mock(return_value=response()))
    result = scoring.score_relevance(
        ResumeDocument.model_validate(data),
        JobDescription(job_id='JD', skills=[], source_text='Build APIs.'), client=client)
    request = client.system_one.call_args.kwargs
    assert 'Built Python services.' in request['state']['cv']
    for excluded in ('technical_skills', 'SQL', 'Kubernetes', 'RAW_ONLY'):
        assert excluded not in request['state']['cv']
    assert 'Do not evaluate technical-skill coverage' in request['questions']['experience_relevance'].instructions
    assert result['excluded_sections'] == ['technical_skills']
    assert data['sections'][-1]['content'] == 'SQL, Kubernetes'


@pytest.mark.parametrize('sections', [[], [
    {'section_id': 'CV_001:skills', 'section_name': 'technical_skills', 'content': 'SQL'},
]])
def test_no_eligible_sections_does_not_fall_back_to_raw_text(sections):
    data = document().model_dump()
    data['sections'] = sections
    client = Mock()
    with pytest.raises(ValueError, match='sections other than technical_skills'):
        scoring.score_relevance(ResumeDocument.model_validate(data),
                                JobDescription(job_id='JD', skills=[], source_text='Build APIs.'),
                                client=client)
    client.system_one.assert_not_called()


def test_jd_without_source_fails_before_api_call():
    client = Mock()
    with pytest.raises(ValueError, match='source_text'):
        scoring.score_relevance(document(), JobDescription(job_id='JD', skills=[]), client=client)
    client.system_one.assert_not_called()


def test_cli_writes_scores_and_refuses_overwrite(tmp_path, monkeypatch):
    resume_path, jd_path, output = [tmp_path / name for name in ('resume.json', 'jd.json', 'scores.json')]
    resume_path.write_text(document().model_dump_json())
    jd_path.write_text(JobDescription(job_id='JD', skills=[], source_text='Build APIs.').model_dump_json())
    client = Mock(system_one=Mock(return_value=response()))
    factory = Mock()
    factory.return_value.__enter__ = Mock(return_value=client)
    factory.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(scoring, 'create_jev_client', factory)
    monkeypatch.setattr('sys.argv', ['score_relevance', str(resume_path), str(jd_path), '--output', str(output)])
    scoring.main()
    saved = output.read_text()
    assert json.loads(saved)['relevance_scores']['jev_score_100'] == 75
    with pytest.raises(SystemExit) as error:
        scoring.main()
    assert error.value.code == 1
    assert output.read_text() == saved
    client.system_one.assert_called_once()
