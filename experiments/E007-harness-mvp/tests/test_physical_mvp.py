import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER_PATH = ROOT / "experiments/E007-harness-mvp/src/run_physical_mvp.py"
PROTOCOL_PATH = ROOT / "site/experiments/E007/physical-mvp-protocol-v0.1.json"
MEMORY_PATH = ROOT / "site/experiments/E007/physical-mvp-memory-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/physical-mvp-result-v0.1.json"
AUDIT_PATH = ROOT / "site/experiments/E007/physical-mvp-human-audit-v0.1.json"
SPEC = importlib.util.spec_from_file_location("e007_physical_mvp", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class PhysicalMvpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        cls.memory = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))

    def fake_room(self):
        questions = self.protocol["questions"]
        nodes = []
        device_by_card = {
            card: device["id"] for device in self.protocol["devices"] for card in device["cards"]
        }
        for card_id, device in device_by_card.items():
            results = []
            for question in questions:
                for lane in ("exact_terms", "chargram_vector", "multilingual_neural"):
                    results.append({
                        "question_id": question["id"],
                        "question_hash": RUNNER.digest_bytes(question["question"].encode()),
                        "lane": lane, "status": "empty", "score": 0.0,
                        "source_id": "NOISE", "capsule": None, "canary_hash": "",
                    })
            nodes.append({
                "card_id": card_id, "device_label": device, "status": "complete",
                "result": {"results": results},
            })
        return {
            "room_id": "LTEST", "protocol_revision": self.protocol["revision"],
            "status": "complete", "nodes": nodes,
        }

    def test_transport_gate_requires_four_nodes_and_all_receipts(self):
        room = self.fake_room()
        result = RUNNER.validate_transport(room, self.protocol)
        self.assertTrue(result["passed"])
        self.assertEqual(result["terminal_receipts"], 72)
        room["nodes"][0]["result"]["results"].pop()
        self.assertFalse(RUNNER.validate_transport(room, self.protocol)["passed"])

    def test_exact_source_verification_builds_one_deduplicated_candidate(self):
        room = self.fake_room()
        node = next(item for item in room["nodes"] if item["card_id"] == "MVP-Y1")
        source = next(item for item in self.memory["libraries"]["MVP-Y1"] if item["id"] == "Y1-AVEN-SAFE")
        capsule = {
            **source["capsule"], "evidence": source["text"],
            "source_lineage": source["lineage"], "permission": "share_this_capsule",
        }
        for receipt in node["result"]["results"][:2]:
            receipt.update({"status": "found", "source_id": source["id"], "capsule": capsule})
        candidates, checks = RUNNER.mechanically_verified_candidates(room, self.protocol, self.memory)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source_id"], "Y1-AVEN-SAFE")
        self.assertEqual(len(candidates[0]["receipt_lanes"]), 2)
        self.assertTrue(all(item["valid"] for item in checks))

    def test_locked_thresholds_keep_uncertainty(self):
        spec = self.protocol["central_pipeline_contract"]["reranker"]
        self.assertEqual(RUNNER.reranker_decision(0.99, spec), "TAKE")
        self.assertEqual(RUNNER.reranker_decision(0.5, spec), "NOT_SURE")
        self.assertEqual(RUNNER.reranker_decision(0.0, spec), "DROP")

    def test_json_parser_accepts_plain_or_fenced_object(self):
        self.assertEqual(RUNNER.parse_json_object('{"used_ids": []}'), {"used_ids": []})
        self.assertEqual(
            RUNNER.parse_json_object('```json\n{"used_ids": []}\n```'), {"used_ids": []}
        )
        self.assertIsNone(RUNNER.parse_json_object("not json"))

    def test_preserved_result_matches_manual_audit_counts(self):
        result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        self.assertTrue(result["transport"]["passed"])
        self.assertEqual(result["transport"]["terminal_receipts"], 72)
        required_found = sum(
            len(set(item["required_sources"]) & {
                source["source_id"] for source in item["candidates_before_central_filter"]
            })
            for item in result["questions"]
        )
        alternatives_found = sum(
            len(set(item["expected_alternatives"]) & {
                source["source_id"] for source in item["candidates_before_central_filter"]
            })
            for item in result["questions"]
        )
        self.assertEqual(required_found, 9)
        self.assertEqual(alternatives_found, 2)
        self.assertEqual(sum(item["main_answer_correct"] for item in audit["cases"][:5]), 4)
        self.assertFalse(audit["cases"][5]["main_answer_correct"])
        self.assertFalse(audit["summary"]["all_locked_gates_passed"])
        serialized = RESULT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("{{SYNTHETIC_PRIVATE_CANARY}}", serialized)


if __name__ == "__main__":
    unittest.main()
