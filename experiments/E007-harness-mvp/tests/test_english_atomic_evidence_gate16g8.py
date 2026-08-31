import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "run_english_atomic_evidence_gate16g8.py"
SPEC = importlib.util.spec_from_file_location("gate16g8", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EvidenceToolTests(unittest.TestCase):
    def test_accepts_multiple_exact_spans(self):
        raw = '<tool_call>{"name":"send_evidence","arguments":{"spans":[{"source_id":"M1","quote":"alpha"},{"source_id":"M2","quote":"beta"}]}}</tool_call>'
        result = MODULE.parse_tool(raw, {"M1": "alpha one", "M2": "two beta"}, 3, 600)
        self.assertEqual(result["receipt"], "EXACT_EVIDENCE")
        self.assertEqual(len(result["spans"]), 2)

    def test_rejects_paraphrased_span(self):
        raw = '<tool_call>{"name":"send_evidence","arguments":{"spans":[{"source_id":"M1","quote":"similar"}]}}</tool_call>'
        result = MODULE.parse_tool(raw, {"M1": "exact"}, 3, 600)
        self.assertEqual(result["receipt"], "ERROR")

    def test_accepts_no_evidence(self):
        raw = '<tool_call>{"name":"send_no_evidence","arguments":{}}</tool_call>'
        result = MODULE.parse_tool(raw, {"M1": "exact"}, 3, 600)
        self.assertEqual(result["receipt"], "NO_EVIDENCE")

    def test_rejects_more_than_three_spans(self):
        spans = ','.join(f'{{"source_id":"M1","quote":"q{i}"}}' for i in range(4))
        raw = f'<tool_call>{{"name":"send_evidence","arguments":{{"spans":[{spans}]}}}}</tool_call>'
        result = MODULE.parse_tool(raw, {"M1": "q0 q1 q2 q3"}, 3, 600)
        self.assertEqual(result["receipt"], "ERROR")


if __name__ == "__main__":
    unittest.main()
