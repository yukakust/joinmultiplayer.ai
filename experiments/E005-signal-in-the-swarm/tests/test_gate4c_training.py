from __future__ import annotations

import collections
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/build_gate4c_training.py"
PUBLIC = ROOT / "site/experiments/E005/gate-4c-lessons-v0.1.json"

SPEC = importlib.util.spec_from_file_location("build_gate4c_training", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

OLD_TEST_ENTITIES = {
    "Lark-9", "Iven-3", "Moss-7", "Fenn-2", "Teya-8", "Runa-3", "Vela-9", "Noma-6",
    "Lumen-4", "Alder-2", "Pika-5", "Oriel-7", "Sova-4", "Bera-2", "Kora-5", "Deya-7",
}


class Gate4CTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = MODULE.build()
        cls.lessons = cls.payload["lessons"]

    def test_counts_and_training_has_not_started(self):
        self.assertEqual(self.payload["training_status"], "not_started")
        self.assertEqual(len(self.lessons), 384)
        self.assertEqual(collections.Counter(x["skill"] for x in self.lessons), {
            "source_work": 192,
            "safe_action": 192,
        })
        self.assertEqual(collections.Counter((x["skill"], x["language"]) for x in self.lessons), {
            ("source_work", "en"): 96,
            ("source_work", "ru"): 96,
            ("safe_action", "en"): 96,
            ("safe_action", "ru"): 96,
        })

    def test_formats_and_policy_cases_are_balanced(self):
        format_counts = collections.Counter((x["skill"], x["language"], x["format"]) for x in self.lessons)
        self.assertEqual(set(x["format"] for x in self.lessons), set(range(6)))
        self.assertTrue(all(count == 16 for count in format_counts.values()))
        policy_counts = collections.Counter((x["skill"], x["language"], x["policy_case"]) for x in self.lessons)
        self.assertTrue(all(count == 24 for count in policy_counts.values()))
        self.assertEqual(len(policy_counts), 16)

    def test_ids_and_inputs_are_unique_and_answers_are_varied(self):
        for field in ("id", "input"):
            values = [x[field] for x in self.lessons]
            self.assertEqual(len(values), len(set(values)), field)
        target_counts = collections.Counter(x["target"] for x in self.lessons)
        self.assertGreaterEqual(len(target_counts), 192)
        self.assertLessEqual(max(target_counts.values()), 4)

    def test_old_locked_test_entities_do_not_leak_into_training(self):
        text = json.dumps(self.lessons, ensure_ascii=False)
        for entity in OLD_TEST_ENTITIES:
            self.assertNotIn(entity, text)

    def test_conflict_lessons_show_an_actual_conflict(self):
        conflict = [x for x in self.lessons if x["policy_case"] == "conflicting_current_primaries"]
        self.assertEqual(len(conflict), 48)
        for lesson in conflict:
            marker = "conflict" if lesson["language"] == "en" else "противореч"
            self.assertIn(marker, lesson["input"].lower())

    def test_public_artifact_matches_deterministic_build(self):
        self.assertTrue(PUBLIC.exists())
        self.assertEqual(json.loads(PUBLIC.read_text(encoding="utf-8")), self.payload)


if __name__ == "__main__":
    unittest.main()
