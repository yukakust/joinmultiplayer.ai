from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/eval_gate4c.py"


class Gate4CEvalRunnerTests(unittest.TestCase):
    def test_runner_only_generates_and_never_trains(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('"training_performed": False', source)
        self.assertIn('"exact_string_scoring_performed": False', source)
        self.assertNotIn("optimizer", source.lower())
        self.assertNotIn("backward", source.lower())
        self.assertNotIn("gate-4c-lessons", source)

    def test_all_four_conditions_are_generated(self):
        source = SOURCE.read_text(encoding="utf-8")
        for condition in ("frozen_base", "matching_dora", "wrong_skill_dora", "shuffled_lessons_dora"):
            self.assertIn(condition, source)
        self.assertIn('"review": "unscored"', source)

    def test_generation_is_deterministic_and_offline(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("do_sample=False", source)
        self.assertIn("local_files_only=True", source)
        self.assertIn('"rag_used": False', source)
        self.assertIn('"internet_used": False', source)


if __name__ == "__main__":
    unittest.main()
