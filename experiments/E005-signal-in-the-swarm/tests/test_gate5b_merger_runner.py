import importlib.util
import sys
import unittest
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/train_gate5b_merger.py"
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("train_gate5b_merger", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Gate5BMergerRunnerTests(unittest.TestCase):
    def test_tensor_digest_changes_with_a_tensor(self):
        first = {"x": torch.tensor([1.0, 2.0])}
        second = {"x": torch.tensor([1.0, 3.0])}
        self.assertNotEqual(MODULE.tensor_digest(first), MODULE.tensor_digest(second))

    def test_runner_loads_both_tracks_before_training_only_merger(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertLess(source.index('load_adapter(model, "cause"'), source.index('train_merger(' , source.index('def run(')))
        self.assertLess(source.index('load_adapter(model, "safety"'), source.index('train_merger(' , source.index('def run(')))
        self.assertIn('model.set_trainable("merger")', source)
        self.assertIn('mode="correct"', source)
        self.assertIn('"exam_run": False', source)

    def test_runner_checks_both_tracks_are_unchanged(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('"cause_unchanged": cause_before == cause_after', source)
        self.assertIn('"safety_unchanged": safety_before == safety_after', source)
        self.assertIn('"merger_changed": merger_before != merger_after', source)


if __name__ == "__main__":
    unittest.main()
