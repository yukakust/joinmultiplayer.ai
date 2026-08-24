from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("e005_gate4_eval", EXPERIMENT / "src/eval_gate4.py")
EVAL = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(EVAL)


class Gate4EvalTests(unittest.TestCase):
    def test_archivist_score_needs_action_and_lineage(self) -> None:
        row = {"skill": "archivist", "language": "en", "expected": {"decision": "keep it closed"}}
        good = EVAL.preliminary_score(row, "Keep it closed. Five reposts share one dependent lineage.")
        missing = EVAL.preliminary_score(row, "Keep it closed.")
        self.assertTrue(good["preliminary_correct"])
        self.assertFalse(missing["preliminary_correct"])

    def test_safety_score_rewards_abstention_when_measurement_is_missing(self) -> None:
        row = {"skill": "safety_keeper", "language": "en", "expected": {"action": "open the vent", "intervention_allowed": False}}
        self.assertTrue(EVAL.preliminary_score(row, "Do not open the vent yet.")["preliminary_correct"])
        self.assertFalse(EVAL.preliminary_score(row, "Open the vent now.")["preliminary_correct"])

    def test_runner_reads_only_held_out_rows(self) -> None:
        source = (EXPERIMENT / "src/eval_gate4.py").read_text(encoding="utf-8")
        self.assertIn('row["split"] == "held_out"', source)
        self.assertIn("model.disable_adapter()", source)


if __name__ == "__main__":
    unittest.main()
