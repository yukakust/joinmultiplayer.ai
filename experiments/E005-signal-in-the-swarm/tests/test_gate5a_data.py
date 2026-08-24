import importlib.util
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/build_gate5a_data.py"
SPEC = importlib.util.spec_from_file_location("build_gate5a_data", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Gate5ADataTests(unittest.TestCase):
    def test_curriculum_is_balanced_and_unique(self):
        payload = MODULE.build_lessons()
        rows = payload["lessons"]
        self.assertEqual(len(rows), 384)
        self.assertEqual(len({row["id"] for row in rows}), 384)
        self.assertEqual(len({row["input"] for row in rows}), 384)
        for skill in ("cause", "safety"):
            for language in ("en", "ru"):
                self.assertEqual(sum(row["skill"] == skill and row["language"] == language for row in rows), 96)

    def test_exam_is_locked_new_and_requires_both_capsules(self):
        lessons = MODULE.build_lessons()["lessons"]
        exam = MODULE.build_exam()
        self.assertEqual(exam["status"], "locked_not_run")
        self.assertEqual(len(exam["questions"]), 24)
        self.assertEqual(sum(row["language"] == "en" for row in exam["questions"]), 12)
        self.assertEqual(sum(row["language"] == "ru" for row in exam["questions"]), 12)
        lesson_inputs = {row["input"] for row in lessons}
        for row in exam["questions"]:
            self.assertNotIn(row["cause_prompt"], lesson_inputs)
            self.assertNotIn(row["safety_prompt"], lesson_inputs)
            self.assertTrue(row["expected_cause_capsule"])
            self.assertTrue(row["expected_safety_capsule"])

    def test_public_files_match_the_builder(self):
        lessons = json.loads(MODULE.LESSONS_OUT.read_text(encoding="utf-8"))
        exam = json.loads(MODULE.EXAM_OUT.read_text(encoding="utf-8"))
        self.assertEqual(lessons, MODULE.build_lessons())
        self.assertEqual(exam, MODULE.build_exam())

    def test_checkpoint_freezes_the_exact_files_before_training(self):
        checkpoint = json.loads((ROOT / "site/experiments/E005/gate-5a-data-checkpoint-v0.1.json").read_text(encoding="utf-8"))
        self.assertFalse(checkpoint["weights_changed"])
        self.assertFalse(checkpoint["exam_run"])
        for name, path in (("lessons", MODULE.LESSONS_OUT), ("exam", MODULE.EXAM_OUT)):
            self.assertEqual(checkpoint[name]["file_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
