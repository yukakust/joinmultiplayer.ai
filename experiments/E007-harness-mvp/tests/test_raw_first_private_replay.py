import importlib.util
import unittest
from pathlib import Path


MODULE = Path(__file__).parents[1] / "src/run_raw_first_private_replay.py"
SPEC = importlib.util.spec_from_file_location("raw_first", MODULE)
RAW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RAW)


class RawFirstReplayTests(unittest.TestCase):
    def test_locked_thresholds_have_three_states(self):
        self.assertEqual(RAW.reranker_decision(0.99), "TAKE")
        self.assertEqual(RAW.reranker_decision(0.5), "NOT_SURE")
        self.assertEqual(RAW.reranker_decision(0.0), "DROP")

    def test_frozen_case_labels_cover_five_useful_and_three_wrong_context(self):
        labels = list(RAW.EXPECTED_RAW_CASES.values())
        self.assertEqual(set(RAW.EXPECTED_RAW_CASES), {2, 3, 8, 9, 11, 14, 15, 20})
        self.assertEqual(labels.count("useful"), 5)
        self.assertEqual(labels.count("wrong_context"), 3)

    def test_invented_evidence_id_is_rejected(self):
        sources = [{"source_id": "S1", "text": "DeBERTa is a second signal."}]
        accepted, rejected = RAW.validate_candidates(
            '{"candidates":[{"claim":"It is a second signal.","evidence_ids":["S9.1"]}]}',
            sources,
        )
        self.assertEqual(accepted, [])
        self.assertEqual(rejected[0]["reason"], "invented_evidence_id")

    def test_final_answer_may_only_cite_accepted_claims(self):
        claims = [{"candidate_id": "E1"}]
        self.assertTrue(RAW.valid_final("It is supported [E1].", claims))
        self.assertFalse(RAW.valid_final("It is supported [E2].", claims))
        self.assertFalse(RAW.valid_final("It is supported.", claims))


if __name__ == "__main__":
    unittest.main()
