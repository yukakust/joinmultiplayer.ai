import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/build_gate5b_data.py"
SPEC = importlib.util.spec_from_file_location("build_gate5b_data", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Gate5BDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design, cls.curriculum, cls.exam = MODULE.build()

    def test_public_files_match_deterministic_builder(self):
        for name, expected in (
            ("gate-5b-design-v0.1.json", self.design),
            ("gate-5b-curriculum-v0.1.json", self.curriculum),
            ("gate-5b-locked-test-v0.1.json", self.exam),
        ):
            actual = json.loads((ROOT / "site/experiments/E005" / name).read_text())
            self.assertEqual(actual, expected)

    def test_split_counts_and_languages_are_balanced(self):
        tracks = self.curriculum["track_lessons"]
        merger = self.curriculum["merger_lessons"]
        exam = self.exam["questions"]
        self.assertEqual(len(tracks), 256)
        self.assertEqual(len(merger), 192)
        self.assertEqual(len(exam), 32)
        for rows in (tracks, merger, exam):
            self.assertEqual(sum(row["language"] == "en" for row in rows), len(rows) // 2)

    def test_entities_and_prompts_do_not_cross_splits(self):
        groups = [self.curriculum["track_lessons"], self.curriculum["merger_lessons"], self.exam["questions"]]
        entity_sets = [{row["device"] for row in rows} for rows in groups]
        prompt_sets = [{row.get("prompt", row.get("question")) for row in rows} for rows in groups]
        for left in range(len(groups)):
            for right in range(left + 1, len(groups)):
                self.assertTrue(entity_sets[left].isdisjoint(entity_sets[right]))
                self.assertTrue(prompt_sets[left].isdisjoint(prompt_sets[right]))

    def test_exam_covers_every_pair_in_both_languages(self):
        for language in ("en", "ru"):
            pairs = {(row["cause_label"], row["safety_label"]) for row in self.exam["questions"] if row["language"] == language}
            self.assertEqual(len(pairs), 16)

    def test_design_freezes_real_track_equation_and_controls(self):
        architecture = self.design["architecture"]
        self.assertEqual(architecture["personal_track_layers"], [6, 21])
        self.assertIn("track_cause(h)-z0", architecture["equation"])
        self.assertFalse(self.design["training_performed"])
        self.assertFalse(self.design["exam_run"])
        self.assertIn("wrong_same_role_pair", self.design["conditions"])


if __name__ == "__main__":
    unittest.main()
