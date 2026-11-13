import psycopg
import pytest
from dotenv import load_dotenv

from mycareerai.core.postgre.ingest import save_table

TEST_ID = "test-row-not-a-real-hash"


def record(**fields):
    return {
        "id": TEST_ID,
        "text": "",
        "email": None,
        "phone": None,
        "work_experience": [],
        "education": [],
        "certifications": [],
        "skills": [],
        "hard_skills": [],
        "soft_skills": [],
        "occupation": None,
        "seniority_level": None,
        "industry": None,
        "resume_format": None,
        "writing_style": None,
        **fields,
    }


@pytest.fixture
def connection():
    load_dotenv()
    try:
        connection = psycopg.connect(connect_timeout=2)
    except psycopg.OperationalError:
        pytest.skip("Postgres is not running; start it with `docker compose up -d`")
    yield connection
    # Deleting the document also deletes its resume row.
    connection.execute("DELETE FROM documents WHERE id = %s", (TEST_ID,))
    connection.commit()
    connection.close()


def test_saving_the_same_file_twice_keeps_one_row(connection):
    save_table(record(text="first"))
    save_table(record(text="second"))

    rows = connection.execute("SELECT row->>'text' FROM documents WHERE id = %s", (TEST_ID,)).fetchall()
    assert rows == [("second",)]


def test_resume_fields_are_stored_as_columns(connection):
    role = {"title": "Analyst", "company": "Acme", "start_date": "Jan 2020", "end_date": None, "description": None}
    save_table(record(email="sam@example.com", skills=["Python", "SQL"], work_experience=[role]))
    save_table(record(email="new@example.com", skills=["Python", "SQL"], work_experience=[role]))

    rows = connection.execute(
        "SELECT email, skills, work_experience FROM resumes WHERE document_id = %s", (TEST_ID,)
    ).fetchall()
    assert rows == [("new@example.com", ["Python", "SQL"], [role])]
