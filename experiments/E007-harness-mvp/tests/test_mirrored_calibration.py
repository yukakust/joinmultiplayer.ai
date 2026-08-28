import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
SCRIPT_PATH = ROOT / "experiments/E007-harness-mvp/src/calibrate_mirrored_labels.py"
SPEC = importlib.util.spec_from_file_location("calibrate_mirrored_labels", SCRIPT_PATH)
SCRIPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCRIPT)


class MirroredCalibrationTest(unittest.TestCase):
    def test_builds_ten_paired_records(self):
        result = SCRIPT.build()
        self.assertEqual(len(result["records"]), 10)

    def test_agreement_can_return_unsure(self):
        result = SCRIPT.build()
        self.assertTrue(any(record["agreement_method"]["decision"] == "unsure" for record in result["records"]))

    def test_calibrated_decision_matches_margin_sign(self):
        result = SCRIPT.build()
        for record in result["records"]:
            expected = "approve" if record["logit_calibration"]["semantic_margin"] > 0 else "reject"
            self.assertEqual(record["logit_calibration"]["decision"], expected)


if __name__ == "__main__":
    unittest.main()
