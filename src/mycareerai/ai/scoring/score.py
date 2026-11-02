"""Turns graded requirements into a fit score, and rates the CV on its own."""

import re
from dataclasses import dataclass

from ..ocr.resume import split_sections
from .match import Match

# Starting values, to be calibrated against labelled CV and job pairs.
FIT_WEIGHTS = {"Must-have skills": 65, "Preferred skills": 15, "Experience": 15, "Education": 5}
IMPACT_WEIGHT = 60
STRUCTURE_WEIGHT = 40

CAP_ANY_MISSING_MUST = 79
CAP_LOW_MUST_COVERAGE = 59
LOW_MUST_COVERAGE = 50

TARGET_QUANTIFIED_SHARE = 0.6
NO_BULLETS_IMPACT = 20
WEAK_PHRASE_PENALTY = 5
MIN_CV_WORDS = 150
MAX_CV_WORDS = 1100
LENGTH_PENALTY = 20

_BULLET = re.compile(r"^\s*[-•*]")
_WEAK_PHRASE = re.compile(r"\b(?:responsible for|worked on|helped with|(?:was|were) involved in|in charge of)\b", re.IGNORECASE)
_EXPECTED_SECTIONS = {
    "Summary": ("summary",),
    "Experience": ("experience",),
    "Education": ("education",),
    "Skills": ("skills",),
    "Projects or certifications": ("projects", "certifications"),
}


@dataclass(frozen=True)
class Part:
    label: str
    weight: int
    score: int
    detail: str


@dataclass(frozen=True)
class Fit:
    overall: int
    parts: tuple[Part, ...]
    # The limit that lowered the score, if one did.
    cap: int | None


@dataclass(frozen=True)
class Quality:
    score: int
    parts: tuple[Part, ...]
    bullets: int
    quantified: int
    weak_phrases: int
    missing_sections: tuple[str, ...]

# -------------------------------------- HELPERS -----------------------------------------------------------

def _mean_credit(matches: list[Match]) -> float:
    return 100 * sum(match.credit for match in matches) / len(matches)


def _category(match: Match) -> str:
    if match.requirement.kind == "experience":
        return "Experience"
    if match.requirement.kind == "education":
        return "Education"
    return "Must-have skills" if match.requirement.importance == "must" else "Preferred skills"


def _detail(label: str, matches: list[Match]) -> str:
    if label == "Experience":
        return matches[0].evidence or "No dated roles found"
    if label == "Education":
        return "Meets the stated level" if matches[0].credit == 1 else "Below the stated level"
    fully_met = sum(match.tier == "demonstrated" for match in matches)
    return f"{fully_met} of {len(matches)} shown in your work or projects"

# ------------------------------------- FUNCTIONS-----------------------------------------------------------

def score_fit(matches: list[Match]) -> Fit:
    scored = [match for match in matches if match.credit is not None]
    groups = {
        label: group
        for label in FIT_WEIGHTS
        if (group := [match for match in scored if _category(match) == label])
    }
    total_weight = sum(FIT_WEIGHTS[label] for label in groups)
    values = {label: _mean_credit(group) for label, group in groups.items()}
    raw = sum(values[label] * FIT_WEIGHTS[label] for label in groups) / total_weight
    overall = round(raw)

    must = groups.get("Must-have skills")
    cap = None
    if must and values["Must-have skills"] < LOW_MUST_COVERAGE:
        cap = CAP_LOW_MUST_COVERAGE
    elif any(match.requirement.importance == "must" and match.credit == 0 for match in scored):
        cap = CAP_ANY_MISSING_MUST

    parts = tuple(
        Part(label, round(FIT_WEIGHTS[label] / total_weight * 100), round(values[label]), _detail(label, group))
        for label, group in groups.items()
    )
    if cap is None or overall <= cap:
        return Fit(overall, parts, None)
    return Fit(cap, parts, cap)


def score_quality(cv: str) -> Quality:
    bullets = [line for line in cv.splitlines() if _BULLET.match(line)]
    quantified = sum(bool(re.search(r"\d", line)) for line in bullets)
    weak_phrases = sum(bool(_WEAK_PHRASE.search(line)) for line in cv.splitlines())
    impact = NO_BULLETS_IMPACT
    if bullets:
        share = min(100, round(quantified / len(bullets) / TARGET_QUANTIFIED_SHARE * 100))
        impact = max(0, share - weak_phrases * WEAK_PHRASE_PENALTY)

    present = split_sections(cv)
    missing = tuple(name for name, keys in _EXPECTED_SECTIONS.items() if not any(key in present for key in keys))
    structure = round((len(_EXPECTED_SECTIONS) - len(missing)) / len(_EXPECTED_SECTIONS) * 100)
    if not MIN_CV_WORDS <= len(cv.split()) <= MAX_CV_WORDS:
        structure = max(0, structure - LENGTH_PENALTY)

    parts = (
        Part(
            "Impact",
            IMPACT_WEIGHT,
            impact,
            f"{quantified} of {len(bullets)} bullet points quantified · {weak_phrases} weak phrase{'' if weak_phrases == 1 else 's'}",
        ),
        Part("Structure", STRUCTURE_WEIGHT, structure, f"Missing: {', '.join(missing)}" if missing else "All key sections present"),
    )
    score = round((impact * IMPACT_WEIGHT + structure * STRUCTURE_WEIGHT) / (IMPACT_WEIGHT + STRUCTURE_WEIGHT))
    return Quality(score, parts, len(bullets), quantified, weak_phrases, missing)
