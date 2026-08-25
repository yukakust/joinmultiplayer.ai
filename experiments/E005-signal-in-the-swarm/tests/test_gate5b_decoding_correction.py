import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/resume_gate5b_truncated.py"
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("resume_gate5b_truncated", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Gate5BDecodingCorrectionTests(unittest.TestCase):
    def test_only_ceiling_answers_are_selected(self):
        class Tokenizer:
            def encode(self, text, **kwargs):
                return list(text)
        self.assertTrue(MODULE.is_cut_off(Tokenizer(), {"answer": "xxxx"}, 4))
        self.assertFalse(MODULE.is_cut_off(Tokenizer(), {"answer": "xxx"}, 4))

    def test_science_contract_does_not_retrain_or_change_exam(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("optimizer", source.casefold())
        self.assertIn('"weights_changed": False', source)
        self.assertIn('"questions_changed": False', source)
        self.assertIn('"pass_rule_changed": False', source)
        self.assertIn("answer.startswith(old)", source)


if __name__ == "__main__":
    unittest.main()
