import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/eval_gate5a3.py"


class Gate5A3RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("eval_gate5a3", SOURCE)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_human_capsules_expand_labels(self):
        row = {"language": "en"}
        cause, safety = self.module.semantic_capsules(row, "thermal_rebound", "keep_aux_vent_closed")
        self.assertIn("thermal rebound", cause["claim"])
        self.assertIn("vent closed", safety["action"])
        self.assertNotIn("thermal_rebound", str(cause))

    def test_instruct_chat_disables_thinking(self):
        self.assertIn("apply_chat_template", self.source)
        self.assertIn("enable_thinking=False", self.source)

    def test_runner_does_not_train_or_use_rag(self):
        self.assertNotIn(".train()", self.source)
        self.assertNotIn("optimizer", self.source.casefold())
        self.assertIn('"rag_used": False', self.source)
        self.assertIn('"training_performed": False', self.source)

    def test_cut_off_answer_cannot_pass(self):
        row = {
            "language": "en",
            "expected_cause_capsule": {"cause": "thermal_rebound"},
            "expected_safety_capsule": {"restriction": "keep_aux_vent_closed"},
        }
        result = {"output": "thermal rebound; keep the auxiliary vent closed", "generated_tokens": 192, "hit_token_limit": True}
        self.assertFalse(self.module.score(result, row)["complete"])


if __name__ == "__main__":
    unittest.main()
