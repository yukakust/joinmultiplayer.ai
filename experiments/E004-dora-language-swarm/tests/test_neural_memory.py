import sys
import unittest
from pathlib import Path

import torch


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_neural_memory import NeuralMemoryPocket, SourceDecoder  # noqa: E402


class NeuralMemoryTests(unittest.TestCase):
    def test_capsule_and_decoder_shapes_are_finite(self):
        torch.manual_seed(1)
        pocket = NeuralMemoryPocket(input_dim=32, capsule_dim=16, slots=4)
        decoder = SourceDecoder(capsule_dim=16)
        capsule = pocket(torch.randn(3, 32))
        logits = decoder(capsule)
        self.assertEqual(capsule.shape, (3, 16))
        self.assertEqual(logits.shape, (3, 998))
        self.assertTrue(torch.isfinite(logits).all())


if __name__ == "__main__":
    unittest.main()
