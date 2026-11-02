"""Rule-based parsing of a job description into a checklist of requirements."""

import re
from dataclasses import dataclass
from typing import Literal

from ..ocr.resume import HARD_SKILLS, SOFT_SKILLS
from ..ocr.terms_loader import load_headings

Importance = Literal["must", "preferred"]
Kind = Literal["skill", "experience", "education"]

JOB_HEADINGS = load_headings("job_headings.yaml")
SOFT_NAMES = frozenset(term.name for term in SOFT_SKILLS)

_BULLET = re.compile(r"^[-•*]\s+")
_PREFERRED = re.compile(
    r"\b(?:a plus|a bonus|bonus|nice to have|preferred|preferable|desirable|advantage|advantageous|ideally)\b",
    re.IGNORECASE,
)
_YEARS = re.compile(r"(\d+)\s*(?:\+|plus)?\s*(?:(?:-|–|to)\s*\d+\s*)?(?:years?|yrs?)\b", re.IGNORECASE)
_ALTERNATIVE_GAP = re.compile(r"\s*(?:,\s*)?(?:(?:and/)?or\b|/)\s*", re.IGNORECASE)
_COMMA_GAP = re.compile(r"\s*,\s*")
# Abbreviations are case sensitive, so "ma" and "ba" inside ordinary text can't count as degrees.
_DEGREE_LEVELS = (
    (4, re.compile(r"\b(?i:ph\.?d|doctorate)\b")),
    (3, re.compile(r"\b(?i:master(?:'s|s)?)\b|\bMBA\b|\bM\.?(?:Sc|Eng|Tech|A)\b")),
    (2, re.compile(r"\b(?i:bachelor(?:'s|s)?|degree)\b|\bB\.?(?:Sc|Eng|Comp|Tech|A)\b")),
    (1, re.compile(r"\b(?i:diploma)\b")),
)
MIN_FREE_TEXT_WORDS = 3


@dataclass(frozen=True)
class Requirement:
    text: str
    kind: Kind
    importance: Importance
    # Any one of these satisfies the requirement. Empty when it names no known skill.
    skills: tuple[str, ...] = ()
    min_years: int | None = None
    degree_level: int | None = None


@dataclass(frozen=True)
class JobProfile:
    requirements: tuple[Requirement, ...]
    has_sections: bool

# -------------------------------------- HELPERS -----------------------------------------------------------

def _heading(line: str) -> str | None:
    return JOB_HEADINGS.get(line.strip().rstrip(":").replace("’", "'").casefold())


def _find_skills(line: str) -> list[tuple[str, ...]]:
    """Groups the skills in a line, so `Tableau or Power BI` is one requirement and `SQL, Excel` is two."""
    spans = sorted(
        (match.start(), match.end(), term.name)
        for term in (*HARD_SKILLS, *SOFT_SKILLS)
        for match in term.pattern.finditer(line)
    )
    groups: list[list[str]] = []
    run: list[str] = []
    is_alternative = False

    def finish_run() -> None:
        nonlocal is_alternative
        groups.extend([run.copy()] if is_alternative else [[name] for name in run])
        run.clear()
        is_alternative = False

    previous_end = 0
    for start, end, name in spans:
        gap = line[previous_end:start]
        if _ALTERNATIVE_GAP.fullmatch(gap):
            is_alternative = bool(run)
        elif not _COMMA_GAP.fullmatch(gap):
            finish_run()
        run.append(name)
        previous_end = end
    finish_run()
    return [tuple(dict.fromkeys(group)) for group in groups]


def _importance(section: str | None, line: str, has_sections: bool) -> Importance:
    if _PREFERRED.search(line) or section in ("preferred", "responsibilities"):
        return "preferred"
    # Text before the first heading is usually about the company, so it can't set a must-have.
    return "preferred" if has_sections and section is None else "must"


def _rank(importance: Importance) -> int:
    return 1 if importance == "must" else 0

# ------------------------------------- FUNCTIONS-----------------------------------------------------------

def degree_levels(text: str) -> list[int]:
    return [level for level, pattern in _DEGREE_LEVELS if pattern.search(text)]


def parse_job(text: str) -> JobProfile:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    has_sections = any(_heading(line) for line in lines)

    found: dict[object, Requirement] = {}
    years: Requirement | None = None
    degree: Requirement | None = None

    def add(key: object, requirement: Requirement) -> None:
        current = found.get(key)
        if not current or _rank(requirement.importance) > _rank(current.importance):
            found[key] = requirement

    section = None
    for raw_line in lines:
        if heading := _heading(raw_line):
            section = heading
            continue
        line = _BULLET.sub("", raw_line)
        importance = _importance(section, line, has_sections)
        skills = _find_skills(line)

        for group in skills:
            is_soft = SOFT_NAMES.issuperset(group)
            # Few CVs state soft skills outright, so a missing one can't count as a missing must-have.
            add(group, Requirement(" or ".join(group), "skill", "preferred" if is_soft else importance, group))

        if section == "responsibilities":
            continue

        min_years = _YEARS.search(line)
        if min_years:
            candidate = Requirement(line, "experience", importance, min_years=int(min_years[1]))
            if not years or (_rank(candidate.importance), candidate.min_years) > (_rank(years.importance), years.min_years):
                years = candidate

        levels = degree_levels(line)
        if levels and (not degree or _rank(importance) > _rank(degree.importance)):
            degree = Requirement(line, "education", importance, degree_level=min(levels))

        is_free_text = not (skills or min_years or levels) and section and len(line.split()) >= MIN_FREE_TEXT_WORDS
        if is_free_text:
            add(line.casefold(), Requirement(line, "skill", importance))

    extras = [requirement for requirement in (years, degree) if requirement]
    return JobProfile((*found.values(), *extras), has_sections)
