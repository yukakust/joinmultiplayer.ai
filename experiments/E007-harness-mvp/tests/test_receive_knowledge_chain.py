import importlib.util
import json
import unittest
from copy import deepcopy
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src/receive_knowledge_chain.py"
PAYLOAD_PATH = Path(__file__).parents[3] / "site/experiments/E007/knowledge-chain-physical-payload-v0.2.json"
SPEC = importlib.util.spec_from_file_location("receive_knowledge_chain", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReceiveKnowledgeChainTests(unittest.TestCase):
    def payload(self):
        return json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))

    def encode(self, value):
        return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    def test_frozen_payload_selects_last_revision(self):
        result = MODULE.reconstruct(PAYLOAD_PATH.read_bytes(), "test-receiver")
        self.assertEqual(result["decision"], "ready")
        self.assertEqual(result["current_revision_id"], "PHY-R3")
        self.assertEqual(result["history_revision_ids"], ["PHY-R1", "PHY-R2"])

    def test_input_order_does_not_choose_current(self):
        payload = self.payload()
        payload["records"].reverse()
        result = MODULE.reconstruct(self.encode(payload), "test-receiver")
        self.assertEqual(result["current_revision_id"], "PHY-R3")

    def test_relation_field_is_rejected_as_contract_noise(self):
        payload = self.payload()
        payload["records"][1]["relation"] = "refines"
        result = MODULE.reconstruct(self.encode(payload), "test-receiver")
        self.assertEqual(result["decision"], "invalid_record_contract")

    def test_missing_parent_stops_chain(self):
        payload = self.payload()
        payload["records"] = payload["records"][1:]
        result = MODULE.reconstruct(self.encode(payload), "test-receiver")
        self.assertEqual(result["decision"], "invalid_root")

    def test_two_heads_are_a_fork(self):
        payload = self.payload()
        fork = deepcopy(payload["records"][-1])
        fork["revision_id"] = "PHY-R3B"
        fork["claim"] = "A conflicting current claim."
        payload["records"].append(fork)
        result = MODULE.reconstruct(self.encode(payload), "test-receiver")
        self.assertEqual(result["decision"], "forked")

    def test_inactive_head_withdraws_current_claim(self):
        payload = self.payload()
        payload["records"][-1]["active"] = False
        payload["records"][-1]["claim"] = ""
        result = MODULE.reconstruct(self.encode(payload), "test-receiver")
        self.assertEqual(result["decision"], "withdrawn")
        self.assertIsNone(result["current_revision_id"])
        self.assertEqual(result["history_revision_ids"], ["PHY-R1", "PHY-R2", "PHY-R3"])


if __name__ == "__main__":
    unittest.main()
