"""Run from the repo root: .venv/bin/python -m unittest improvement.tests.test_gap_analysis -v"""
import json
import unittest
from pathlib import Path

from improvement.src.gap_analysis import CompetencyAssessment, GapAnalysisPipeline, LLMAssessment

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class FakeAssessor:
    """Returns a scripted LLMAssessment (or raises a scripted Exception) and records the evidence it saw."""

    def __init__(self, reply=None):
        self.reply = reply
        self.calls = []

    def assess(self, requirement, evidence):
        self.calls.append(evidence)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def hit(chunk_id, text, score, flat=False):
    """Evidence in RerankingPipeline's real shape (chunk_id inside metadata) unless flat=True."""
    base = {"text": text, "cross_encoder_score": score, "bi_encoder_score": 0.5, "rank": 1}
    return {**base, "chunk_id": chunk_id} if flat else {**base, "metadata": {"chunk_id": chunk_id}}


def requirement(jd_text, *evidence, jd_id="JD_001"):
    return {"jd_chunk_id": jd_id, "jd_text": jd_text, "cv_evidence": list(evidence)}


def comp(name, status, *ids):
    return CompetencyAssessment(competency=name, status=status, evidence_ids=list(ids), explanation="x")


def assessment(label, cited, competencies=(), missing=()):
    return LLMAssessment(fit_label=label, reasoning="Assessed from cited chunks.", competencies=list(competencies),
                         missing_evidence=list(missing), supporting_chunk_ids=list(cited),
                         suggested_clarification=None)


ETL_REQ = "Develop scalable ETL pipelines using Python and SQL."
CV_ETL = hit("CV_001", "Built Python ETL pipelines integrating regional sales data.", 0.94)
CV_SQL = hit("CV_002", "Developed SQL queries in Amazon Redshift.", 0.86)


def run(reply, *items):
    assessor = FakeAssessor(reply)
    return GapAnalysisPipeline(assessor=assessor).analyze(list(items)), assessor


class FitTests(unittest.TestCase):
    def test_good_fit(self):
        reply = assessment("good_fit", ["CV_001", "CV_002"],
                           [comp("Python", "demonstrated", "CV_001"), comp("SQL", "demonstrated", "CV_002")])
        [r], _ = run(reply, requirement(ETL_REQ, CV_ETL, CV_SQL))
        self.assertEqual((r["status"], r["fit_label"], r["improvement_action"]),
                         ("assessed", "good_fit", "rewrite_existing_bullet"))
        self.assertEqual([e["chunk_id"] for e in r["supporting_evidence"]], ["CV_001", "CV_002"])

    def test_potential_fit(self):
        reply = assessment("potential_fit", ["CV_001"], [comp("Python", "demonstrated", "CV_001"),
                                                         comp("SQL", "not_demonstrated")], ["SQL evidence"])
        [r], _ = run(reply, requirement(ETL_REQ, CV_ETL, CV_SQL))
        self.assertEqual((r["fit_label"], r["improvement_action"]), ("potential_fit", "request_clarification"))
        self.assertEqual([e["chunk_id"] for e in r["supporting_evidence"]], ["CV_001"])  # uncited CV_002 dropped

    def test_no_fit(self):
        [r], _ = run(assessment("no_fit", [], [comp("Terraform", "not_demonstrated")]),
                     requirement("Familiarity with Terraform.", hit("CV_009", "Created Tableau dashboards.", 0.12)))
        self.assertEqual((r["fit_label"], r["improvement_action"]), ("no_fit", "flag_missing_evidence"))
        self.assertEqual(r["supporting_evidence"], [])


class EvidenceInputTests(unittest.TestCase):
    def test_empty_retrieval_is_review_not_no_fit(self):
        [r], assessor = run(None, requirement(ETL_REQ))
        self.assertEqual((r["status"], r["fit_label"], r["improvement_action"]),
                         ("review_needed", None, "review_retrieval"))
        self.assertEqual(assessor.calls, [])

    def test_flat_chunk_id_accepted(self):
        [r], _ = run(assessment("potential_fit", ["CV_001"]), requirement(ETL_REQ, hit("CV_001", "t", 0.9, flat=True)))
        self.assertEqual(r["supporting_evidence"][0]["chunk_id"], "CV_001")

    def test_missing_chunk_id_skipped_and_duplicates_collapsed(self):
        orphan = {"text": "Orphan", "metadata": {}}
        _, assessor = run(assessment("no_fit", []), requirement(ETL_REQ, orphan, CV_ETL, CV_ETL))
        self.assertEqual([e["chunk_id"] for e in assessor.calls[0]], ["CV_001"])


class ValidationTests(unittest.TestCase):
    def assertReview(self, reply, *evidence):
        [r], _ = run(reply, requirement(ETL_REQ, *evidence))
        self.assertEqual((r["status"], r["fit_label"]), ("review_needed", None))

    def test_unknown_citation(self):
        self.assertReview(assessment("potential_fit", ["CV_999"]), CV_ETL)

    def test_good_fit_with_partial_competency_downgraded(self):
        reply = assessment("good_fit", ["CV_001"], [comp("Python", "demonstrated", "CV_001"),
                                                    comp("SQL", "partial", "CV_001")])
        [r], _ = run(reply, requirement(ETL_REQ, CV_ETL))
        self.assertEqual((r["status"], r["fit_label"], r["improvement_action"]),
                         ("assessed", "potential_fit", "request_clarification"))
        self.assertIn("SQL", r["missing_evidence"])
        self.assertIn("SQL", r["suggested_clarification"])

    def test_good_fit_with_nothing_demonstrated_becomes_no_fit(self):
        reply = assessment("good_fit", ["CV_001"], [comp("Terraform", "not_demonstrated")])
        [r], _ = run(reply, requirement(ETL_REQ, CV_ETL))
        self.assertEqual((r["fit_label"], r["improvement_action"]), ("no_fit", "flag_missing_evidence"))

    def test_good_fit_without_citations(self):
        self.assertReview(assessment("good_fit", []), CV_ETL)

    def test_demonstrated_without_evidence(self):
        self.assertReview(assessment("potential_fit", ["CV_001"], [comp("SQL", "demonstrated")]), CV_ETL)

    def test_assessor_error(self):
        self.assertReview(RuntimeError("503"), CV_ETL)


class RealShapeTests(unittest.TestCase):
    def test_example_input_runs(self):
        items = json.loads((EXAMPLES / "gap_input.json").read_text())
        results, assessor = run(assessment("no_fit", []), *items)
        self.assertEqual(len(results), len(items))
        self.assertEqual([r["status"] for r in results], ["assessed", "review_needed"])  # JD_002 has no evidence
        self.assertTrue(all(e["chunk_id"] for call in assessor.calls for e in call))


if __name__ == "__main__":
    unittest.main()
