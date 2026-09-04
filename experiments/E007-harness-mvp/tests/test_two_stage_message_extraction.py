import importlib.util
import json
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "run_two_stage_message_extraction.py"
SPEC = importlib.util.spec_from_file_location("two_stage_message_extraction", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TwoStageMessageExtractionTest(unittest.TestCase):
    def test_simple_handles_are_validated(self):
        selected, errors = MODULE.validate_selection('{"message_ids":["M2","M1"]}', {"M1", "M2"})
        self.assertEqual(selected, ["M2", "M1"])
        self.assertEqual(errors, [])

    def test_code_reconstructs_exact_source_lines(self):
        message = {"handle": "M1", "text": "first line\nexact **source** line"}
        raw = json.dumps({
            "status": "FOUND",
            "claims": [{
                "claim": "The source supports the answer.",
                "message_id": "M1",
                "evidence_ids": ["M1-L2"],
            }],
        })
        result = MODULE.validate_extraction(raw, message)
        self.assertEqual(result["accepted"][0]["exact_quote"], "exact **source** line")

    def test_placeholder_claim_is_rejected(self):
        message = {"handle": "M1", "text": "real source"}
        raw = json.dumps({
            "status": "FOUND",
            "claims": [{
                "claim": "one atomic statement",
                "message_id": "M1",
                "evidence_ids": ["M1-L1"],
            }],
        })
        result = MODULE.validate_extraction(raw, message)
        self.assertEqual(result["accepted"], [])
        self.assertEqual(result["rejected"][0]["reason"], "placeholder_claim")


if __name__ == "__main__":
    unittest.main()
