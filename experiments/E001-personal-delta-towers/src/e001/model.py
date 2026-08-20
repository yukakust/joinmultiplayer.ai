"""Small, data-free building blocks for E001 Personal Delta Towers.

The experiment deliberately separates three concerns:

* :class:`SharedStem` turns a synthetic ``(specialty, key)`` pair into the
  three-token sequence ``[CLS, specialty, key]``.
* :class:`PersonalDeltaTower` compares a trainable personal branch with the
  corresponding frozen base branch and exposes only their bounded difference.
* :class:`SourceMerger` preserves the order of two expert capsules, merges
  them into a bounded update to the source state ``z0``, and maps that state
  to the four classes used by the Private World task.

No dataset assumptions live in this module.  In particular, callers pass
integer IDs to the stem and already-encoded stem states to a delta tower.
"""

from __future__ import annotations

import copy
from typing import Final

import torch
from torch import Tensor, nn


BASE_DEPTH: Final[int] = 24
ALLOWED_PERSONAL_DEPTHS: Final[tuple[int, ...]] = (6, 12, 24)


def _validate_model_width(d_model: int, nhead: int) -> None:
    if d_model <= 0:
        raise ValueError("d_model must be positive")
    if nhead <= 0 or d_model % nhead:
        raise ValueError("nhead must be positive and divide d_model exactly")


def _encoder_block(d_model: int, nhead: int, dim_feedforward: int) -> nn.Module:
    """Build a deterministic transformer block shared by all E001 branches."""

    return nn.TransformerEncoderLayer(
        d_model=d_model,
        nhead=nhead,
        dim_feedforward=dim_feedforward,
        dropout=0.0,
        activation="gelu",
        batch_first=True,
        norm_first=True,
    )


def sanitize_and_clip(capsule: Tensor, max_norm: float, eps: float = 1e-12) -> Tensor:
    """Replace non-finite values with zero and clip each capsule's L2 norm.

    Clipping is applied independently over the last dimension.  Norms are
    calculated in float32 so this helper is also safe for float16 activations.
    It is intentionally differentiable for finite values inside the boundary.
    """

    if max_norm <= 0:
        raise ValueError("max_norm must be positive")
    if eps <= 0:
        raise ValueError("eps must be positive")
    if capsule.ndim == 0:
        raise ValueError("capsule must have at least one dimension")

    finite = torch.where(torch.isfinite(capsule), capsule, torch.zeros_like(capsule))
    norms = torch.linalg.vector_norm(finite.float(), dim=-1, keepdim=True)
    scale = torch.clamp(float(max_norm) / norms.clamp_min(eps), max=1.0)
    return finite * scale.to(dtype=finite.dtype)


class SharedStem(nn.Module):
    """Encode ``[CLS, specialty, key]`` into a ``[batch, 3, d_model]`` sequence."""

    sequence_length: Final[int] = 3

    def __init__(
        self,
        specialty_vocab_size: int,
        key_vocab_size: int,
        d_model: int = 32,
        nhead: int = 4,
        dim_feedforward: int | None = None,
    ) -> None:
        super().__init__()
        _validate_model_width(d_model, nhead)
        if specialty_vocab_size <= 0 or key_vocab_size <= 0:
            raise ValueError("vocabulary sizes must be positive")

        feedforward = 4 * d_model if dim_feedforward is None else dim_feedforward
        if feedforward <= 0:
            raise ValueError("dim_feedforward must be positive")

        self.d_model = d_model
        self.specialty_embedding = nn.Embedding(specialty_vocab_size, d_model)
        self.key_embedding = nn.Embedding(key_vocab_size, d_model)
        self.cls_token = nn.Parameter(torch.empty(1, 1, d_model))
        self.position_embedding = nn.Parameter(
            torch.empty(1, self.sequence_length, d_model)
        )
        self.block = _encoder_block(d_model, nhead, feedforward)
        self.output_norm = nn.LayerNorm(d_model)

        nn.init.normal_(self.cls_token, mean=0.0, std=0.02)
        nn.init.normal_(self.position_embedding, mean=0.0, std=0.02)

    @staticmethod
    def _as_batch(ids: Tensor, name: str) -> Tensor:
        if ids.ndim == 0:
            ids = ids.unsqueeze(0)
        if ids.ndim != 1:
            raise ValueError(f"{name} must be a scalar or a one-dimensional batch")
        return ids.long()

    def forward(self, specialty_ids: Tensor, key_ids: Tensor) -> Tensor:
        specialty_ids = self._as_batch(specialty_ids, "specialty_ids")
        key_ids = self._as_batch(key_ids, "key_ids")
        if specialty_ids.shape != key_ids.shape:
            raise ValueError("specialty_ids and key_ids must have the same shape")

        batch_size = specialty_ids.shape[0]
        cls = self.cls_token.expand(batch_size, -1, -1)
        specialty = self.specialty_embedding(specialty_ids).unsqueeze(1)
        key = self.key_embedding(key_ids).unsqueeze(1)
        tokens = torch.cat((cls, specialty, key), dim=1)
        tokens = tokens + self.position_embedding
        return self.output_norm(self.block(tokens))


