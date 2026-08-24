import importlib.util
import unittest
from pathlib import Path

import torch
from torch import nn


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/gate5b_model.py"
SPEC = importlib.util.spec_from_file_location("gate5b_model", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Gate5BModelTests(unittest.TestCase):
    def test_fresh_dora_is_exactly_the_frozen_linear(self):
        torch.manual_seed(3)
        base = nn.Linear(7, 5, bias=True)
        dora = MODULE.DoRALinear(base, rank=2, alpha=4)
        inputs = torch.randn(3, 7)
        torch.testing.assert_close(dora(inputs), base(inputs), atol=2e-6, rtol=2e-6)

    def test_dora_optimizer_changes_only_personal_parameters(self):
        torch.manual_seed(4)
        base = nn.Linear(6, 4, bias=False)
        dora = MODULE.DoRALinear(base, rank=2)
        frozen = dora.weight.detach().clone()
        optimizer = torch.optim.AdamW([dora.lora_a, dora.lora_b, dora.magnitude], lr=0.1)
        loss = dora(torch.randn(5, 6)).square().mean()
        loss.backward(); optimizer.step()
        torch.testing.assert_close(dora.weight, frozen)
        self.assertGreater(torch.linalg.vector_norm(dora.lora_b).item(), 0)

    def test_bounded_merger_uses_exact_source_equation(self):
        torch.manual_seed(5)
        merger = MODULE.BoundedDeltaMerger(8, max_delta_ratio=0.25)
        base = torch.randn(2, 3, 8)
        cause = torch.randn(2, 3, 8) * 100
        safety = torch.randn(2, 3, 8) * 100
        update = merger.merge_update(base, cause, safety)
        torch.testing.assert_close(merger(base, cause, safety), base + update)
        for clipped in (merger.clip(cause, base), merger.clip(safety, base)):
            ratio = torch.linalg.vector_norm(clipped, dim=-1) / torch.linalg.vector_norm(base, dim=-1).clamp_min(1e-6)
            self.assertLessEqual(ratio.max().item(), 0.25001)

    def test_wrong_pair_reuses_one_logical_track_not_a_replica(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("self.merger(base_middle, cause_delta, cause_delta)", source)
        self.assertIn("self.merger(base_middle, safety_delta, safety_delta)", source)

    def test_architecture_has_real_separate_middle_modules(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("self.cause_layers = nn.ModuleList(copy.deepcopy(middle))", source)
        self.assertIn("self.safety_layers = nn.ModuleList(copy.deepcopy(middle))", source)
        self.assertIn("cause_hidden - base_middle", source)
        self.assertIn("safety_hidden - base_middle", source)


if __name__ == "__main__":
    unittest.main()
