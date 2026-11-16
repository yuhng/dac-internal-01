from unittest.mock import Mock

import pytest

from backend.app.module.scoring_v2.overall_score import calculate_overall_score, score_application
from backend.app.schema.schema import JobDescription

from test_relevance import document as summary_only_document, response


def document():
    # Skills are only read from experience entries and technical_skills, not the summary.
    cv = summary_only_document().model_dump()
    cv["text"] += "\nSkills: Python"
    cv["sections"].append({"section_id": "CV_001:technical_skills",
                           "section_name": "technical_skills", "content": "Skills: Python"})
    return type(summary_only_document()).model_validate(cv)


def jd(skills=(), review_status="approved"):
    text = "Requires Python. Nice to have Docker."
    quotes = {"Python": "Requires Python", "Docker": "Nice to have Docker"}
    importance = {"Python": "required", "Docker": "preferred"}
    return JobDescription(
        job_id="JD_001", source_text=text, review_status=review_status,
        skills=[{"requirement_id": f"R{i}", "name": name, "importance": importance[name],
                 "source_quote": quotes[name]} for i, name in enumerate(skills, 1)],
    )


def jev_client():
    return Mock(system_one=Mock(return_value=response()))  # jev_score_100 == 75


def test_application_weights_skills_and_relevance():
    # Python is in the CV (matched), Docker is not: skill = (0.60*100 + 0.25*0) / 0.85.
    result = score_application(document(), jd(["Python", "Docker"]), jev_client=jev_client())
    overall = result["overall"]
    assert overall["skill_score_100"] == round(60 / 0.85, 2)
    assert overall["relevance_score_100"] == 75
    assert overall["overall_score_100"] == round(0.40 * 60 / 0.85 + 0.60 * 75, 2)
    assert overall["method"] == "weighted_skills_and_relevance"
    assert overall["provisional"] is False
    assert result["skill_scores"]["skills"][0]["matched"] is True
    assert result["relevance_scores"]["jev_score_100"] == 75


def test_jd_without_skills_falls_back_to_relevance_and_is_provisional():
    overall = score_application(document(), jd([]), jev_client=jev_client())["overall"]
    assert overall["skill_score_100"] is None
    assert overall["overall_score_100"] == 75
    assert overall["method"] == "relevance_only"
    assert overall["provisional"] is True


def test_unreviewed_jd_marks_combined_score_provisional():
    overall = score_application(document(), jd(["Python"], review_status="pending"),
                                jev_client=jev_client())["overall"]
    assert overall["method"] == "weighted_skills_and_relevance"
    assert overall["provisional"] is True


def test_missing_relevance_leaves_overall_unscored():
    result = score_application(document(), jd(["Python"]), jev_client=jev_client())
    relevance = {**result["relevance_scores"], "jev_score_100": None}
    overall = calculate_overall_score(result["skill_scores"], relevance)
    assert overall["overall_score_100"] is None
    assert overall["method"] is None


@pytest.mark.parametrize("key", ["job_id", "document_id", "document_version"])
def test_scores_from_different_pairs_are_rejected(key):
    result = score_application(document(), jd(["Python"]), jev_client=jev_client())
    relevance = {**result["relevance_scores"], key: "OTHER"}
    with pytest.raises(ValueError, match=key):
        calculate_overall_score(result["skill_scores"], relevance)
