"""Run from the repo root: .venv/bin/python -m unittest improvement.tests.test_cv_improvement -v"""
import unittest

from langchain_core.documents import Document

from improvement.src.cv_improvement import CVImprovementPipeline, CVRecommendation, LLMImprovementResponse

CHUNK_TEXT = ("Built Python ETL pipelines integrating sales data, reducing manual processing time by approximately 80%. "
              "Developed reusable SQL queries in Amazon Redshift.")
CV_CHUNKS = [
    Document(page_content=CHUNK_TEXT, metadata={"chunk_id": "CV_001", "section_name": "work_experience",
                                                "source": "/Users/someone/cv.json", "candidate_id": "C1"}),
    Document(page_content="Created Tableau dashboards.", metadata={"chunk_id": "CV_002", "section_name": "work_experience"}),
]
SQL_BULLET = "Developed reusable SQL queries in Amazon Redshift."


class FakeEngine:
    """Returns scripted recommendations and records the evidence it was given."""

    def __init__(self, *recommendations):
        self.recommendations = list(recommendations)
        self.calls = []

    def generate(self, requirement, fit_label, gap_analysis, cv_evidence):
        self.calls.append(cv_evidence)
        return LLMImprovementResponse(recommendations=self.recommendations)


def rec(original=SQL_BULLET, improved="Wrote reusable Amazon Redshift SQL for recurring reporting.",
        source="CV_001", evidence=("CV_001",), question=None):
    return CVRecommendation(source_chunk_id=source, original_text=original, improved_text=improved,
                            explanation="x", evidence_ids=list(evidence), clarification_question=question)


def gap(fit_label="good_fit", status="assessed", cited=("CV_001",)):
    action = {"good_fit": "rewrite_existing_bullet", "potential_fit": "request_clarification",
              "no_fit": "flag_missing_evidence"}.get(fit_label, "review_retrieval")
    return {"requirement_id": "JD_001", "requirement": "SQL on AWS data warehouses.", "status": status,
            "fit_label": fit_label, "reasoning": "r", "competencies": [], "missing_evidence": [],
            "supporting_evidence": [{"chunk_id": c, "text": "t"} for c in cited], "improvement_action": action,
            "suggested_clarification": None}


def run(engine, *gaps):
    return CVImprovementPipeline(engine).generate(list(gaps), CV_CHUNKS)


class CVImprovementTests(unittest.TestCase):
    def test_rewrite_quoting_one_bullet_is_kept(self):
        [r] = run(FakeEngine(rec()), gap())
        self.assertEqual((r["status"], len(r["recommendations"])), ("generated", 1))

    def test_whitespace_differences_in_quote_accepted(self):
        [r] = run(FakeEngine(rec(original="Developed reusable SQL queries\n in  Amazon Redshift.")), gap())
        self.assertEqual(r["status"], "generated")

    def test_misquoted_original_dropped(self):
        [r] = run(FakeEngine(rec(original="Developed SQL queries in Snowflake.")), gap())
        self.assertEqual((r["status"], r["recommendations"]), ("review_needed", []))

    def test_invented_number_dropped(self):
        bad = rec(improved="Wrote 50 reusable Redshift SQL queries for recurring reporting.")
        kept = rec(original="Built Python ETL pipelines integrating sales data, reducing manual processing time "
                            "by approximately 80%.", improved="Cut manual processing ~80% with Python ETL pipelines.")
        [r] = run(FakeEngine(bad, kept), gap())
        self.assertEqual([x["improved_text"] for x in r["recommendations"]], [kept.improved_text])

    def test_unprovided_evidence_dropped_but_valid_kept(self):
        [r] = run(FakeEngine(rec(evidence=("CV_001", "CV_002")), rec()), gap())  # CV_002 not cited by the gap
        self.assertEqual(len(r["recommendations"]), 1)

    def test_no_fit_rewrite_dropped_question_kept(self):
        question = rec(original=None, improved=None, source=None, evidence=(), question="Have you used Terraform?")
        [r] = run(FakeEngine(rec(), question), gap("no_fit", cited=()))
        self.assertEqual(r["status"], "missing_evidence")
        self.assertEqual([x["clarification_question"] for x in r["recommendations"]], ["Have you used Terraform?"])

    def test_review_needed_gap_skipped(self):
        engine = FakeEngine(rec())
        [r] = run(engine, gap(None, status="review_needed"))
        self.assertEqual((r["status"], engine.calls), ("review_needed", []))

    def test_only_needed_fields_sent_to_llm(self):
        engine = FakeEngine(rec())
        run(engine, gap())
        self.assertEqual(set(engine.calls[0][0]), {"chunk_id", "text", "section_name"})


if __name__ == "__main__":
    unittest.main()
