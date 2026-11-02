"""Grades each job requirement against evidence in a CV."""

import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from ..ocr import parse_resume
from ..ocr.resume import HARD_SKILLS, SOFT_SKILLS, evidence_lines
from .encoder import Encoder
from .job import Requirement, degree_levels

Tier = Literal["demonstrated", "implied", "listed", "related", "partial", "missing", "unassessed"]

CREDIT: dict[Tier, float] = {"demonstrated": 1.0, "implied": 0.8, "listed": 0.6, "related": 0.4, "missing": 0.0}
# A lower qualification than the job asks for, or some of the years.
PARTIAL_DEGREE_CREDIT = 0.5
# Placeholders. Each model needs its own values, set against labelled pairs before it is switched on.
IMPLIED_SIMILARITY = 0.7
RELATED_SIMILARITY = 0.55

_TERMS = {term.name: term for term in (*HARD_SKILLS, *SOFT_SKILLS)}
_RELATED: dict[str, set[str]] = {}
for _term in HARD_SKILLS:
    for _name in _term.related:
        _RELATED.setdefault(_term.name, set()).add(_name)
        _RELATED.setdefault(_name, set()).add(_term.name)

_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
_DATE = re.compile(r"(?:(?P<month>[A-Za-z]{3})[a-z]*\.?\s+)?(?P<year>\d{4})")


@dataclass(frozen=True)
class CvProfile:
    text: str
    evidence: tuple[str, ...]
    months_of_experience: int
    degree_level: int | None


@dataclass(frozen=True)
class Match:
    requirement: Requirement
    tier: Tier
    # None when the requirement could not be assessed, so it does not count towards the score.
    credit: float | None
    evidence: str | None = None
    method: Literal["exact", "semantic"] | None = None

# -------------------------------------- HELPERS -----------------------------------------------------------

def _to_month(value: str | None, *, is_end: bool, today: date) -> int | None:
    """Returns the months since year 0. A year alone covers the whole of that year."""
    if value is None:
        return today.year * 12 + today.month if is_end else None
    match = _DATE.fullmatch(value.strip())
    if not match:
        return None
    month = match["month"]
    if month and month.casefold() in _MONTHS:
        return int(match["year"]) * 12 + _MONTHS.index(month.casefold()) + 1
    return int(match["year"]) * 12 + (12 if is_end else 1)


def _months_of_experience(roles: list[dict[str, Any]], today: date) -> int:
    """Totals the time covered by any role, so roles held at once are not counted twice."""
    ranges = []
    for role in roles:
        start = _to_month(role["start_date"], is_end=False, today=today)
        end = _to_month(role["end_date"], is_end=True, today=today)
        if start is not None and end is not None and end >= start:
            ranges.append((start, end))

    total = 0
    covered_to = None
    for start, end in sorted(ranges):
        first = start if covered_to is None else max(start, covered_to + 1)
        if end >= first:
            total += end - first + 1
            covered_to = end
    return total


def _find_line(name: str, lines: list[str] | tuple[str, ...]) -> str | None:
    return next((line for line in lines if _TERMS[name].pattern.search(line)), None)


def _exact(requirement: Requirement, cv: CvProfile) -> Match:
    lines = cv.text.splitlines()
    for name in requirement.skills:
        if line := _find_line(name, cv.evidence):
            return Match(requirement, "demonstrated", CREDIT["demonstrated"], line, "exact")
    for name in requirement.skills:
        if line := _find_line(name, lines):
            return Match(requirement, "listed", CREDIT["listed"], line, "exact")
    for name in requirement.skills:
        for related in sorted(_RELATED.get(name, ())):
            if line := _find_line(related, (*cv.evidence, *lines)):
                return Match(requirement, "related", CREDIT["related"], line, "exact")
    return Match(requirement, "missing", CREDIT["missing"])


def _names_another_skill(requirement: Requirement, line: str) -> bool:
    """Embeddings rate different tools as similar, so these two can only ever be related."""
    return any(term.name not in requirement.skills and term.pattern.search(line) for term in HARD_SKILLS)


def _semantic(requirement: Requirement, cv: CvProfile, encoder: Encoder) -> Match | None:
    if not cv.evidence:
        return None
    query, *vectors = encoder.encode([requirement.text, *cv.evidence])
    similarity, line = max(
        (sum(a * b for a, b in zip(query, vector)), line) for vector, line in zip(vectors, cv.evidence)
    )
    if similarity >= IMPLIED_SIMILARITY:
        tier: Tier = "related" if requirement.skills and _names_another_skill(requirement, line) else "implied"
    elif similarity >= RELATED_SIMILARITY:
        tier = "related"
    else:
        return None
    return Match(requirement, tier, CREDIT[tier], line, "semantic")


def _match_skill(requirement: Requirement, cv: CvProfile, encoder: Encoder | None) -> Match:
    if not requirement.skills and not encoder:
        return Match(requirement, "unassessed", None)

    best = _exact(requirement, cv) if requirement.skills else Match(requirement, "missing", CREDIT["missing"])
    if encoder and best.tier != "demonstrated":
        semantic = _semantic(requirement, cv, encoder)
        if semantic and semantic.credit > best.credit:
            return semantic
    return best


def _match_experience(requirement: Requirement, cv: CvProfile) -> Match:
    needed = requirement.min_years * 12
    if not needed or cv.months_of_experience >= needed:
        return Match(requirement, "demonstrated", 1.0, _describe_years(cv), "exact")
    if not cv.months_of_experience:
        return Match(requirement, "missing", 0.0)
    return Match(requirement, "partial", cv.months_of_experience / needed, _describe_years(cv), "exact")


def _describe_years(cv: CvProfile) -> str:
    return f"About {cv.months_of_experience / 12:.1f} years across dated roles"


def _match_education(requirement: Requirement, cv: CvProfile) -> Match:
    if cv.degree_level is None:
        return Match(requirement, "missing", 0.0)
    if cv.degree_level >= requirement.degree_level:
        return Match(requirement, "demonstrated", 1.0, method="exact")
    return Match(requirement, "partial", PARTIAL_DEGREE_CREDIT, method="exact")

# ------------------------------------- FUNCTIONS-----------------------------------------------------------

def read_cv(text: str, today: date | None = None) -> CvProfile:
    fields = parse_resume(text)
    levels = [level for entry in fields["education"] for level in degree_levels(entry["degree"])]
    return CvProfile(
        text=text,
        evidence=tuple(evidence_lines(text)),
        months_of_experience=_months_of_experience(fields["work_experience"], today or date.today()),
        degree_level=max(levels, default=None),
    )


def match_requirement(requirement: Requirement, cv: CvProfile, encoder: Encoder | None = None) -> Match:
    if requirement.kind == "experience":
        return _match_experience(requirement, cv)
    if requirement.kind == "education":
        return _match_education(requirement, cv)
    return _match_skill(requirement, cv, encoder)
