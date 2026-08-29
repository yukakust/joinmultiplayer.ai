import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
WORLD_PATH = ROOT / "site/experiments/E007/answer-synthesis-world-v0.1.json"
PROTOCOL_PATH = ROOT / "site/experiments/E007/answer-synthesis-protocol-v0.1.json"
MODULE_PATH = Path(__file__).parents[1] / "src/run_answer_synthesis.py"
SPEC = importlib.util.spec_from_file_location("run_answer_synthesis", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AnswerSynthesisProtocolTests(unittest.TestCase):
    def test_protocol_pins_frozen_world(self):
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        actual = hashlib.sha256(WORLD_PATH.read_bytes()).hexdigest()
        self.assertEqual(actual, protocol["source"]["sha256"])
        self.assertEqual(protocol["status"], "locked_before_first_run")

    def test_world_has_eight_nonempty_and_two_empty_cases(self):
        world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(world["cases"]), 10)
        self.assertEqual(sum(bool(case["piles"]) for case in world["cases"]), 8)
        self.assertEqual(sum(not case["piles"] for case in world["cases"]), 2)

    def test_every_nonempty_case_has_locked_meanings(self):
        world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        for case in world["cases"]:
            if case["piles"]:
                self.assertTrue(case["required_meanings"], case["id"])
                self.assertTrue(case["forbidden_meanings"], case["id"])

    def test_prompt_contains_question_and_every_pile(self):
        case = {
            "question": "What happened?",
            "piles": [
                {"pile_id": "P1", "claims": ["First claim."]},
                {"pile_id": "P2", "claims": ["Second claim."]},
            ],
        }
        prompt = MODULE.make_user_prompt(case)
        self.assertIn("QUESTION:\nWhat happened?", prompt)
        self.assertEqual(prompt.count("First claim."), 1)
        self.assertEqual(prompt.count("Second claim."), 1)
        self.assertIn("FINAL ANSWER:", prompt)

    def test_published_result_preserves_failed_manual_gate(self):
        result_path = ROOT / "site/experiments/E007/answer-synthesis-result-v0.1.json"
        audit_path = ROOT / "site/experiments/E007/answer-synthesis-human-audit-v0.1.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(result_path.read_bytes()).hexdigest(), audit["result_sha256"])
        self.assertEqual(result["mechanical_summary"]["exact_empty_answers"], 2)
        self.assertEqual(result["mechanical_summary"]["token_limit_hits"], 0)
        self.assertEqual(audit["summary"]["passed_cases"], 8)
        self.assertFalse(audit["summary"]["passed_locked_gate"])

    def test_qwen17b_protocol_changes_only_the_model(self):
        baseline = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        paired_path = ROOT / "site/experiments/E007/answer-synthesis-qwen17b-protocol-v0.1.json"
        paired = json.loads(paired_path.read_text(encoding="utf-8"))
        self.assertEqual(paired["source"], baseline["source"])
        self.assertEqual(paired["model"]["system"], baseline["model"]["system"])
        self.assertEqual(paired["model"]["max_new_tokens"], baseline["model"]["max_new_tokens"])
        self.assertEqual(paired["model"]["thinking"], baseline["model"]["thinking"])
        self.assertEqual(paired["model"]["do_sample"], baseline["model"]["do_sample"])
        self.assertEqual(paired["model"]["repository"], "Qwen/Qwen3-1.7B")
        self.assertEqual(paired["paired_baseline"]["protocol_sha256"], hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
