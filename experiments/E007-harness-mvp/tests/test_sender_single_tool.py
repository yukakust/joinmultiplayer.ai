import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
PROTOCOL = ROOT / "site/experiments/E007/sender-single-tool-protocol-v0.1.json"
MODULE = Path(__file__).parents[1] / "src/run_sender_single_tool.py"
spec = importlib.util.spec_from_file_location("run_sender_single_tool", MODULE)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)


class SenderSingleToolTest(unittest.TestCase):
    def test_protocol_has_ten_independent_questions(self):
        data = json.loads(PROTOCOL.read_text())
        self.assertEqual(data["status"], "locked_before_inference")
        self.assertEqual(len(data["questions"]), 10)
        self.assertTrue(data["constants"]["one_question_per_generation"])
        self.assertEqual(sum(q["expected_status"] == "FOUND" for q in data["questions"]), 5)
        self.assertEqual(sum(q["expected_status"] == "EMPTY" for q in data["questions"]), 5)

    def test_parse_tool_calls(self):
        found = module.parse_tool('<tool_call>{"name":"send_found","arguments":{"claim":"x","evidence":["M0002"]}}</tool_call>')
        empty = module.parse_tool('<tool_call>{"name":"send_empty","arguments":{}}</tool_call>')
        self.assertEqual(found["status"], "FOUND")
        self.assertEqual(empty["status"], "EMPTY")
        self.assertEqual(module.parse_tool("plain text")["status"], "ERROR")

    def test_tool_schema_has_only_two_choices(self):
        self.assertEqual({tool["function"]["name"] for tool in module.TOOLS}, {"send_found", "send_empty"})


if __name__ == "__main__":
    unittest.main()
