from __future__ import annotations

import sys
import unittest
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trace_gate5b_tokens import summarize  # noqa: E402


class Gate5B3XrayTest(unittest.TestCase):
    def test_summary_keeps_languages_separate(self):
        token = {
            "cause_gate": 1.0,
            "safety_gate": 0.1,
            "cause_contribution_norm": 10.0,
            "safety_contribution_norm": 1.0,
            "delta_cosine_similarity": 0.25,
        }
        result = summarize([
            {"language": "ru", "tokens": [token]},
            {"language": "en", "tokens": [{**token, "safety_gate": 0.9}]},
        ])
        self.assertEqual(result["ru"]["safety_gate_mean"], 0.1)
        self.assertEqual(result["en"]["safety_gate_mean"], 0.9)
        self.assertEqual(result["all"]["safety_gate_mean"], 0.5)
        self.assertEqual(result["ru"]["safety_gate_below_0_25_fraction"], 1.0)

    def test_public_protocol_is_locked_and_read_only(self):
        import json

        protocol = json.loads((ROOT.parents[1] / "site/experiments/E005/gate-5b3-xray-protocol-v0.1.json").read_text())
        self.assertEqual(protocol["status"], "locked_before_run")
        self.assertTrue(protocol["frozen_inputs"]["weights_must_not_change"])
        self.assertEqual(protocol["next_step_is_not_authorized_by_this_protocol"], "training_or_changing_the_merger")


if __name__ == "__main__":
    unittest.main()
