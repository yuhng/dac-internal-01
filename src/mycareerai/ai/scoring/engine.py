"""Runs a CV and job description through the scoring steps and builds the API response."""

from dataclasses import asdict
from datetime import date
from typing import Any
from uuid import uuid4

from .encoder import Encoder
from .job import parse_job
from .match import Match, match_requirement, read_cv
from .score import Fit, Quality, score_fit, score_quality

ENGINE_VERSION = "rules-1"
MIN_CONFIDENT_REQUIREMENTS = 3
MAX_LISTED_IN_RECOMMENDATION = 4

METHODOLOGY = [
    "**Requirements**: each job description is split into must-have and preferred requirements, using its headings and wording.",
    "**Evidence**: a skill used in a work or project bullet earns 100% credit, one that only appears elsewhere earns 60%, and a closely related skill earns 40%.",
    "**Score**: must-have skills count for 65%, preferred skills 15%, experience 15% and education 5%. Categories the job doesn't mention are left out, and the rest are scaled up.",
    "**Limits**: a missing must-have limits the score to 79, and under 50% must-have coverage limits it to 59.",
    "**CV quality** is shown separately and does not affect the match score.",
    "These weights are starting values and have not yet been validated against hiring outcomes. Treat the score as a guide, not a prediction.",
]


class ScoringError(Exception):
    """A CV and job description could not be scored. The message is safe to show to the user."""

# -------------------------------------- HELPERS -----------------------------------------------------------

def _band(score: int) -> tuple[str, str]:
    if score >= 80:
        return "strong", "Strong match"
    if score >= 60:
        return "good", "Good match"
    if score >= 40:
        return "fair", "Fair match"
    return "weak", "Weak match"


def _names(matches: list[Match]) -> str:
    names = [match.requirement.text for match in matches[:MAX_LISTED_IN_RECOMMENDATION]]
    return ", ".join(names[:-1]) + f" and {names[-1]}" if len(names) > 1 else names[0]


def _skills_with(matches: list[Match], *tiers: str) -> list[Match]:
    return [
        match for match in matches
        if match.requirement.kind == "skill" and match.requirement.skills and match.tier in tiers
    ]


def _recommendations(matches: list[Match], quality: Quality) -> list[dict[str, str]]:
    must = [match for match in matches if match.requirement.importance == "must"]
    preferred = [match for match in matches if match.requirement.importance == "preferred"]
    items: list[dict[str, str]] = []

    def recommend(severity: str, text: str) -> None:
        items.append({"severity": severity, "text": text})

    if missing := _skills_with(must, "missing", "related"):
        recommend("high", f"Required but not shown: **{_names(missing)}**. Add evidence if you have it.")
    if listed := _skills_with(must, "listed"):
        recommend("high", f"Mentioned but not shown in use: **{_names(listed)}**. Add it to a work or project bullet.")
    if gaps := _skills_with(preferred, "missing", "related"):
        recommend("med", f"Useful but not mentioned: **{_names(gaps)}**. Add it if you have it.")
    if quality.bullets and quality.quantified / quality.bullets < 0.6:
        recommend("med", f"Quantify more achievements. Only {quality.quantified} of {quality.bullets} bullet points include a number, percentage or scale.")
    if quality.weak_phrases:
        recommend("med", f"Replace {quality.weak_phrases} passive phrase{'' if quality.weak_phrases == 1 else 's'} such as “responsible for” with action verbs.")
    if quality.missing_sections:
        recommend("low", f"Consider adding a section for {quality.missing_sections[0].lower()}.")
    if not items:
        recommend("low", "Your application is well aligned. Tailor your opening line to the company before sending.")
    return items


def _confidence(matches: list[Match], has_sections: bool, months_of_experience: int) -> dict[str, Any]:
    scored = [match for match in matches if match.credit is not None]
    unassessed = len(matches) - len(scored)
    reasons = []
    if not has_sections:
        reasons.append("The job description has no recognised headings, so must-haves may be mislabelled.")
    if len(scored) < MIN_CONFIDENT_REQUIREMENTS:
        reasons.append(f"Only {len(scored)} requirement{'' if len(scored) == 1 else 's'} could be assessed.")
    if unassessed:
        reasons.append(f"{unassessed} requirement{'' if unassessed == 1 else 's'} could not be assessed and {'was' if unassessed == 1 else 'were'} left out of the score.")
    if not months_of_experience:
        reasons.append("No dated roles were found in your CV, so its layout may not have been read correctly.")
    level = "high" if not reasons else "medium" if len(reasons) == 1 else "low"
    return {"level": level, "reasons": reasons}


def _requirement(match: Match) -> dict[str, Any]:
    return {
        "text": match.requirement.text,
        "kind": match.requirement.kind,
        "importance": match.requirement.importance,
        "tier": match.tier,
        "credit": match.credit,
        "evidence": match.evidence,
        "method": match.method,
    }


def _build_response(
    title: str, company: str, jd: str, cv: str, matches: list[Match], fit: Fit, quality: Quality, confidence: dict[str, Any], version: str,
) -> dict[str, Any]:
    band, band_label = _band(fit.overall)
    return {
        "title": title,
        "company": company,
        "jd": jd,
        "cv": cv,
        "id": str(uuid4()),
        "overall": fit.overall,
        "band": band,
        "bandLabel": band_label,
        "parts": [asdict(part) for part in fit.parts],
        "matched": [match.requirement.text for match in _skills_with(matches, "demonstrated", "implied", "listed")],
        "missing": [match.requirement.text for match in _skills_with(matches, "missing", "related")],
        "recommendations": _recommendations(matches, quality),
        "methodology": METHODOLOGY,
        "requirements": [_requirement(match) for match in matches],
        "quality": {"score": quality.score, "parts": [asdict(part) for part in quality.parts]},
        "confidence": confidence,
        "cap": fit.cap,
        "engineVersion": version,
    }

# ------------------------------------- FUNCTIONS-----------------------------------------------------------

def analyze(
    title: str, company: str, jd: str, cv: str, *, encoder: Encoder | None = None, today: date | None = None,
) -> dict[str, Any]:
    job = parse_job(jd)
    profile = read_cv(cv, today)
    matches = [match_requirement(requirement, profile, encoder) for requirement in job.requirements]
    if not any(match.requirement.kind == "skill" and match.credit is not None for match in matches):
        raise ScoringError("No recognised skills were found in that job description, so it can't be scored yet.")

    version = f"{ENGINE_VERSION}+{encoder.version}" if encoder else ENGINE_VERSION
    confidence = _confidence(matches, job.has_sections, profile.months_of_experience)
    return _build_response(title, company, jd, cv, matches, score_fit(matches), score_quality(cv), confidence, version)