class BaseTowerTemplate(nn.Module):
    """The frozen 24-block reference whose prefixes seed personal towers."""

    depth: Final[int] = BASE_DEPTH

    def __init__(
        self,
        d_model: int = 32,
        nhead: int = 4,
        dim_feedforward: int | None = None,
    ) -> None:
        super().__init__()
        _validate_model_width(d_model, nhead)
        feedforward = 4 * d_model if dim_feedforward is None else dim_feedforward
        if feedforward <= 0:
            raise ValueError("dim_feedforward must be positive")

        self.d_model = d_model
        self.blocks = nn.ModuleList(
            _encoder_block(d_model, nhead, feedforward) for _ in range(self.depth)
        )
        # The base is a control, never an optimization target in E001.
        self.requires_grad_(False)

    def forward(self, hidden: Tensor, depth: int = BASE_DEPTH) -> Tensor:
        if hidden.ndim != 3 or hidden.shape[-1] != self.d_model:
            raise ValueError(
                f"hidden must have shape [batch, sequence, {self.d_model}]"
            )
        if not 1 <= depth <= self.depth:
            raise ValueError(f"depth must be between 1 and {self.depth}")

        state = hidden
        for block in self.blocks[:depth]:
            state = block(state)
        return state


class PersonalDeltaTower(nn.Module):
    """A trainable 6/12/24-block expert initialized from a frozen base prefix.

    ``raw_delta`` is ``personal_cls - base_cls``.  The public ``forward``
    applies a bias-free ABI projection and norm bound.  Consequently the
    canonical fresh tower returns the exact zero capsule (``z0``).
    """

    def __init__(
        self,
        base_template: BaseTowerTemplate,
        depth: int,
        abi_dim: int | None = None,
        max_capsule_norm: float = 1.0,
    ) -> None:
        super().__init__()
        if depth not in ALLOWED_PERSONAL_DEPTHS:
            raise ValueError(
                f"depth must be one of {ALLOWED_PERSONAL_DEPTHS}, got {depth}"
            )
        if max_capsule_norm <= 0:
            raise ValueError("max_capsule_norm must be positive")

        output_dim = abi_dim if abi_dim is not None else base_template.d_model
        if output_dim <= 0:
            raise ValueError("abi_dim must be positive")

        self.base_template = base_template
        # Be defensive if a caller constructed the base and changed flags.
        self.base_template.requires_grad_(False)
        self.depth = depth
        self.d_model = base_template.d_model
        self.abi_dim = output_dim
        self.max_capsule_norm = float(max_capsule_norm)

        self.personal_blocks = nn.ModuleList(
            copy.deepcopy(base_template.blocks[index]) for index in range(depth)
        )
        # deepcopy preserves requires_grad=False; personal parameters must learn.
        self.personal_blocks.requires_grad_(True)
        self.abi_projection = nn.Linear(self.d_model, self.abi_dim, bias=False)

    def _personal_forward(self, hidden: Tensor) -> Tensor:
        state = hidden
        for block in self.personal_blocks:
            state = block(state)
        return state

    def raw_delta(self, stem_hidden: Tensor) -> Tensor:
        """Return the unprojected personal-minus-base CLS representation."""

        if stem_hidden.ndim != 3 or stem_hidden.shape[-1] != self.d_model:
            raise ValueError(
                f"stem_hidden must have shape [batch, sequence, {self.d_model}]"
            )
        if stem_hidden.shape[1] < 1:
            raise ValueError("stem_hidden must contain a CLS token")

        base_cls = self.base_template(stem_hidden, depth=self.depth)[:, 0, :]
        personal_cls = self._personal_forward(stem_hidden)[:, 0, :]
        return personal_cls - base_cls

    def forward(self, stem_hidden: Tensor) -> Tensor:
        projected = self.abi_projection(self.raw_delta(stem_hidden))
        return sanitize_and_clip(projected, self.max_capsule_norm)


