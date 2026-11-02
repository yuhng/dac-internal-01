from mycareerai.ai.scoring import parse_job
from mycareerai.ai.scoring.job import degree_levels

JD = """Northwind is hiring an analyst to work with Salesforce data.

Responsibilities:
- Build dashboards in Tableau or Power BI
- Automate reports using Python

Requirements:
- 2+ years of experience in data analysis
- Strong SQL and Excel skills
- Python, pandas, or Polars experience
- Bachelor's degree in a numerate subject, Master's preferred
- Excellent communication
- Knowledge of retail pricing models
- Familiarity with Snowflake is a plus

Nice to have:
- Docker
"""


def by_text(job):
    return {requirement.text: requirement for requirement in job.requirements}


def test_required_section_gives_must_haves():
    found = by_text(parse_job(JD))
    assert found["SQL"].importance == "must"
    assert found["Excel"].importance == "must"


def test_preferred_wording_and_sections_are_not_must_haves():
    found = by_text(parse_job(JD))
    assert found["Snowflake"].importance == "preferred"
    assert found["Docker"].importance == "preferred"


def test_responsibilities_and_intro_are_preferred():
    found = by_text(parse_job(JD))
    assert found["Tableau or Power BI"].importance == "preferred"
    assert found["Salesforce"].importance == "preferred"


def test_a_skill_in_both_sections_keeps_the_higher_importance():
    found = by_text(parse_job("Responsibilities:\n- Use Docker\nRequirements:\n- Docker\n"))
    assert found["Docker"].importance == "must"


def test_alternatives_are_one_requirement():
    found = by_text(parse_job(JD))
    assert found["Tableau or Power BI"].skills == ("Tableau", "Power BI")


def test_a_list_with_or_is_one_requirement():
    assert by_text(parse_job("Requirements:\n- SQL, Python, or Java\n"))["SQL or Python or Java"]


def test_a_list_without_or_is_separate_requirements():
    assert set(by_text(parse_job("Requirements:\n- SQL, Python and Java\n"))) == {"SQL", "Python", "Java"}


def test_soft_skills_are_never_must_haves():
    assert by_text(parse_job(JD))["Communication"].importance == "preferred"


def test_reads_years_and_degree():
    requirements = parse_job(JD).requirements
    assert next(r for r in requirements if r.kind == "experience").min_years == 2
    assert next(r for r in requirements if r.kind == "education").degree_level == 2


def test_the_lowest_degree_named_is_the_requirement():
    assert min(degree_levels("Diploma or degree")) == 1


def test_abbreviations_in_ordinary_text_are_not_degrees():
    assert degree_levels("work with the ba team and ma colleagues") == []
    assert degree_levels("MBA") == [3]


def test_lines_with_no_known_skill_are_kept_as_free_text():
    requirement = by_text(parse_job(JD))["Knowledge of retail pricing models"]
    assert requirement.skills == ()


def test_without_headings_everything_is_a_must_have():
    job = parse_job("Python and SQL developer wanted.")
    assert not job.has_sections
    assert {requirement.importance for requirement in job.requirements} == {"must"}
