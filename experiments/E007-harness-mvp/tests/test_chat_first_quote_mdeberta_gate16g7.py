import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "run_chat_first_quote_mdeberta_gate16g7.py"
SPEC = importlib.util.spec_from_file_location("gate16g7", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class QuoteTurnstileTests(unittest.TestCase):
    def test_accepts_only_exact_source_quote(self):
        raw = '<tool_call>{"name":"send_quote","arguments":{"source_id":"M1","quote":"exact words"}}</tool_call>'
        result = MODULE.parse_quote_tool(raw, {"M1": "before exact words after"}, 100)
        self.assertEqual(result["quote_receipt"], "EXACT_QUOTE")
        self.assertTrue(result["quote_exact"])

    def test_rejects_paraphrase(self):
        raw = '<tool_call>{"name":"send_quote","arguments":{"source_id":"M1","quote":"similar words"}}</tool_call>'
        result = MODULE.parse_quote_tool(raw, {"M1": "before exact words after"}, 100)
        self.assertEqual(result["quote_receipt"], "ERROR")

    def test_accepts_explicit_no_quote(self):
        raw = '<tool_call>{"name":"send_no_quote","arguments":{}}</tool_call>'
        result = MODULE.parse_quote_tool(raw, {"M1": "source"}, 100)
        self.assertEqual(result["quote_receipt"], "NO_QUOTE")

    def test_rejects_unknown_source(self):
        raw = '<tool_call>{"name":"send_quote","arguments":{"source_id":"M2","quote":"source"}}</tool_call>'
        result = MODULE.parse_quote_tool(raw, {"M1": "source"}, 100)
        self.assertEqual(result["quote_receipt"], "ERROR")


if __name__ == "__main__":
    unittest.main()
