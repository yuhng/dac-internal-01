"""Combine skill coverage and experience relevance into one overall score."""
from .prepare_evidence import prepare_evidence
from .score_relevance import score_relevance
from .score_skills import score_skills


def calculate_overall_score(skill_scores, relevance_scores):

    # Checks
    for key in ("job_id", "document_id", "document_version"):
        if skill_scores[key] != relevance_scores[key]:
            raise ValueError(f"Score inputs disagree on {key}")

    weights = {
        "required": 0.60,
        "preferred": 0.25,
        "unspecified": 0.15,
    }

    available = [
        (weights[group], skill_scores["coverage"][group]["percent"])
        for group in weights
        if skill_scores["coverage"][group]["requested"] > 0
    ]

    skill_score = (
        sum(weight * percent for weight, percent in available)
        / sum(weight for weight, _ in available)
        if available else None
    )

    relevance_score = relevance_scores["jev_score_100"]

    # Without relevance, a skills-only score is just keyword counting, so leave it unscored.
    if relevance_score is None:
        overall_score, method = None, None
    elif skill_score is not None:
        overall_score = 0.40 * skill_score + 0.60 * relevance_score
        method = "weighted_skills_and_relevance"
    else:
        # No skill requirements extracted from the JD: score on relevance alone, and say so.
        overall_score, method = relevance_score, "relevance_only"

    return {
        "skill_score_100": (
            round(skill_score, 2) if skill_score is not None else None
        ),
        "relevance_score_100": relevance_score,
        "overall_score_100": (
            round(overall_score, 2) if overall_score is not None else None
        ),
        "method": method,
        "provisional": (
            skill_scores["provisional"]
            or relevance_scores["provisional"]
            or method == "relevance_only"
        ),
    }

def score_application(document, jd, *, jev_client=None):
    """Run both scorers on one CV-JD pair and combine them."""
    skill_scores = score_skills(prepare_evidence(document), jd)
    relevance_scores = score_relevance(document, jd, client=jev_client)
    return {
        "skill_scores": skill_scores,
        "relevance_scores": relevance_scores,
        "overall": calculate_overall_score(skill_scores, relevance_scores),
    }
