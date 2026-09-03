import importlib.util
import sys
import unittest
from pathlib import Path


SRC = Path(__file__).parents[1] / "src"
sys.path.insert(0, str(SRC))
MODULE = SRC / "run_minimal_evidence_private_replay.py"
SPEC = importlib.util.spec_from_file_location("minimal_evidence", MODULE)
MINIMAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MINIMAL)


class MinimalEvidenceReplayTests(unittest.TestCase):
    def test_only_top_two_take_sentences_are_allowed(self):
        units = [
            {"evidence_id": "S1.1", "reranker": {"score": 0.99, "decision": "TAKE"}},
            {"evidence_id": "S1.2", "reranker": {"score": 0.95, "decision": "TAKE"}},
            {"evidence_id": "S1.3", "reranker": {"score": 0.94, "decision": "TAKE"}},
            {"evidence_id": "S1.4", "reranker": {"score": 0.8, "decision": "NOT_SURE"}},
        ]
        self.assertEqual([item["evidence_id"] for item in MINIMAL.choose_allowed(units)], ["S1.1", "S1.2"])

    def test_non_allowed_id_is_rejected_even_if_it_exists_in_context(self):
        allowed = [{"evidence_id": "S1.1", "source_id": "S1", "text": "The direct answer."}]
        accepted, rejected = MINIMAL.validate_candidates(
            '{"candidates":[{"claim":"Neighboring advice.","evidence_ids":["S1.2"]}]}',
            allowed,
        )
        self.assertEqual(accepted, [])
        self.assertEqual(rejected[0]["reason"], "non_allowed_evidence_id")

    def test_allowed_exact_id_is_accepted(self):
        allowed = [{"evidence_id": "S1.1", "source_id": "S1", "text": "Normalize before judging."}]
        accepted, rejected = MINIMAL.validate_candidates(
            '{"candidates":[{"claim":"Normalize before judging.","evidence_ids":["S1.1"]}]}',
            allowed,
        )
        self.assertEqual(len(accepted), 1)
        self.assertEqual(rejected, [])


if __name__ == "__main__":
    unittest.main()
