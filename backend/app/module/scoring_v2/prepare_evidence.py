"""Prepare versioned resume evidence without changing the extraction JSON."""
import re

from backend.app.schema.schema import EntriesSection, ResumeDocument

SKILLS = {
    "Python": ["Python"], "SQL": ["SQL"], "PySpark": ["PySpark"],
    "pandas": ["pandas"], "Polars": ["Polars"],
    "PostgreSQL": ["PostgreSQL", "Postgres"], "MySQL": ["MySQL"],
    "BigQuery": ["BigQuery"], "Tableau": ["Tableau"], "Power BI": ["Power BI", "PowerBI"],
    "Looker Studio": ["Looker Studio"], "Informatica": ["Informatica"],
    "Docker": ["Docker"], "GitHub Actions": ["GitHub Actions"],
    "scikit-learn": ["scikit-learn", "sklearn"], "LangChain": ["LangChain"],
    "Hugging Face": ["Hugging Face", "HuggingFace"],
    "AWS": ["AWS", "Amazon Web Services"], "GCP": ["GCP", "Google Cloud Platform"],
    "Azure": ["Azure"], "Databricks": ["Databricks", "Azure Databricks"],
    "FastAPI": ["FastAPI"], "React": ["React", "React.js"],
    "RAG": ["RAG", "retrieval-augmented generation"], "OCR": ["OCR"],
    "Delta Lake": ["Delta Lake"], "asyncio": ["asyncio"],
    "dbt": ["dbt"], "Airflow": ["Airflow", "Apache Airflow"],
    "MLflow": ["MLflow"], "Terraform": ["Terraform"],
}


def clean_line(text):
    text = text.translate(str.maketrans("", "", "\u200b\ufeff\u00ad"))
    text = re.sub(r"^\s*(?:[-•●▪‣*]|\d+[.)])\s*", "", text)
    return " ".join(text.split())


def canonical_skill(name):
    key = " ".join(name.split()).casefold()
    for canonical, aliases in SKILLS.items():
        if key in {alias.casefold() for alias in aliases}:
            return canonical
    if not key:
        raise ValueError("Skill name must be nonempty")
    return " ".join(name.split())


def skill_mentions(text, names=None):
    selected = SKILLS if names is None else {
        canonical_skill(name): SKILLS.get(canonical_skill(name), [name.strip()])
        for name in names
    }
    for canonical, aliases in selected.items():
        pattern = r"(?<![\w+#.])(?:" + "|".join(
            re.escape(alias) for alias in sorted(aliases, key=len, reverse=True)
        ) + r")(?![\w+#])"
        for match in re.finditer(pattern, text, re.IGNORECASE):
            yield {"skill": canonical, "mention": match.group(),
                   "start": match.start(), "end": match.end()}


def prepare_evidence(document: ResumeDocument):
    bullets, mentions, sources = [], [], []
    warnings = list(document.parsing_warnings)
    for section in document.sections:
        records = []
        if isinstance(section, EntriesSection) and section.section_name in {
            "work_experience", "project_experience"
        }:
            for entry in section.entries:
                count = 0
                for source_line, original in enumerate(entry.content.splitlines(), 1):
                    cleaned = clean_line(original)
                    if not cleaned:
                        continue
                    count += 1
                    record = {
                        "bullet_id": f"{entry.entry_id}:bullet:{count:03d}",
                        "entry_id": entry.entry_id, "section_id": section.section_id,
                        "project_name": entry.project_name, "job_title": entry.job_title,
                        "company": entry.company, "source_line": source_line,
                        "original_text": original, "text": cleaned,
                    }
                    bullets.append(record)
                    records.append((record["bullet_id"], original, cleaned))
        elif section.section_name == "technical_skills" and not isinstance(section, EntriesSection):
            for line_number, original in enumerate(section.content.splitlines(), 1):
                if re.match(r"\s*certifications?\s*:", original, re.IGNORECASE):
                    continue
                records.append((f"{section.section_id}:line:{line_number:03d}",
                                original, clean_line(original)))
        for evidence_id, original, cleaned in records:
            sources.append({"evidence_id": evidence_id, "section_id": section.section_id,
                            "original_text": original, "text": cleaned})
            for mention in skill_mentions(cleaned):
                mentions.append({**mention, "evidence_id": evidence_id,
                                 "section_id": section.section_id,
                                 "original_text": original, "text": cleaned})
    warnings.append("Each nonempty entry line is treated as one bullet; verify OCR line grouping.")
    warnings.append("Skill matching uses known aliases or exact JD names; negation and proficiency are not assessed.")
    return {
        "document_id": document.document_id, "document_version": document.document_version,
        "review_status": document.metadata.review_status,
        "bullets": bullets, "skill_mentions": mentions, "skill_sources": sources, "warnings": warnings,
    }
