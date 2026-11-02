from datetime import date

import pytest
from fastapi.testclient import TestClient

from mycareerai.ai.scoring import ScoringError, analyze
from mycareerai.ai.scoring import match as match_module
from mycareerai.ai.scoring.job import Requirement
from mycareerai.ai.scoring.match import match_requirement, read_cv
from mycareerai.main import app

TODAY = date(2026, 11, 1)

JD = """Responsibilities:
- Build dashboards in Tableau or Power BI

Requirements:
- 2+ years of experience in data analysis
- Strong SQL and Python skills
- Bachelor's degree

Nice to have:
- Snowflake
"""

CV = """SUMMARY
Analyst.

EXPERIENCE
Analyst, Harbourline (Jan 2023 – Dec 2024)
- Wrote SQL queries that cut reporting time by 30%
- Built Python scripts to clean
survey data
Data Intern, Brightside (Jun 2022 – Dec 2022)
- Built Tableau dashboards for 12 clients

PROJECTS
Pricing Model | Personal Jan 2024 – Mar 2024
- Trained a Snowflake model

EDUCATION
BSc Business Analytics, National University of Singapore, 2022

SKILLS
SQL, Python, Tableau, Snowflake
"""


def run(jd=JD, cv=CV, **kwargs):
    return analyze("Analyst", "Northwind", jd, cv, today=TODAY, **kwargs)


def requirement(result, text):
    return next(item for item in result["requirements"] if item["text"] == text)


def test_a_fully_evidenced_cv_scores_strong():
    result = run()
    assert result["overall"] == 100
    assert result["band"] == "strong"
    assert result["missing"] == []


def test_evidence_quotes_the_whole_wrapped_bullet():
    assert requirement(run(), "Python")["evidence"] == "Built Python scripts to clean survey data"


def test_a_blank_line_ends_a_bullet():
    cv = "EXPERIENCE\nAnalyst, Acme (2020 – 2024)\n- Wrote SQL reports\n\nStray note\n"
    assert read_cv(cv, TODAY).evidence[1:] == ("Wrote SQL reports", "Stray note")


def test_project_bullets_count_as_evidence():
    assert requirement(run(), "Snowflake")["tier"] == "demonstrated"


def test_a_skill_only_in_the_skills_section_gets_partial_credit():
    cv = CV.replace("- Wrote SQL queries that cut reporting time by 30%\n", "")
    item = requirement(run(cv=cv), "SQL")
    assert (item["tier"], item["credit"]) == ("listed", 0.6)


def test_a_related_skill_is_still_reported_as_missing():
    cv = "EXPERIENCE\nAnalyst, Acme (2020 – 2024)\n- Built Power BI reports\n"
    result = run("Requirements:\n- Tableau\n- SQL\n", cv)
    assert requirement(result, "Tableau")["tier"] == "related"
    assert "Tableau" in result["missing"]


def test_any_missing_must_have_prevents_a_strong_score():
    result = run(JD.replace("SQL and Python", "SQL, Python, Tableau, Snowflake and Docker"))
    assert requirement(result, "Docker")["credit"] == 0
    assert result["overall"] == result["cap"] == 79


def test_low_must_have_coverage_caps_the_score():
    result = run("Requirements:\n- SQL\n- Java\n- Docker\n- Kubernetes\n- Azure\nNice to have:\n- Python\n", CV)
    assert result["overall"] <= 59


def test_unrelated_job_scores_weak():
    assert run("Requirements:\n- Java\n- Docker\n- Kubernetes\n- Figma\n", CV)["band"] == "weak"


def test_keyword_stuffing_earns_listed_credit_at_most():
    jd = "Requirements:\n- Java\n- Docker\n- SQL\n"
    plain = run(jd)
    stuffed = run(jd, CV + "Java, Docker\n")
    assert stuffed["overall"] > plain["overall"]
    assert requirement(stuffed, "Java")["credit"] == 0.6


@pytest.mark.parametrize(
    "line",
    ["- Wrote SQL queries that cut reporting time by 30%\n", "- Built Tableau dashboards for 12 clients\n"],
)
def test_deleting_evidence_never_raises_the_score(line):
    assert run(cv=CV.replace(line, ""))["overall"] <= run()["overall"]


def test_the_score_is_repeatable():
    first, second = run(), run()
    assert (first["overall"], first["requirements"]) == (second["overall"], second["requirements"])


