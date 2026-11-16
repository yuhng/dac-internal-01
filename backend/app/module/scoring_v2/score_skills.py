"""Score explicit skill coverage against a manually reviewed structured JD."""
from .prepare_evidence import SKILLS as SKILL_ALIASES
from .prepare_evidence import canonical_skill, skill_mentions


def score_skills(evidence, jd):
    print("Scoring Skills...")
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

