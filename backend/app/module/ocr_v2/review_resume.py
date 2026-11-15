"""Print a human review checklist for extracted resume JSON; never auto-approve."""
import argparse
import re
from pathlib import Path

if __package__:
    from ...schema.schema import EntriesSection, ResumeDocument
else:
    from backend.app.schema.schema import EntriesSection, ResumeDocument


def review_report(document: ResumeDocument) -> str:
    lines = [f"Resume review: {document.document_id} (version {document.document_version})",
             f"Status: {document.metadata.review_status}",
             f"Extraction: {document.metadata.collection_method}", ""]
    issues = list(document.parsing_warnings)
    seen_contents = set()
    jobs = projects = bullet_lines = 0
    for section in document.sections:
        lines.append(f"SECTION: {section.section_name} [{section.section_id}]")
        if isinstance(section, EntriesSection):
            if not section.entries:
                issues.append(f"Empty entries section: {section.section_id}")
            if section.section_name == "work_experience":
                jobs += len(section.entries)
            elif section.section_name == "project_experience":
                projects += len(section.entries)
            for entry in section.entries:
                lines.extend([
                    f"  Entry: {entry.entry_id}",
                    f"  Title: {entry.job_title or '[missing]'}",
                    f"  Company: {entry.company or '[missing]'}",
                    f"  Dates: {entry.start_date or '[missing]'} → {entry.end_date or '[missing]'}",
                ])
                if section.section_name == "work_experience":
                    for field in ("job_title", "company", "start_date", "end_date"):
                        if not getattr(entry, field):
                            issues.append(f"Missing {field}: {entry.entry_id}")
                # Counts are candidates, not verified source bullet counts.
                content_lines = [line.strip() for line in entry.content.splitlines() if line.strip()]
                bullet_lines += len(content_lines)
                if not content_lines:
                    issues.append(f"Empty content: {entry.entry_id}")
                normalized = " ".join(entry.content.split()).casefold()
                if normalized and normalized in seen_contents:
                    issues.append(f"Repeated entry content; verify duplication: {entry.entry_id}")
                if normalized:
                    seen_contents.add(normalized)
                lines.extend(f"    {i}. {text}" for i, text in enumerate(content_lines, 1))
                numbers = re.findall(r"\d[\d,.]*(?:\s*%|\+)?", entry.content)
                if numbers:
                    lines.append("  Numbers to verify: " + ", ".join(numbers))
        else:
            lines.append(section.content or "[empty]")
            if not section.content.strip():
                issues.append(f"Empty content: {section.section_id}")
        lines.append("")
    lines.extend([
        f"SUMMARY: {jobs} jobs; {projects} projects; {bullet_lines} nonempty entry lines",
        "Entry lines are bullet candidates only; compare against the source PDF.",
        "", "ISSUES TO REVIEW:",
        *([f"- {issue}" for issue in issues] or ["- No heuristic issues found; source accuracy is unverified."]),
        "", "MANUAL SOURCE CHECK:",
        "[ ] Every page and section is represented.",
        "[ ] Every bullet appears once under the correct role or project.",
        "[ ] Employers, titles, dates, numbers and technical terms match the PDF.",
        "[ ] Full text includes contact details and all original sections.",
        "[ ] All parsing warnings have been resolved.",
        "", "This report does not change review_status or approve the document.",
    ])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_file", type=Path)
    args = parser.parse_args()
    try:
        document = ResumeDocument.model_validate_json(args.json_file.read_text(encoding="utf-8"))
    except (ValueError, OSError) as error:
        parser.exit(1, f"Cannot review resume: {error}\n")
    print(review_report(document), end="")


if __name__ == "__main__":
    main()
