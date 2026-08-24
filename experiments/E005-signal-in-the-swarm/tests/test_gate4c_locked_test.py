from __future__ import annotations

import collections
import importlib.util
import json
import sys
import unittest
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/build_gate4c_locked_test.py"
PUBLIC = ROOT / "site/experiments/E005/gate-4c-locked-test-v0.1.json"
LESSONS = ROOT / "site/experiments/E005/gate-4c-lessons-v0.1.json"
SPEC = importlib.util.spec_from_file_location("build_gate4c_locked_test", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Gate4CLockedTestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = MODULE.build()
        cls.rows = cls.payload["questions"]
        cls.lessons = json.loads(LESSONS.read_text(encoding="utf-8"))["lessons"]

    def test_exam_is_balanced_unique_and_not_run(self):
        self.assertEqual(self.payload["status"], "locked_not_run")
        self.assertTrue(self.payload["training_not_started_at_freeze"])
        self.assertEqual(len(self.rows), 48)
        self.assertEqual(len({row["prompt"] for row in self.rows}), 48)
        self.assertEqual(collections.Counter((row["skill"], row["language"]) for row in self.rows), {
            ("source_work", "en"): 12,
            ("source_work", "ru"): 12,
            ("safe_action", "en"): 12,
            ("safe_action", "ru"): 12,
        })

    def test_all_policy_cases_are_covered(self):
        counts = collections.Counter((row["skill"], row["language"], row["rubric"]["policy_case"]) for row in self.rows)
        self.assertEqual(len(counts), 16)
        self.assertTrue(all(value == 3 for value in counts.values()))

    def test_exam_does_not_copy_training_inputs_or_answers(self):
        lesson_inputs = {row["input"] for row in self.lessons}
        lesson_targets = {row["target"] for row in self.lessons}
        for row in self.rows:
            self.assertNotIn(row["prompt"], lesson_inputs)
            self.assertNotIn(row["reference_answer"], lesson_targets)
            nearest = max(
                SequenceMatcher(None, row["reference_answer"], lesson["target"]).ratio()
                for lesson in self.lessons
                if lesson["skill"] == row["skill"] and lesson["language"] == row["language"]
            )
            self.assertLess(nearest, 0.90, row["id"])

    def test_rules_are_frozen_before_training(self):
        rules = self.payload["rules"]
        self.assertFalse(rules["rag_used"])
        self.assertFalse(rules["internet_used"])
        self.assertFalse(rules["exact_string_scoring_allowed"])
        self.assertFalse(rules["questions_may_change_after_training"])
        self.assertTrue(rules["final_score_requires_owner_review"])
        self.assertEqual(self.payload["pass_rule"]["matching_dora_minimum_correct_per_skill"], 20)
        self.assertEqual(self.payload["pass_rule"]["minimum_lead_over_every_control_answers_per_skill"], 6)

    def test_public_artifact_matches_deterministic_build(self):
        self.assertTrue(PUBLIC.exists())
        self.assertEqual(json.loads(PUBLIC.read_text(encoding="utf-8")), self.payload)


if __name__ == "__main__":
    unittest.main()
