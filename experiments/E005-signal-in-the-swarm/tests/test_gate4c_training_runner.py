from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/train_gate4c.py"
DATA = ROOT / "site/experiments/E005/gate-4c-lessons-v0.1.json"
SPEC = importlib.util.spec_from_file_location("train_gate4c", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Gate4CTrainingRunnerTests(unittest.TestCase):
    def test_runner_reads_only_frozen_lessons(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("gate-4c-locked-test", source)
        for skill in ("source_work", "safe_action"):
            payload, rows = MODULE.load_rows(DATA, skill, "correct")
            self.assertEqual(payload["training_status"], "not_started")
            self.assertEqual(len(rows), 192)

    def test_shuffled_control_changes_every_answer(self):
        for skill in ("source_work", "safe_action"):
            _, correct = MODULE.load_rows(DATA, skill, "correct")
            _, shuffled = MODULE.load_rows(DATA, skill, "shuffled")
            self.assertEqual([row["input"] for row in correct], [row["input"] for row in shuffled])
            self.assertTrue(all(a["target"] != b["target"] for a, b in zip(correct, shuffled)))

    def test_real_dora_and_frozen_base_are_required(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("use_dora=True", source)
        self.assertIn('target_modules=["q_proj", "v_proj"]', source)
        self.assertIn('"base_unchanged": base_hash_before == base_hash_after', source)
        self.assertNotIn("save_pretrained(args.model", source)

    def test_curriculum_content_hash_is_stable(self):
        payload = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertEqual(payload["content_sha256"], "08e12b86987bb6d49103f18fe9e1e3cad305abefd3af85d2cbcb2d2bb55badf1")


if __name__ == "__main__":
    unittest.main()
