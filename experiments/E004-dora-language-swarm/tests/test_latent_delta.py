import sys
import unittest
from pathlib import Path

import torch
from torch.nn import functional as F


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_latent_delta import CommonTower, FinalLayers, PersonalDelta  # noqa: E402


class LatentDeltaTests(unittest.TestCase):
    def test_fresh_delta_is_zero_bounded_and_z0_enters_equation(self):
        torch.manual_seed(1)
        common = CommonTower(32, 16).eval().requires_grad_(False)
        pocket = PersonalDelta(common)
        final = FinalLayers(16)
        value = torch.randn(4, 32)
        delta = pocket(value)
        self.assertTrue(torch.allclose(delta, torch.zeros_like(delta)))
        z0 = F.normalize(common(value), dim=-1)
        self.assertFalse(torch.allclose(final(z0, delta), final(torch.zeros_like(z0), delta)))

    def test_adversarial_delta_is_norm_bounded(self):
        torch.manual_seed(2)
        common = CommonTower(32, 16).eval().requires_grad_(False)
        pocket = PersonalDelta(common)
        with torch.no_grad():
            for parameter in pocket.personal.parameters():
                parameter.add_(torch.randn_like(parameter) * 1000)
        delta = pocket(torch.randn(8, 32))
        self.assertLessEqual(float(delta.norm(dim=-1).max()), 1.00001)


if __name__ == "__main__":
    unittest.main()
