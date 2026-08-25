from __future__ import annotations

import sys
import unittest
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gate5c_model import SeparateShelfReader, SeparateShelfQwen  # noqa: E402
from train_gate5c_reader import encode_next_token_examples  # noqa: E402


class Gate5CModelTest(unittest.TestCase):
    def test_fresh_projectors_keep_two_equal_base_shelves(self):
        reader = SeparateShelfReader(16, rank=4)
        base = torch.randn(2, 16)
        cause = torch.randn(2, 16)
        safety = torch.randn(2, 16)
        cause_shelf, safety_shelf = reader(base, cause, safety)
        self.assertTrue(torch.equal(cause_shelf, base))
        self.assertTrue(torch.equal(safety_shelf, base))

    def test_two_projectors_do_not_share_parameters(self):
        reader = SeparateShelfReader(16, rank=4)
        cause_ids = {id(parameter) for parameter in reader.cause_projector.parameters()}
        safety_ids = {id(parameter) for parameter in reader.safety_projector.parameters()}
        self.assertFalse(cause_ids & safety_ids)

    def test_clip_bounds_each_shelf_input(self):
        reader = SeparateShelfReader(8, rank=2, max_delta_ratio=0.5)
        base = torch.ones(1, 8)
        clipped = reader.clip(torch.full((1, 8), 100.0), base)
        self.assertLessEqual(float(torch.linalg.vector_norm(clipped)), float(torch.linalg.vector_norm(base)) * 0.5 + 1e-5)

    def test_controls_assign_roles_without_mixing(self):
        model = object.__new__(SeparateShelfQwen)
        cause = torch.tensor([[1.0, 2.0]])
        safety = torch.tensor([[3.0, 4.0]])
        left, right = SeparateShelfQwen._select_shelves(model, cause, safety, "correct_shelves")
        self.assertTrue(torch.equal(left, cause))
        self.assertTrue(torch.equal(right, safety))
        left, right = SeparateShelfQwen._select_shelves(model, cause, safety, "swapped")
        self.assertTrue(torch.equal(left, safety))
        self.assertTrue(torch.equal(right, cause))
        left, right = SeparateShelfQwen._select_shelves(model, cause, safety, "empty")
        self.assertEqual(float(left.abs().sum() + right.abs().sum()), 0.0)

    def test_reader_examples_weight_the_second_skill_more(self):
        class TinyTokenizer:
            eos_token = "!"
            def apply_chat_template(self, messages, **kwargs):
                return "P:"
            def encode(self, text, add_special_tokens=False):
                return [ord(char) for char in text]

        rows = encode_next_token_examples(TinyTokenizer(), {
            "id": "L1", "language": "en", "prompt": "x", "target": "Cause. Safety."
        }, 64)
        self.assertEqual({row["weight"] for row in rows if row["part"] == "cause"}, {1.0})
        self.assertEqual({row["weight"] for row in rows if row["part"] == "safety"}, {2.0})


if __name__ == "__main__":
    unittest.main()
