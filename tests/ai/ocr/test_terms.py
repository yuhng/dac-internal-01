import pytest
import yaml

from mycareerai.ai.ocr import parse_resume
from mycareerai.ai.ocr import terms_loader as terms_module
from mycareerai.ai.ocr.resume import HARD_SKILLS, SOFT_SKILLS
from mycareerai.ai.ocr.terms_loader import TERMS_DIR, load_terms


def forms(terms):
    return [form.casefold() for term in terms for form in term.forms]


@pytest.mark.parametrize("terms", [HARD_SKILLS, SOFT_SKILLS], ids=["hard", "soft"])
def test_every_spelling_belongs_to_one_term(terms):
    assert len(forms(terms)) == len(set(forms(terms)))


def test_related_terms_exist():
    names = {term.name for term in HARD_SKILLS}
    assert {name for term in HARD_SKILLS for name in term.related} <= names


def test_no_term_is_both_hard_and_soft():
    assert not set(forms(HARD_SKILLS)) & set(forms(SOFT_SKILLS))


def test_every_heading_belongs_to_one_section():
    headings = [h.casefold() for group in yaml.safe_load((TERMS_DIR / "headings.yaml").read_text()).values() for h in group]
    assert len(headings) == len(set(headings))


@pytest.mark.parametrize("file_name", ["hard_skills.yaml", "soft_skills.yaml"])
def test_terms_only_use_known_keys(file_name):
    for entry in yaml.safe_load((TERMS_DIR / file_name).read_text()):
        assert set(entry) <= {"name", "aliases", "case_sensitive", "related"}, entry


@pytest.mark.parametrize(
    ("text", "skill"),
    [
        ("Built dashboards in React", "React"),
        ("Built apps in React.js", "React"),
        ("Reported in Microsoft Excel", "Excel"),
        ("Ran jobs on Apache Spark", "Spark"),
        ("Deployed to Google Cloud Platform", "GCP"),
        ("Deployed on k8s", "Kubernetes"),
        ("Built reports in PowerBI", "Power BI"),
    ],
)
def test_finds_terms_and_aliases(text, skill):
    assert parse_resume(text)["hard_skills"] == [skill]


@pytest.mark.parametrize(
    ("text", "skill"),
    [
        ("Trained to react to incidents", "React"),
        ("Known to excel at reporting", "Excel"),
        ("Helped spark new ideas", "Spark"),
        ("Wrote JavaScript", "Java"),
        ("Used PySpark", "Spark"),
    ],
)
def test_does_not_match_ordinary_words_or_longer_terms(text, skill):
    assert skill not in parse_resume(text)["hard_skills"]


def test_listed_aliases_use_the_terms_name():
    fields = parse_resume("SKILLS\nReactJS, Amazon Web Services, react, Julia\n")
    assert fields["hard_skills"] == ["React", "AWS", "Julia"]


def test_loads_aliases_from_a_terms_file(monkeypatch, tmp_path):
    monkeypatch.setattr(terms_module, "TERMS_DIR", tmp_path)
    (tmp_path / "soft.yaml").write_text("- name: Teamwork\n  aliases: [Team Player]\n")

    term = load_terms("soft.yaml")[0]

    assert term.name == "Teamwork"
    assert term.pattern.search("a team-player")
