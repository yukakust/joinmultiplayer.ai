import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src/evaluate_mobile_reranker.py"
SPEC = importlib.util.spec_from_file_location("evaluate_mobile_reranker", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MobileRerankerTests(unittest.TestCase):
    def test_evaluate_uses_frozen_three_way_rule(self):
        calibration = [
            {"relevant": True}, {"relevant": True}, {"relevant": True}, {"relevant": True},
            {"relevant": False}, {"relevant": False}, {"relevant": False}, {"relevant": False},
        ]
        heldout = [
            {"id":"u","kind":"useful","question":"q","passage":"p","family":"x"},
            {"id":"h","kind":"hard_extra","question":"q","passage":"h","family":"x"},
            {"id":"o","kind":"obvious_extra","question":"q","passage":"o","family":"x"},
        ]
        payload = {
            "method":"fake", "mode":"llama", "runtime_seconds":1,
            "model_file_bytes":100,
            "calibration_scores":[0.9,0.8,0.7,0.6,0.4,0.3,0.2,0.1],
            "heldout_scores":[0.95,0.5,0.05]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scores.json"
            path.write_text(json.dumps(payload))
            result = MODULE.evaluate(path, calibration, heldout)
        self.assertEqual([item["decision"] for item in result["records"]], ["accept", "unclear", "reject"])
        self.assertEqual(result["summary"]["useful_rejected"], 0)


if __name__ == "__main__":
    unittest.main()
