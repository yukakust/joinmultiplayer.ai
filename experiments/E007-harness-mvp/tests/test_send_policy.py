import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
SPEC = importlib.util.spec_from_file_location("send_policy", ROOT / "experiments/E007-harness-mvp/src/evaluate_send_policy.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SendPolicyTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads((ROOT / "site/experiments/E007/send-policy-protocol-v0.1.json").read_text())
        self.memory = json.loads((ROOT / "site/experiments/E007/send-policy-memory-v0.1.json").read_text())

    def test_protocol_is_locked_before_run(self):
        self.assertEqual(self.protocol["status"], "locked_before_run")
        self.assertEqual([item["id"] for item in self.protocol["policies"]], ["balanced", "recall_first", "top1_candidate"])

    def test_test_world_is_new_and_complete(self):
        self.assertEqual(len(self.memory["questions"]), 10)
        self.assertEqual({key: len(value) for key, value in self.memory["libraries"].items()}, {"ATT-Y1": 6, "ATT-Y2": 6, "ATT-M1": 6, "ATT-M2": 6})
        self.assertEqual(sum(state == "found" for question in self.memory["questions"] for state in question["expected"].values()), 8)
        self.assertEqual(sum(state == "blocked" for question in self.memory["questions"] for state in question["expected"].values()), 1)

    def test_f2_threshold_prefers_recall(self):
        scores = [0.9, 0.4, 0.3, 0.2]
        labels = [True, True, False, False]
        f1_threshold, _ = MODULE.select_threshold(scores, labels, 1.0)
        f2_threshold, _ = MODULE.select_threshold(scores, labels, 2.0)
        self.assertLessEqual(f2_threshold, f1_threshold)

    def test_private_record_has_no_public_secret(self):
        private = next(item for item in self.memory["libraries"]["ATT-M1"] if item["permission"] == "blocked")
        self.assertIsNone(private["capsule"])
        self.assertIn("{{SYNTHETIC_PRIVATE_CANARY}}", private["text"])

    def test_published_result_preserves_equal_threshold_finding(self):
        result_path = ROOT / "site/experiments/E007/send-policy-result-v0.1.json"
        if not result_path.exists():
            self.skipTest("locked protocol has not run yet")
        result = json.loads(result_path.read_text())
        self.assertEqual(result["thresholds"]["balanced_f1"], result["thresholds"]["recall_first_f2"])
        self.assertEqual(result["summaries"]["balanced"]["useful_sources_delivered"], 8)
        self.assertEqual(result["summaries"]["balanced"]["critical_missed_knowledge"], 0)
        self.assertEqual(result["summaries"]["balanced"]["filterable_extra_candidates"], 8)
        self.assertEqual(result["summaries"]["top1_candidate"]["filterable_extra_candidates"], 30)


if __name__ == "__main__":
    unittest.main()