def test_cv_quality_does_not_change_the_match_score():
    weak_wording = CV.replace("Wrote SQL queries", "Was responsible for SQL queries")
    assert run(cv=weak_wording)["overall"] == run()["overall"]
    assert run(cv=weak_wording)["quality"]["score"] < run()["quality"]["score"]


def test_weights_are_rescaled_when_a_category_is_absent():
    result = run("Requirements:\n- SQL\nNice to have:\n- Docker\n")
    assert [part["weight"] for part in result["parts"]] == [81, 19]


def test_overlapping_roles_are_not_counted_twice():
    cv = "EXPERIENCE\nAnalyst, A (Jan 2020 – Dec 2020)\nAnalyst, B (Jun 2020 – Dec 2021)\n"
    assert read_cv(cv, TODAY).months_of_experience == 24


def test_a_current_role_runs_to_today():
    assert read_cv("EXPERIENCE\nAnalyst, A (Oct 2026 – Present)\n", TODAY).months_of_experience == 2


def test_too_little_experience_gets_partial_credit():
    item = next(i for i in run("Requirements:\n- SQL\n- 10+ years of experience\n")["requirements"] if i["kind"] == "experience")
    assert item["tier"] == "partial"
    assert item["credit"] == pytest.approx(31 / 120)


def test_a_lower_degree_gets_partial_credit():
    item = next(i for i in run("Requirements:\n- SQL\n- PhD\n")["requirements"] if i["kind"] == "education")
    assert (item["tier"], item["credit"]) == ("partial", 0.5)


def test_free_text_requirements_are_left_out_without_a_model():
    result = run("Requirements:\n- SQL\n- Knowledge of retail pricing models\n")
    assert requirement(result, "Knowledge of retail pricing models")["tier"] == "unassessed"
    assert result["overall"] == 100
    assert any("could not be assessed" in reason for reason in result["confidence"]["reasons"])


def test_confidence_falls_when_little_can_be_assessed():
    assert run("SQL developer wanted.")["confidence"]["level"] == "low"
    assert run()["confidence"]["level"] == "high"


def test_a_job_with_no_known_skills_is_rejected():
    with pytest.raises(ScoringError, match="No recognised skills"):
        run("Gardener needed to prune roses and tend orchards.")


class FakeEncoder:
    version = "fake-1"

    def __init__(self, similar_to: str):
        self.similar_to = similar_to

    def encode(self, texts):
        return [[1.0, 0.0], *([1.0, 0.0] if self.similar_to in text else [0.0, 1.0] for text in texts[1:])]


def test_an_encoder_can_satisfy_a_free_text_requirement():
    result = run("Requirements:\n- SQL\n- Knowledge of retail pricing models\n", encoder=FakeEncoder("Pricing Model"))
    item = requirement(result, "Knowledge of retail pricing models")
    assert (item["tier"], item["method"]) == ("implied", "semantic")
    assert result["engineVersion"] == "rules-1+fake-1"


def test_an_encoder_cannot_turn_a_different_tool_into_a_full_match():
    item = Requirement("Java", "skill", "must", ("Java",))
    match = match_requirement(item, read_cv(CV, TODAY), FakeEncoder("Wrote SQL"))
    assert match.tier == "related"
    assert match.credit == match_module.CREDIT["related"]


def test_a_low_similarity_is_ignored():
    class Unrelated(FakeEncoder):
        def encode(self, texts):
            return [[1.0, 0.0], *([0.0, 1.0] for _ in texts[1:])]

    match = match_requirement(Requirement("Java", "skill", "must", ("Java",)), read_cv(CV, TODAY), Unrelated(""))
    assert match.tier == "missing"


client = TestClient(app)


def test_api_returns_the_analysis():
    response = client.post("/api/scoring/analyze", json={"title": "Analyst", "company": "", "jd": JD, "cv": CV})
    assert response.status_code == 200
    assert response.json()["engineVersion"] == "rules-1"


def test_api_explains_an_unscorable_job():
    response = client.post("/api/scoring/analyze", json={"jd": "Gardener needed.", "cv": CV})
    assert response.status_code == 422
    assert "No recognised skills" in response.json()["detail"]


def test_api_rejects_oversized_text():
    assert client.post("/api/scoring/analyze", json={"jd": "x" * 50_001, "cv": CV}).status_code == 422
