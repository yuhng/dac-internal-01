"""Run from the repo root: .venv/bin/python -m unittest improvement.tests.test_usage -v"""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

from improvement.src import usage
from improvement.src.gap_analysis import EvidenceAssessor, LLMAssessment


def fake_response(prompt=1000, completion=200, cached=400, model="gpt-4o-mini-2024-07-18"):
    parsed = LLMAssessment(fit_label="no_fit", reasoning="r", competencies=[], missing_evidence=[],
                           supporting_chunk_ids=[], suggested_clarification=None)
    return NS(model=model, choices=[NS(message=NS(parsed=parsed))],
              usage=NS(prompt_tokens=prompt, completion_tokens=completion,
                       prompt_tokens_details=NS(cached_tokens=cached)))


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.log = Path(tempfile.mkdtemp()) / "usage.jsonl"
        patcher = mock.patch.object(usage, "LOG_PATH", self.log)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_assessor_records_each_call(self):
        client = NS(chat=NS(completions=NS(parse=lambda **_: fake_response())))
        assessor = EvidenceAssessor(client=client)
        assessor.assess("req", [])
        assessor.assess("req", [])
        entries = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(len(entries), 2)
        self.assertEqual((entries[0]["input_tokens"], entries[0]["cached_input_tokens"]), (1000, 400))
        self.assertAlmostEqual(entries[0]["estimated_cost_usd"], (600 * 0.15 + 400 * 0.075 + 200 * 0.60) / 1e6)

    def test_summarize_cost_and_totals(self):
        e = {"timestamp": "2026-11-13T10:00:00+00:00", "model": "gpt-4o-mini-2024-07-18",
             "input_tokens": 1_000_000, "cached_input_tokens": 400_000, "output_tokens": 100_000}
        r = usage.summarize([e, {**e, "model": "mystery-model"}])
        m = r["by_model"]["gpt-4o-mini-2024-07-18"]
        self.assertAlmostEqual(m["estimated_cost_usd"], 0.6 * 0.15 + 0.4 * 0.075 + 0.1 * 0.60)  # 0.18
        self.assertIsNone(r["by_model"]["mystery-model"]["estimated_cost_usd"])
        self.assertEqual(r["estimated_cost_usd"], m["estimated_cost_usd"])
        self.assertEqual(r["by_day"]["2026-11-13"]["requests"], 2)

    def test_gpt4o_not_priced_as_mini(self):
        totals = {"input_tokens": 1_000_000, "cached_input_tokens": 0, "output_tokens": 0}
        self.assertEqual(usage.estimate_cost("gpt-4o-2024-08-06", totals), 2.5)

    def test_empty_log(self):
        self.assertEqual(usage.summarize([])["requests"], 0)


if __name__ == "__main__":
    unittest.main()
