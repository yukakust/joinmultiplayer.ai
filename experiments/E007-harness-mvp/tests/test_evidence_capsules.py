import json
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
MODULE_PATH = ROOT / "experiments/E007-harness-mvp/src/run_evidence_capsule_test.py"
SPEC = importlib.util.spec_from_file_location("run_evidence_capsule_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EvidenceCapsuleWorldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads((ROOT / "site/experiments/E007/evidence-capsule-protocol-v0.1.json").read_text())
        cls.world = json.loads((ROOT / "site/experiments/E007/evidence-capsules-v0.1.json").read_text())

    def test_protocol_and_world_are_frozen_before_inference(self):
        self.assertEqual(self.protocol["status"], "locked_before_inference")
        self.assertEqual(self.world["status"], "frozen_before_inference")

    def test_balanced_population(self):
        counts = {group: sum(item["group"] == group for item in self.world["packets"]) for group in ("useful", "misleading", "broken")}
        self.assertEqual(counts, {"useful": 8, "misleading": 8, "broken": 8})

    def test_every_packet_has_the_four_agreed_parts(self):
        for packet in self.world["packets"]:
            self.assertTrue(packet["claim"])
            self.assertTrue(packet["evidence_window"]["text"])
            self.assertTrue(packet["candidate_evidence"]["text"])
            self.assertEqual(set(packet["source"]), {"source_id", "source_version", "sha256"})

    def test_only_locked_oversize_case_exceeds_limit(self):
        over = [item["id"] for item in self.world["packets"] if item["evidence_window"]["token_count"] > 500]
        self.assertEqual(over, ["B08"])

    def test_mechanical_verifier_matches_all_frozen_expectations(self):
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained("/home/yuka/models/e007/qwen3-reranker-4b-22e6836", local_files_only=True)
        decisions = {
            packet["id"]: MODULE.verify_packet(packet, self.world["sources"], tokenizer)["decision"]
            for packet in self.world["packets"]
        }
        expected = {packet["id"]: packet["expected"]["mechanical"] for packet in self.world["packets"]}
        self.assertEqual(decisions, expected)

    def test_relevance_decision_uses_locked_thresholds(self):
        thresholds = self.protocol["relevance_gate"]["thresholds"]
        self.assertEqual(MODULE.relevance_decision(0.99, thresholds), "take")
        self.assertEqual(MODULE.relevance_decision(0.50, thresholds), "not_sure")
        self.assertEqual(MODULE.relevance_decision(0.001, thresholds), "drop")

    def test_published_result_preserves_locked_outcome(self):
        path = ROOT / "site/experiments/E007/evidence-capsule-result-v0.1.json"
        if not path.exists():
            self.skipTest("result not published yet")
        result = json.loads(path.read_text())
        self.assertTrue(result["passed_locked_gate"])
        self.assertEqual(result["mechanical"]["summary"]["correct"], 24)
        self.assertEqual(result["mechanical"]["summary"]["broken_accepted"], 0)
        self.assertEqual(result["relevance"]["summary"]["useful_taken"], 8)
        self.assertEqual(result["relevance"]["summary"]["useful_dropped"], 0)
        self.assertEqual(result["relevance"]["summary"]["misleading_taken"], 0)


if __name__ == "__main__":
    unittest.main()
