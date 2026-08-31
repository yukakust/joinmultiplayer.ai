import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from outbound_secret_gate import inspect_capsule
from run_outbound_secret_gate16f1 import benign_cases, secret_cases


class SecretGateTests(unittest.TestCase):
    def test_every_locked_secret_is_blocked_without_value(self):
        for case in secret_cases():
            decision = inspect_capsule(case)
            self.assertEqual(decision["status"], "blocked", case["id"])
            self.assertNotIn(case["evidence"], str(decision))
            self.assertNotIn("capsule", decision)

    def test_every_locked_hard_negative_is_allowed_unchanged(self):
        for case in benign_cases():
            decision = inspect_capsule(case)
            self.assertEqual(decision, {"status": "allowed", "capsule": case}, case["id"])


if __name__ == "__main__":
    unittest.main()
