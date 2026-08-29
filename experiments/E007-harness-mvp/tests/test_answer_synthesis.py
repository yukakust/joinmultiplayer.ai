import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
WORLD_PATH = ROOT / "site/experiments/E007/answer-synthesis-world-v0.1.json"
PROTOCOL_PATH = ROOT / "site/experiments/E007/answer-synthesis-protocol-v0.1.json"


class AnswerSynthesisProtocolTests(unittest.TestCase):
    def test_protocol_pins_frozen_world(self):
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        actual = hashlib.sha256(WORLD_PATH.read_bytes()).hexdigest()
        self.assertEqual(actual, protocol["source"]["sha256"])
        self.assertEqual(protocol["status"], "locked_before_first_run")

    def test_world_has_eight_nonempty_and_two_empty_cases(self):
        world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(world["cases"]), 10)
        self.assertEqual(sum(bool(case["piles"]) for case in world["cases"]), 8)
        self.assertEqual(sum(not case["piles"] for case in world["cases"]), 2)

    def test_every_nonempty_case_has_locked_meanings(self):
        world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        for case in world["cases"]:
            if case["piles"]:
                self.assertTrue(case["required_meanings"], case["id"])
                self.assertTrue(case["forbidden_meanings"], case["id"])


if __name__ == "__main__":
    unittest.main()
