import sys
import unittest
from pathlib import Path

import torch


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_token_moe import (  # noqa: E402
    FrozenTokenStem,
    PersonalFFNExpert,
    decode_result,
    encode_result,
)


class TokenMoeTests(unittest.TestCase):
    def test_three_symbol_codec_is_nonbinary_and_round_trips(self):
        for value in (0, 7, 42, 431, 996, 997):
            symbols = encode_result(value)
            self.assertEqual(len(symbols), 3)
            expected = None if value == 997 else value
            self.assertEqual(decode_result(symbols), expected)

    def test_fresh_expert_is_zero_and_trained_output_is_bounded(self):
        torch.manual_seed(1)
        stem = FrozenTokenStem(32, 16)
        expert = PersonalFFNExpert(16, 24)
        hidden = stem(torch.randn(5, 32), torch.tensor([0, 1, 2, 0, 1]), torch.tensor([11, 1, 2, 3, 4]))
        fresh = expert(hidden)
        self.assertTrue(torch.allclose(fresh, torch.zeros_like(fresh)))
        with torch.no_grad():
            expert.down.weight.add_(torch.randn_like(expert.down.weight) * 100)
        changed = expert(hidden)
        self.assertLessEqual(float(changed.detach().norm(dim=-1).max()), 1.00001)


if __name__ == "__main__":
    unittest.main()
