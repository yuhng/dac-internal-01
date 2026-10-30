"""Rule-based parsing of resume text into the structured fields of data/schema.json."""

import re
from typing import Any

HEADINGS = {
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "employment": "experience",
    "work history": "experience",
    "project experience": "projects",
    "projects": "projects",
    "education": "education",
    "skills": "skills",
    "technical skills": "skills",
    "core skills": "skills",
    "certifications": "certifications",
    "certificates": "certifications",
    "summary": "summary",
    "profile": "summary",
    "professional summary": "summary",
    "objective": "summary",
}

HARD_SKILLS = (
    "A/B Testing", "Airflow", "AWS", "Azure", "BigQuery", "CI/CD", "Databricks", "dbt", "Docker", "ETL", "Excel",
    "FastAPI", "GCP", "Git", "Informatica", "Java", "JavaScript", "Kubernetes", "LangChain", "Looker",
    "Machine Learning", "Pandas", "Power BI", "PySpark", "Python", "React", "Snowflake", "Spark", "SQL", "Tableau",
    "TypeScript",
)
SOFT_SKILLS = (
    "Collaboration", "Communication", "Leadership", "Negotiation", "Presentation", "Problem Solving",
    "Project Management", "Stakeholder Management", "Teamwork",
)

_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
_DATE = rf"(?:{_MONTH}\s+)?\d{{4}}"
_DATE_RANGE = re.compile(
    rf"\(?\s*(?P<start>{_DATE})\s*[-–—]\s*(?P<end>{_DATE}|Present|Current|Now)\s*\)?$", re.IGNORECASE
)
_BULLET = re.compile(r"^[-•*]\s+")
_DEGREE = re.compile(
    r"(?<![\w.])(?:Bachelor(?:'s)?(?: of \w+)?|Master(?:'s)?(?: of \w+)?|Doctorate|Diploma|MBA|Ph\.?D\.?"
    r"|B\.?(?:Sc|A|Eng|Comp|Tech)\.?|M\.?(?:Sc|A|Eng|Tech)\.?)(?![\w])\.?(?:\s*\(Hons?\.?\)|\s*\(Honours\))?"
)
_TRAILING_YEAR = re.compile(r"[,\s]+(\d{4})$")


def _dedupe(items: list[str]) -> list[str]:
    unique: dict[str, str] = {}
    for item in items:
        unique.setdefault(item.casefold(), item)
    return list(unique.values())


def _split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        section = HEADINGS.get(line.strip().rstrip(":").casefold())
        if section:
            current = section
            sections.setdefault(current, [])
        elif current:
            sections[current].append(line)
    return sections


def _split_header(left: str) -> tuple[str, str | None]:
    """Returns (title, company) from `Company | Title` or `Title, Company`."""
    if "|" in left:
        company, title = (part.strip() for part in left.split("|", 1))
        return title, company or None
    if "," in left:
        title, company = (part.strip() for part in left.split(",", 1))
        return title, company or None
    return left, None


def _parse_experience(lines: list[str]) -> list[dict[str, Any]]:
    roles: list[dict[str, Any]] = []
    bullets: list[str] = []

    def finish_role() -> None:
        if roles:
            roles[-1]["description"] = "\n".join(bullets) or None
        bullets.clear()

    for line in lines:
        dates = None if _BULLET.match(line) else _DATE_RANGE.search(line)
        if dates:
            finish_role()
            title, company = _split_header(line[: dates.start()].strip(" |,-"))
            end = dates["end"]
            roles.append({
                "title": title,
                "company": company,
                "start_date": dates["start"],
                "end_date": None if end.casefold() in ("present", "current", "now") else end,
                "description": None,
            })
        elif _BULLET.match(line):
            bullets.append(_BULLET.sub("", line))
        elif bullets:
            bullets[-1] += f" {line}"
    finish_role()
    return roles


def _parse_education(lines: list[str]) -> list[dict[str, Any]]:
    entries = []
    for line in lines:
        if _BULLET.match(line):
            continue
        dates = _DATE_RANGE.search(line)
        main = (line[: dates.start()] if dates else line).split("|")[0].strip(" ,-")
        year_match = _TRAILING_YEAR.search(main)
        year = dates["end"][-4:] if dates else year_match and year_match[1]
        if year_match:
            main = main[: year_match.start()]

        degree = _DEGREE.search(main)
        if not degree:
            if dates:
                entries.append({"degree": main, "institution": None, "field_of_study": None, "graduation_year": None})
            continue

        institution = main[: degree.start()].strip(" ,-") or None
        field = re.sub(r"^(?:in|of)\s+", "", main[degree.end():].strip(" ,-")) or None
        if field and "," in field:
            field, rest = (part.strip() for part in field.split(",", 1))
            institution = institution or rest
        entries.append({
            "degree": degree[0],
            "institution": institution,
            "field_of_study": field,
            "graduation_year": int(year) if year and year.isdigit() else None,
        })
    return entries


def _split_items(value: str) -> list[str]:
    """Splits a comma list, treating `Python (Pandas, Polars)` as three items."""
    return [item.strip() for item in re.split(r"[,;()]", value) if item.strip()]


def _parse_skill_lines(lines: list[str]) -> tuple[list[str], list[str]]:
    skills: list[str] = []
    certifications: list[str] = []
    for line in lines:
        label, separator, value = line.partition(":")
        if separator and label.casefold().startswith("certif"):
            certifications += _split_items(value)
        else:
            skills += _split_items(value if separator else line)
    return skills, certifications


def _find_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    def pattern(term: str) -> str:
        return rf"(?<![a-z0-9]){re.escape(term).replace(r'\ ', '[ -]')}(?![a-z0-9])"

    return [term for term in terms if re.search(pattern(term), text, re.IGNORECASE)]


def parse_resume(text: str) -> dict[str, Any]:
    sections = _split_sections(text)
    listed_skills, skill_line_certifications = _parse_skill_lines(sections.get("skills", []))
    certifications = [
        item.strip()
        for line in sections.get("certifications", [])
        for item in _split_items(_BULLET.sub("", line))
    ]

    soft_skills = _find_terms(text, SOFT_SKILLS)
    soft_names = {skill.casefold() for skill in SOFT_SKILLS}
    hard_skills = _dedupe(
        [skill for skill in listed_skills if skill.casefold() not in soft_names] + _find_terms(text, HARD_SKILLS)
    )

    return {
        "work_experience": _parse_experience(sections.get("experience", [])),
        "education": _parse_education(sections.get("education", [])),
        "certifications": _dedupe(certifications + skill_line_certifications),
        "skills": _dedupe(hard_skills + soft_skills),
        "hard_skills": hard_skills,
        "soft_skills": soft_skills,
    }
