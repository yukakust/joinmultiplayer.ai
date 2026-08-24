import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "experiments/E005-signal-in-the-swarm/src"
sys.path.insert(0, str(SRC))
SPEC = importlib.util.spec_from_file_location("build_gate5a2_exam", SRC / "build_gate5a2_exam.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Gate5A2DesignTests(unittest.TestCase):
    def test_new_exam_is_balanced_and_locked(self):
        exam = MODULE.build()
        self.assertEqual(exam["status"], "locked_not_run")
        self.assertEqual(len(exam["questions"]), 24)
        self.assertEqual(sum(row["language"] == "en" for row in exam["questions"]), 12)
        self.assertEqual(sum(row["language"] == "ru" for row in exam["questions"]), 12)
        self.assertEqual(len({row["question"] for row in exam["questions"]}), 24)

    def test_design_requires_human_language_and_missing_capsule_controls(self):
        design = json.loads((ROOT / "site/experiments/E005/gate-5a2-design-v0.1.json").read_text(encoding="utf-8"))
        self.assertEqual(design["status"], "frozen_before_run")
        self.assertIn("Do not show JSON", design["output_rule"]["en"])
        self.assertIn("cause capsule only", design["conditions"])
        self.assertIn("safety capsule only", design["conditions"])
        self.assertGreater(design["pass_rule"]["actual_pair_complete_at_least"], design["pass_rule"]["each_missing_capsule_complete_at_most"])


if __name__ == "__main__":
    unittest.main()
