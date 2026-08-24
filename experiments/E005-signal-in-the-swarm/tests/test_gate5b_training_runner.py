import importlib.util
import sys
import unittest
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/train_gate5b_tracks.py"
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("train_gate5b_tracks", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Gate5BTrainingRunnerTests(unittest.TestCase):
    def test_prompt_tokens_are_hidden_from_loss(self):
        class Tokenizer:
            pad_token_id = 0
            def apply_chat_template(self, messages, **kwargs):
                return [1, 2, 3] if len(messages) == 1 else [1, 2, 3, 4, 5]
        encoded = MODULE.encode_lesson(Tokenizer(), {"id": "x", "prompt": "p", "target": "t"}, 20)
        self.assertEqual(encoded["labels"], [-100, -100, -100, 4, 5])

    def test_causal_loss_ignores_prompt(self):
        logits = torch.zeros(1, 4, 7)
        labels = torch.tensor([[-100, -100, 3, 4]])
        self.assertTrue(torch.isfinite(MODULE.causal_loss(logits, labels)))

    def test_training_order_freezes_tracks_and_merger(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertLess(source.index('encoded["cause"]'), source.index('encoded["safety"]'))
        self.assertIn('model.set_trainable(part)', source)
        self.assertIn('"merger_trained": False', source)
        self.assertIn('"exam_run": False', source)

    def test_only_adapter_states_are_saved(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('model.adapter_state("cause")', source)
        self.assertIn('model.adapter_state("safety")', source)
        self.assertNotIn('model.state_dict()', source)


if __name__ == "__main__":
    unittest.main()
