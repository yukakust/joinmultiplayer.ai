import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
PROTOCOL = ROOT / "site/experiments/E007/sender-extraction-protocol-v0.1.json"
MODULE = Path(__file__).parents[1] / "src/run_sender_extraction.py"
spec = importlib.util.spec_from_file_location("run_sender_extraction", MODULE)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)


class SenderExtractionTest(unittest.TestCase):
    def test_protocol_is_balanced_and_locked(self):
        data = json.loads(PROTOCOL.read_text())
        self.assertEqual(data["status"], "locked_before_inference")
        self.assertEqual(len(data["questions"]), 10)
        self.assertEqual(sum(q["expected_status"] == "FOUND" for q in data["questions"]), 5)
        self.assertEqual(sum(q["expected_status"] == "EMPTY" for q in data["questions"]), 5)
        self.assertEqual({q["conversation"] for q in data["questions"]}, {"CHAT-C", "CHAT-D"})

    def test_prompt_does_not_reveal_gold(self):
        data = json.loads(PROTOCOL.read_text())
        questions = [{"id": q["id"], "question": q["question"]} for q in data["questions"][:5]]
        prompt = module.make_prompt(questions, "SAFE TRANSCRIPT")
        self.assertNotIn("expected_status", prompt)
        self.assertNotIn("expected_meaning", prompt)
        self.assertNotIn("Published knowledge, Callable", prompt)

    def test_parser_accepts_fenced_json(self):
        parsed = module.parse_array('```json\n[{"id":"C1","status":"EMPTY","claim":"","evidence":[]}]\n```')
        self.assertEqual(parsed[0]["status"], "EMPTY")


if __name__ == "__main__":
    unittest.main()
