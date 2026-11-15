"""Score explicit skill coverage against a manually reviewed structured JD."""
import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from backend.app.schema.schema import ResumeDocument, StrictModel

from .prepare_evidence import SKILLS as SKILL_ALIASES
from .prepare_evidence import canonical_skill, prepare_evidence, skill_mentions


class SkillRequirement(StrictModel):
    requirement_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    importance: Literal["required", "preferred", "unspecified"]
    source_quote: str | None = Field(default=None, min_length=1)


class JobDescription(StrictModel):
    job_id: str = Field(min_length=1)
    skills: list[SkillRequirement]
    source_text: str | None = Field(default=None, min_length=1)
    review_status: Literal["pending", "approved", "needs_review"] = "pending"
    parsing_warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_requirements(self):
        ids, skills = set(), set()
        for requirement in self.skills:
            if self.source_text is not None:
                if not requirement.source_quote or requirement.source_quote not in self.source_text:
                    raise ValueError(f"Skill {requirement.name!r}: source_quote must be an exact excerpt of source_text")
                name = " ".join(requirement.name.split()).casefold()
                quote = " ".join(requirement.source_quote.split()).casefold()
                if not name or name not in quote:
                    raise ValueError(f"Skill name must appear in its source_quote: {requirement.name!r}")
            skill = canonical_skill(requirement.name).casefold()
            if requirement.requirement_id in ids or skill in skills:
                raise ValueError("JD requirement IDs and canonical skills must be unique")
            ids.add(requirement.requirement_id)
            skills.add(skill)
        return self


def score_skills(evidence, jd):
    results = []
    for requirement in jd.skills:
        skill = canonical_skill(requirement.name)
        matches = [
            {**mention, "evidence_id": source["evidence_id"],
             "original_text": source["original_text"], "text": source["text"]}
            for source in evidence["skill_sources"]
            for mention in skill_mentions(source["text"], [requirement.name])
        ]
        sources = sorted({match["evidence_id"] for match in matches})
        results.append({"requirement_id": requirement.requirement_id, "skill": skill,
                        "importance": requirement.importance, "matched": bool(sources),
                        "jd_name": requirement.name,
                        "matching_method": "exact_name_with_known_aliases" if skill in SKILL_ALIASES
                        else "exact_name",
                        "aliases_used": [alias for alias in SKILL_ALIASES.get(skill, [])
                                         if alias.casefold() != requirement.name.strip().casefold()],
                        "matches": matches,
                        "evidence_ids": sources,
                        "finding": "explicit_mention_found" if sources else "not_evidenced_in_cv"})
    coverage = {}
    for importance in ("required", "preferred", "unspecified"):
        group = [item for item in results if item["importance"] == importance]
        count = sum(item["matched"] for item in group)
        coverage[importance] = {"matched": count, "requested": len(group),
                               "percent": round(100 * count / len(group), 2) if group else None}
    return {"scoring_version": "skills-2", "job_id": jd.job_id,
            "document_id": evidence["document_id"],
            "document_version": evidence["document_version"],
            "provisional": evidence["review_status"] != "approved" or jd.review_status != "approved",
            "coverage": coverage, "skills": results,
            "warnings": evidence["warnings"] + jd.parsing_warnings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resume", type=Path)
    parser.add_argument("jd", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("Output already exists; choose a new filename")
        document = ResumeDocument.model_validate_json(args.resume.read_text(encoding="utf-8"))
        jd = JobDescription.model_validate_json(args.jd.read_text(encoding="utf-8"))
        evidence = prepare_evidence(document)
        result = {"evidence": evidence, "skill_scores": score_skills(evidence, jd)}
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(result, output, ensure_ascii=False, indent=2)
            output.write("\n")
    except (ValueError, OSError) as error:
        parser.exit(1, f"Scoring failed: {error}\n")
    print(f"Saved skill scores and evidence: {args.output}")


if __name__ == "__main__":
    main()
