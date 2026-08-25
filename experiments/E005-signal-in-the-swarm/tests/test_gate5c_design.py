from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class Gate5CDesignTest(unittest.TestCase):
    def setUp(self):
        self.design = json.loads((ROOT / "site/experiments/E005/gate-5c-design-v0.1.json").read_text())

    def test_design_is_frozen_before_training(self):
        self.assertEqual(self.design["status"], "locked_before_training")
        self.assertFalse(self.design["training_started"])
        self.assertFalse(self.design["exam_run"])

    def test_only_reader_may_change(self):
        frozen = self.design["training"]["does_not_change"]
        self.assertIn("base Qwen weights", frozen)
        self.assertIn("CAUSE-I weights", frozen)
        self.assertIn("SAFETY-I weights", frozen)
        self.assertIn("shared tail weights", frozen)
        self.assertEqual(len(self.design["training"]["changes"]), 3)

    def test_controls_can_detect_central_shortcut(self):
        conditions = set(self.design["conditions"])
        self.assertIn("empty_shelves", conditions)
        self.assertIn("cause_shelf_only", conditions)
        self.assertIn("safety_shelf_only", conditions)
        self.assertIn("two_cause_shelves", conditions)
        self.assertIn("two_safety_shelves", conditions)

    def test_public_route_and_page_exist(self):
        app = (ROOT / "site/app.js").read_text()
        server = (ROOT / "server/server.py").read_text()
        self.assertIn('path === "experiment/e005/gate-5c"', app)
        self.assertIn('"/experiment/e005/gate-5c"', server)
        self.assertIn("gate-5c-design-v0.1.json", app)


if __name__ == "__main__":
    unittest.main()
