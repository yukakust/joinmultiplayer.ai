from __future__ import annotations

import sys
import unittest
from pathlib import Path

import torch


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT_ROOT / "src"))

from e001.model import (  # noqa: E402
    BaseTowerTemplate,
    PersonalDeltaTower,
    SharedStem,
    SourceMerger,
    sanitize_and_clip,
)


class DeltaTowerTests(unittest.TestCase):
    def setUp(self) -> None:
        torch.manual_seed(7)
        self.tiny_base = BaseTowerTemplate(
            d_model=8, nhead=2, dim_feedforward=16
        )

    def test_shared_stem_emits_three_tokens(self) -> None:
        stem = SharedStem(
            specialty_vocab_size=5,
            key_vocab_size=11,
            d_model=8,
            nhead=2,
            dim_feedforward=16,
        )

        hidden = stem(torch.tensor([0, 4]), torch.tensor([3, 10]))

        self.assertEqual(hidden.shape, (2, 3, 8))
        self.assertTrue(torch.isfinite(hidden).all())

    def test_fresh_tower_has_canonical_zero_delta(self) -> None:
        for depth in (6, 12, 24):
            with self.subTest(depth=depth):
                tower = PersonalDeltaTower(
                    self.tiny_base,
                    depth=depth,
                    abi_dim=5,
                    max_capsule_norm=0.75,
                )
                # Test train mode too: E001 blocks deliberately use zero dropout.
                tower.train()
                hidden = torch.randn(3, 3, 8)

                raw = tower.raw_delta(hidden)
                capsule = tower(hidden)

                # Separate but identical transformer passes can differ by a few
                # float32 ULPs depending on the selected attention kernel.
                torch.testing.assert_close(
                    raw, torch.zeros_like(raw), atol=2e-6, rtol=0.0
                )
                torch.testing.assert_close(
                    capsule, torch.zeros_like(capsule), atol=2e-6, rtol=0.0
                )
                self.assertEqual(capsule.shape, (3, 5))
                self.assertIsNone(tower.abi_projection.bias)

    def test_only_declared_personal_depths_are_allowed(self) -> None:
        for bad_depth in (0, 5, 7, 23, 25):
            with self.subTest(depth=bad_depth):
                with self.assertRaisesRegex(ValueError, "depth must be one of"):
                    PersonalDeltaTower(self.tiny_base, depth=bad_depth)

    def test_base_is_frozen_and_personal_branch_is_trainable(self) -> None:
        tower = PersonalDeltaTower(self.tiny_base, depth=6, abi_dim=4)

        self.assertEqual(len(self.tiny_base.blocks), 24)
        self.assertEqual(len(tower.personal_blocks), 6)
        self.assertTrue(
            all(not parameter.requires_grad for parameter in self.tiny_base.parameters())
        )
        self.assertTrue(
            all(
                parameter.requires_grad
                for parameter in tower.personal_blocks.parameters()
            )
        )
        self.assertTrue(
            all(
                parameter.requires_grad
                for parameter in tower.abi_projection.parameters()
            )
        )

        for base_block, personal_block in zip(
            self.tiny_base.blocks[: tower.depth], tower.personal_blocks, strict=True
        ):
            for base_parameter, personal_parameter in zip(
                base_block.parameters(), personal_block.parameters(), strict=True
            ):
                self.assertTrue(torch.equal(base_parameter, personal_parameter))
                self.assertNotEqual(
                    base_parameter.data_ptr(), personal_parameter.data_ptr()
                )

    def test_optimizer_updates_personal_branch_but_not_base(self) -> None:
        tower = PersonalDeltaTower(self.tiny_base, depth=6, abi_dim=4)
        base_before = [parameter.detach().clone() for parameter in self.tiny_base.parameters()]
        personal_before = [
            parameter.detach().clone() for parameter in tower.personal_blocks.parameters()
        ]
        optimizer = torch.optim.SGD(
            (parameter for parameter in tower.parameters() if parameter.requires_grad),
            lr=0.01,
        )

        capsule = tower(torch.randn(2, 3, 8))
        capsule.sum().backward()
        optimizer.step()

        self.assertTrue(
            all(
                torch.equal(before, after)
                for before, after in zip(
                    base_before, self.tiny_base.parameters(), strict=True
                )
            )
        )
        self.assertTrue(
            any(
                not torch.equal(before, after)
                for before, after in zip(
                    personal_before, tower.personal_blocks.parameters(), strict=True
                )
            )
        )

    def test_sanitize_and_clip_replaces_nonfinite_and_bounds_each_row(self) -> None:
        capsule = torch.tensor(
            [
                [3.0, 4.0, 0.0],
                [float("nan"), float("inf"), float("-inf")],
                [0.1, 0.2, 0.2],
            ]
        )

        clipped = sanitize_and_clip(capsule, max_norm=2.0)

        self.assertTrue(torch.isfinite(clipped).all())
        self.assertTrue(torch.allclose(clipped[0], torch.tensor([1.2, 1.6, 0.0])))
        self.assertTrue(torch.equal(clipped[1], torch.zeros(3)))
        self.assertTrue(torch.equal(clipped[2], capsule[2]))
        self.assertTrue(
            torch.all(torch.linalg.vector_norm(clipped, dim=-1) <= 2.0 + 1e-6)
        )

    def test_source_merger_consumes_two_ordered_capsules(self) -> None:
        torch.manual_seed(19)
        merger = SourceMerger(abi_dim=5, hidden_dim=7, max_update_norm=0.4)
        z0 = torch.randn(4, 5)
        first = torch.randn(4, 5)
        second = torch.randn(4, 5)

        logits = merger(z0, first, second)
        reversed_logits = merger(z0, second, first)
        update = merger.merge_update(first, second)
        expected = merger.final_layers(z0 + update)

        self.assertEqual(logits.shape, (4, 4))
        self.assertTrue(torch.isfinite(logits).all())
        torch.testing.assert_close(logits, expected)
        self.assertTrue(
            torch.all(torch.linalg.vector_norm(update, dim=-1) <= 0.4 + 1e-6)
        )
        self.assertFalse(torch.allclose(logits, reversed_logits))

    def test_source_merger_uses_local_z0(self) -> None:
        torch.manual_seed(23)
        merger = SourceMerger(abi_dim=5, hidden_dim=9)
        first = torch.randn(3, 5)
        second = torch.randn(3, 5)
        z0 = torch.zeros(3, 5)
        changed_z0 = z0.clone()
        changed_z0[:, 0] = 0.5

        without_local_signal = merger(z0, first, second)
        with_local_signal = merger(changed_z0, first, second)

        self.assertFalse(torch.allclose(without_local_signal, with_local_signal))

    def test_source_merger_validates_all_three_abi_inputs(self) -> None:
        merger = SourceMerger(abi_dim=5, hidden_dim=7)
        valid = torch.zeros(2, 5)

        with self.assertRaisesRegex(ValueError, "z0 must have shape"):
            merger(torch.zeros(2, 4), valid, valid)
        with self.assertRaisesRegex(ValueError, "first must have shape"):
            merger(valid, torch.zeros(2, 4), valid)
        with self.assertRaisesRegex(ValueError, "same batch size"):
            merger(valid, valid, torch.zeros(3, 5))


if __name__ == "__main__":
    unittest.main()
