from __future__ import annotations

import json
import unittest
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OLD_DATA = ROOT / "site/experiments/E005/gate-4-data-v0.1.json"
TRANSFER_DATA = ROOT / "site/experiments/E005/gate-4-transfer-data-v0.1.json"


class Gate4TransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.old = json.loads(OLD_DATA.read_text(encoding="utf-8"))["examples"]
        cls.data = json.loads(TRANSFER_DATA.read_text(encoding="utf-8"))
        cls.rows = cls.data["questions"]

    def test_sixteen_questions_are_balanced_and_unique(self) -> None:
        self.assertEqual(len(self.rows), 16)
        self.assertEqual(len({row["prompt"] for row in self.rows}), 16)
        self.assertEqual(Counter((row["skill"], row["language"]) for row in self.rows), {
            ("archivist", "en"): 4,
            ("archivist", "ru"): 4,
            ("safety_keeper", "en"): 4,
            ("safety_keeper", "ru"): 4,
        })

    def test_reference_answers_do_not_reuse_the_training_template(self) -> None:
        for row in self.rows:
            training = [old for old in self.old if old["skill"] == row["skill"] and old["split"] == "train" and old["language"] == row["language"]]
            closest = max(SequenceMatcher(None, row["reference_answer"], old["target"]).ratio() for old in training)
            self.assertLess(closest, 0.85, row["id"])

    def test_no_new_training_or_rag_is_allowed(self) -> None:
        self.assertFalse(self.data["training_allowed"])
        self.assertFalse(self.data["rag_used"])
        self.assertTrue(self.data["pass_rule"]["final_score_requires_human_review"])

    def test_transfer_runner_only_generates_raw_answers(self) -> None:
        source = (ROOT / "experiments/E005-signal-in-the-swarm/src/eval_gate4_transfer.py").read_text(encoding="utf-8")
        self.assertIn('"training_performed": False', source)
        self.assertIn('"rag_used": False', source)
        self.assertIn("exact-string matching forbidden", source)
        self.assertNotIn("optimizer", source)
        self.assertNotIn("loss.backward", source)


if __name__ == "__main__":
    unittest.main()
