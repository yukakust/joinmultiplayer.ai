from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/publish_gate4c_training.py"
PUBLIC = ROOT / "site/experiments/E005/gate-4c-training-v0.1.json"
SPEC = importlib.util.spec_from_file_location("publish_gate4c_training", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Gate4CTrainingResultTests(unittest.TestCase):
    def test_public_checkpoint_matches_private_summaries(self):
        payload = MODULE.build()
        self.assertEqual(json.loads(PUBLIC.read_text(encoding="utf-8")), payload)
        self.assertEqual({run["skill"] for run in payload["runs"]}, {"source_work", "safe_action"})

    def test_training_changed_only_personal_weights(self):
        payload = MODULE.build()
        self.assertTrue(payload["checks"]["all_runs_used_same_frozen_base"])
        self.assertTrue(payload["checks"]["base_unchanged_after_every_run"])
        self.assertFalse(payload["checks"]["exam_was_read_by_training_runner"])
        self.assertFalse(payload["checks"]["rag_used"])
        for run in payload["runs"]:
            self.assertLess(run["loss_mean_last_24"], run["loss_mean_first_24"])
            self.assertEqual(run["trainable_parameters"], 1_232_896)

    def test_checkpoint_does_not_claim_exam_success(self):
        payload = MODULE.build()
        self.assertEqual(payload["status"], "two_personal_adapters_trained_exam_not_run")
        self.assertNotIn("passed", json.dumps(payload).lower())


if __name__ == "__main__":
    unittest.main()
