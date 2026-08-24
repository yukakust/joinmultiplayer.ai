import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/build_gate5a3_design.py"
SPEC = importlib.util.spec_from_file_location("build_gate5a3_design", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Gate5A3DesignTests(unittest.TestCase):
    def setUp(self):
        self.design = json.loads((ROOT / "site/experiments/E005/gate-5a3-design-v0.1.json").read_text())

    def test_public_design_matches_builder(self):
        self.assertEqual(self.design, MODULE.build())
        self.assertEqual(self.design["status"], "locked_not_run")
        self.assertFalse(self.design["training_performed"])
        self.assertFalse(self.design["run_performed"])

    def test_semantic_contract_contains_meaning_and_provenance(self):
        cause = self.design["semantic_capsule_contract"]["cause"]
        safety = self.design["semantic_capsule_contract"]["safety"]
        self.assertIn("thermal rebound", cause["claim"])
        self.assertIn("Keep", safety["action"])
        self.assertEqual(cause["source"], "CAUSE-I")
        self.assertEqual(safety["source"], "SAFETY-I")

    def test_design_keeps_controls_and_marks_text_only_limit(self):
        conditions = set(self.design["conditions"])
        self.assertIn("instruct_question_alone", conditions)
        self.assertIn("instruct_cause_only", conditions)
        self.assertIn("instruct_safety_only", conditions)
        self.assertIn("instruct_semantic_oracle_pair", conditions)
        self.assertIn("parallel", self.design["plain_limit"]["en"])


if __name__ == "__main__":
    unittest.main()
