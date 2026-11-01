"""Loads the headings and skill vocabularies kept in terms/."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

TERMS_DIR = Path(__file__).parent / "terms"


@dataclass(frozen=True)
class Term:
    name: str
    forms: tuple[str, ...]
    pattern: re.Pattern[str]

# -------------------------------------- HELPERS -----------------------------------------------------------

def _read(file_name: str) -> Any:
    return yaml.safe_load((TERMS_DIR / file_name).read_text())


def _build_pattern(forms: tuple[str, ...], case_sensitive: bool) -> re.Pattern[str]:
    alternatives = "|".join(re.escape(form).replace(r"\ ", "[ -]") for form in forms)
    return re.compile(
        rf"(?<![A-Za-z0-9])(?:{alternatives})(?![A-Za-z0-9])",
        0 if case_sensitive else re.IGNORECASE,
    )
# ------------------------------------- FUNCTIONS-----------------------------------------------------------

def load_terms(file_name: str) -> tuple[Term, ...]:
    terms = []
    for entry in _read(file_name):
        forms = (entry["name"], *entry.get("aliases", ()))
        terms.append(Term(entry["name"], forms, _build_pattern(forms, entry.get("case_sensitive", False))))
    return tuple(terms)


def load_headings(file_name: str = "headings.yaml") -> dict[str, str]:
    return {heading.casefold(): section for section, headings in _read(file_name).items() for heading in headings}


def canonical_names(terms: tuple[Term, ...]) -> dict[str, str]:
    """Maps every casefolded form of a term to the term's name."""
    return {form.casefold(): term.name for term in terms for form in term.forms}
