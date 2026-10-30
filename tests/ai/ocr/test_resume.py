from mycareerai.ai.ocr import parse_resume

PIPE_STYLE = """Sam Example
Email: sam@example.com
WORK EXPERIENCE
Acme Corp | Data Engineer Jun 2024 – Present
- Built Python pipelines processing 3TB+ of data and
improving reporting for regional teams.
- Presented findings, using strong communication.
Beta Ltd | Analyst Intern Jan 2023 — Dec 2023
- Designed Tableau dashboards
PROJECT EXPERIENCE
Side Project (Acme Corp) | Data Science Mar 2024 - Jun 2024
- Not a job
SKILLS
Programming: Python (Pandas, Polars), SQL
Cloud Platforms: AWS, GCP
Certification: dbt Fundamentals, IBM AI Engineering
EDUCATION
UOL BSc (Honours) Data Science | Graduate Aug 2021 – Aug 2024
- Relevant modules: Statistics
"""

COMMA_STYLE = """SKILLS
Excel, SQL, Communication
EXPERIENCE
Business Analyst, Harbourline Logistics (2023 – Present)
- Wrote SQL queries
EDUCATION
B.Sc. Business Analytics, National University of Singapore, 2022
"""


def test_parses_roles_and_joins_wrapped_bullets():
    roles = parse_resume(PIPE_STYLE)["work_experience"]
    assert [(r["company"], r["title"]) for r in roles] == [("Acme Corp", "Data Engineer"), ("Beta Ltd", "Analyst Intern")]
    assert roles[0]["start_date"] == "Jun 2024"
    assert roles[0]["end_date"] is None
    assert roles[1]["end_date"] == "Dec 2023"
    assert roles[0]["description"].split("\n")[0].endswith("improving reporting for regional teams.")


def test_projects_are_not_counted_as_jobs():
    assert "Side Project" not in str(parse_resume(PIPE_STYLE)["work_experience"])


def test_parses_education_with_institution_first():
    assert parse_resume(PIPE_STYLE)["education"] == [{
        "degree": "BSc (Honours)",
        "institution": "UOL",
        "field_of_study": "Data Science",
        "graduation_year": 2024,
    }]


def test_parses_education_with_degree_first():
    assert parse_resume(COMMA_STYLE)["education"] == [{
        "degree": "B.Sc.",
        "institution": "National University of Singapore",
        "field_of_study": "Business Analytics",
        "graduation_year": 2022,
    }]


def test_parses_title_before_company():
    role = parse_resume(COMMA_STYLE)["work_experience"][0]
    assert (role["title"], role["company"], role["start_date"]) == ("Business Analyst", "Harbourline Logistics", "2023")


def test_separates_skills_from_certifications():
    fields = parse_resume(PIPE_STYLE)
    assert fields["certifications"] == ["dbt Fundamentals", "IBM AI Engineering"]
    assert "dbt Fundamentals" not in fields["skills"]
    assert {"Python", "Pandas", "Polars", "SQL", "AWS", "GCP"} <= set(fields["hard_skills"])


def test_keeps_listed_skill_order_and_first_spelling():
    fields = parse_resume("SKILLS\nPython, pySpark, SQL\n")
    assert fields["hard_skills"] == ["Python", "pySpark", "SQL"]


def test_finds_skills_outside_the_skills_section():
    assert "Tableau" in parse_resume(PIPE_STYLE)["hard_skills"]


def test_classifies_soft_skills_and_keeps_them_in_skills():
    fields = parse_resume(COMMA_STYLE)
    assert fields["soft_skills"] == ["Communication"]
    assert "Communication" not in fields["hard_skills"]
    assert "Communication" in fields["skills"]


def test_does_not_match_skills_inside_other_words():
    fields = parse_resume("SKILLS\nJavaScript\nSUMMARY\nExcellent spreadsheets\n")
    assert "Java" not in fields["hard_skills"]
    assert "Excel" not in fields["hard_skills"]


def test_missing_sections_return_empty_lists():
    assert parse_resume("Just some text with no headings") == {
        "work_experience": [],
        "education": [],
        "certifications": [],
        "skills": [],
        "hard_skills": [],
        "soft_skills": [],
    }
