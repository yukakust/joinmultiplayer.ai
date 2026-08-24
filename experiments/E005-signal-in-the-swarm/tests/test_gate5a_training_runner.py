import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/train_gate5a.py"
SPEC = importlib.util.spec_from_file_location("train_gate5a", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Gate5ATrainingRunnerTests(unittest.TestCase):
    def test_runner_reads_only_frozen_lessons(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("locked-test", text)
        self.assertNotIn("expected_complete_answer", text)
        self.assertIn('"frozen_not_trained"', text)

    def test_runner_uses_real_dora_and_preserves_base_hash(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("use_dora=True", text)
        self.assertIn('target_modules=["q_proj", "v_proj"]', text)
        self.assertIn('"base_unchanged"', text)

    def test_both_personal_skills_are_supported(self):
        self.assertEqual(MODULE.SKILLS, {"cause", "safety"})


if __name__ == "__main__":
    unittest.main()
