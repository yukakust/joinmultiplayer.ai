from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn
from transformers.masking_utils import create_causal_mask, create_sliding_window_causal_mask

from gate5b_model import ParallelTrackQwen


SHELF_MODES = {
    "correct_shelves",
    "cause_only",
    "safety_only",
    "two_cause",
    "two_safety",
    "swapped",
    "empty",
}


class LowRankShelfProjector(nn.Module):
    def __init__(self, hidden_size: int, rank: int = 128):
        super().__init__()
        self.down = nn.Linear(hidden_size, rank, bias=False)
        self.up = nn.Linear(rank, hidden_size, bias=False)
        nn.init.kaiming_uniform_(self.down.weight, a=5**0.5)
        nn.init.zeros_(self.up.weight)

    def forward(self, delta: torch.Tensor) -> torch.Tensor:
        return self.up(torch.nn.functional.silu(self.down(delta)))


class SeparateShelfReader(nn.Module):
    """Keep two role-labelled neural contributions in two sequence positions."""

    def __init__(self, hidden_size: int, rank: int = 128, max_delta_ratio: float = 0.5):
        super().__init__()
        self.max_delta_ratio = max_delta_ratio
        self.cause_projector = LowRankShelfProjector(hidden_size, rank)
        self.safety_projector = LowRankShelfProjector(hidden_size, rank)
        self.shelf_types = nn.Parameter(torch.zeros(2, hidden_size))

    def clip(self, delta: torch.Tensor, base: torch.Tensor) -> torch.Tensor:
        delta_norm = torch.linalg.vector_norm(delta.float(), dim=-1, keepdim=True)
        base_norm = torch.linalg.vector_norm(base.float(), dim=-1, keepdim=True).clamp_min(1e-6)
        maximum = base_norm * self.max_delta_ratio
        factor = torch.minimum(torch.ones_like(delta_norm), maximum / delta_norm.clamp_min(1e-6))
        return delta * factor.to(delta.dtype)

    def forward(
        self,
        base_last: torch.Tensor,
        cause_delta: torch.Tensor,
        safety_delta: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        cause = self.clip(cause_delta, base_last)
        safety = self.clip(safety_delta, base_last)
        cause_shelf = base_last + self.cause_projector(cause) + self.shelf_types[0]
        safety_shelf = base_last + self.safety_projector(safety) + self.shelf_types[1]
        return cause_shelf, safety_shelf


@dataclass
class ShelfForward:
    next_logits: torch.Tensor
    cause_shelf: torch.Tensor
    safety_shelf: torch.Tensor
    cause_delta: torch.Tensor
    safety_delta: torch.Tensor


class SeparateShelfQwen(ParallelTrackQwen):
    def __init__(self, causal_lm: nn.Module, stem_end: int = 6, track_end: int = 22, track_rank: int = 8, shelf_rank: int = 128):
        super().__init__(causal_lm, stem_end=stem_end, track_end=track_end, rank=track_rank)
        self.shelf_reader = SeparateShelfReader(self.config.hidden_size, rank=shelf_rank)
        self.freeze_all()

    def set_shelf_trainable(self) -> None:
        self.freeze_all()
        for parameter in self.shelf_reader.parameters():
            parameter.requires_grad = True

    def shelf_state(self) -> dict[str, torch.Tensor]:
        return {
            name: tensor.detach().cpu()
            for name, tensor in self.state_dict().items()
            if name.startswith("shelf_reader.")
        }

    def _select_shelves(self, cause: torch.Tensor, safety: torch.Tensor, mode: str) -> tuple[torch.Tensor, torch.Tensor]:
        if mode not in SHELF_MODES:
            raise ValueError(f"unknown shelf mode: {mode}")
        zero = torch.zeros_like(cause)
        return {
            "correct_shelves": (cause, safety),
            "cause_only": (cause, zero),
            "safety_only": (zero, safety),
            "two_cause": (cause, cause),
            "two_safety": (safety, safety),
            "swapped": (safety, cause),
            "empty": (zero, zero),
        }[mode]

    def forward_shelves(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
        mode: str = "correct_shelves",
    ) -> ShelfForward:
        if attention_mask is None:
            attention_mask = torch.ones_like(input_ids)
        with torch.no_grad():
            hidden, position_ids, masks, position_embeddings = self._masks_and_positions(input_ids, attention_mask)
            stem = self._run_layers(
                self.shared.model.layers[: self.stem_end], hidden, offset=0, masks=masks,
                position_ids=position_ids, position_embeddings=position_embeddings,
            )
            base_middle = self._run_layers(
                self.shared.model.layers[self.stem_end : self.track_end], stem, offset=self.stem_end,
                masks=masks, position_ids=position_ids, position_embeddings=position_embeddings,
            )
            cause_hidden = self._run_layers(
                self.cause_layers, stem, offset=self.stem_end, masks=masks,
                position_ids=position_ids, position_embeddings=position_embeddings,
            )
            safety_hidden = self._run_layers(
                self.safety_layers, stem, offset=self.stem_end, masks=masks,
                position_ids=position_ids, position_embeddings=position_embeddings,
            )
            row_index = torch.arange(input_ids.shape[0], device=input_ids.device)
            physical_positions = torch.arange(input_ids.shape[1], device=input_ids.device).unsqueeze(0)
            last_index = physical_positions.masked_fill(attention_mask == 0, -1).max(dim=1).values
            last_position = attention_mask.sum(dim=-1).long() - 1
            base_last = base_middle[row_index, last_index]
            cause_delta = cause_hidden[row_index, last_index] - base_last
            safety_delta = safety_hidden[row_index, last_index] - base_last

        cause_input, safety_input = self._select_shelves(cause_delta, safety_delta, mode)
        cause_shelf, safety_shelf = self.shelf_reader(base_last, cause_input, safety_input)
        expanded = torch.cat((base_middle, cause_shelf[:, None, :], safety_shelf[:, None, :]), dim=1)
        shelf_attention = torch.cat(
            (attention_mask, torch.ones((attention_mask.shape[0], 2), dtype=attention_mask.dtype, device=attention_mask.device)),
            dim=1,
        )
        original_positions = torch.arange(input_ids.shape[1], device=input_ids.device).unsqueeze(0).expand(input_ids.shape[0], -1)
        shelf_positions = torch.stack((last_position + 1, last_position + 2), dim=1)
        tail_positions = torch.cat((original_positions, shelf_positions), dim=1)
        mask_kwargs = {
            "config": self.config,
            "inputs_embeds": expanded,
            "attention_mask": shelf_attention,
            "past_key_values": None,
            "position_ids": tail_positions,
        }
        tail_masks = {"full_attention": create_causal_mask(**mask_kwargs)}
        if self.shared.model.has_sliding_layers:
            tail_masks["sliding_attention"] = create_sliding_window_causal_mask(**mask_kwargs)
        tail_position_embeddings = self.shared.model.rotary_emb(expanded, tail_positions)
        tail = self._run_layers(
            self.shared.model.layers[self.track_end :], expanded, offset=self.track_end,
            masks=tail_masks, position_ids=tail_positions, position_embeddings=tail_position_embeddings,
        )
        tail = self.shared.model.norm(tail)
        next_logits = self.shared.lm_head(tail[:, -1])
        return ShelfForward(next_logits, cause_shelf, safety_shelf, cause_delta, safety_delta)