class SourceMerger(nn.Module):
    """Apply ``FinalLayers(z0 + Merge(first, second))``.

    Concatenation is intentional: ``(first, second)`` and ``(second, first)``
    are different inputs.  E001 can therefore encode roles such as upstream
    versus downstream expertise instead of silently treating experts as a set.
    The learned merge update is projected back to the source ABI width and
    norm-bounded before it is allowed to modify the trusted local ``z0`` path.
    """

    num_classes: Final[int] = 4

    def __init__(
        self,
        abi_dim: int,
        hidden_dim: int | None = None,
        max_update_norm: float = 1.0,
    ) -> None:
        super().__init__()
        if abi_dim <= 0:
            raise ValueError("abi_dim must be positive")
        width = hidden_dim if hidden_dim is not None else 2 * abi_dim
        if width <= 0:
            raise ValueError("hidden_dim must be positive")
        if max_update_norm <= 0:
            raise ValueError("max_update_norm must be positive")

        self.abi_dim = abi_dim
        self.max_update_norm = float(max_update_norm)
        self.merge_layers = nn.Sequential(
            nn.LayerNorm(2 * abi_dim),
            nn.Linear(2 * abi_dim, width),
            nn.GELU(),
            nn.Linear(width, abi_dim),
        )
        self.final_layers = nn.Sequential(
            nn.LayerNorm(abi_dim),
            nn.Linear(abi_dim, width),
            nn.GELU(),
            nn.Linear(width, self.num_classes),
        )

    def _validate_capsule(self, capsule: Tensor, name: str) -> None:
        expected = (self.abi_dim,)
        if capsule.ndim != 2 or capsule.shape[-1:] != expected:
            raise ValueError(f"{name} must have shape [batch, {self.abi_dim}]")

    def merge_update(self, first: Tensor, second: Tensor) -> Tensor:
        """Return the bounded, ordered expert update in source ABI space."""

        self._validate_capsule(first, "first")
        self._validate_capsule(second, "second")
        if first.shape[0] != second.shape[0]:
            raise ValueError("first and second must have the same batch size")

        ordered = torch.cat((first, second), dim=-1)
        learned_update = self.merge_layers(ordered)
        return sanitize_and_clip(learned_update, self.max_update_norm)

    def forward(self, z0: Tensor, first: Tensor, second: Tensor) -> Tensor:
        self._validate_capsule(z0, "z0")
        update = self.merge_update(first, second)
        if z0.shape[0] != update.shape[0]:
            raise ValueError("z0, first, and second must have the same batch size")

        source_state = z0 + update
        return self.final_layers(source_state)


__all__ = [
    "ALLOWED_PERSONAL_DEPTHS",
    "BASE_DEPTH",
    "BaseTowerTemplate",
    "PersonalDeltaTower",
    "SharedStem",
    "SourceMerger",
    "sanitize_and_clip",
]
