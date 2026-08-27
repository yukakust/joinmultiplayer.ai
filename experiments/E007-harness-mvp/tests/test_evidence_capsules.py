import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]


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


if __name__ == "__main__":
    unittest.main()
