import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "run_chat_first_qwen_gate16g6.py"
SPEC = importlib.util.spec_from_file_location("chat_first", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ChatFirstTests(unittest.TestCase):
    def test_fuse_rewards_agreement_and_keeps_limit(self):
        self.assertEqual(module.fuse(["A", "B", "C"], ["B", "D", "A"], 3), ["B", "A", "D"])

    def test_parse_tool_requires_real_supplied_coordinate(self):
        good = '<tool_call>{"name":"send_found","arguments":{"claim":"x","evidence_message_ids":["M1"]}}</tool_call>'
        bad = '<tool_call>{"name":"send_found","arguments":{"claim":"x","evidence_message_ids":["M9"]}}</tool_call>'
        self.assertTrue(module.parse_tool(good, {"M1"})["coordinates_valid"])
        self.assertFalse(module.parse_tool(bad, {"M1"})["coordinates_valid"])

    def test_bm25_prefers_matching_text(self):
        scores = module.bm25_scores(["amber ring", "blue ocean"], "amber")
        self.assertGreater(scores[0], scores[1])


if __name__ == "__main__":
    unittest.main()
