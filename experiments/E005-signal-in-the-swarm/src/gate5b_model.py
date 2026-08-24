from __future__ import annotations

import copy
from dataclasses import dataclass

import torch
from torch import nn
from transformers.masking_utils import create_causal_mask, create_sliding_window_causal_mask


class DoRALinear(nn.Module):
    """A frozen linear layer plus a trainable low-rank direction and magnitude."""

    def __init__(self, base: nn.Linear, rank: int = 8, alpha: float = 16.0):
        super().__init__()
        self.in_features = base.in_features
        self.out_features = base.out_features
        self.rank = rank
        self.scaling = alpha / rank
        self.weight = nn.Parameter(base.weight.detach().clone(), requires_grad=False)
        self.bias = None if base.bias is None else nn.Parameter(base.bias.detach().clone(), requires_grad=False)
        self.lora_a = nn.Parameter(torch.empty(rank, self.in_features))
        self.lora_b = nn.Parameter(torch.zeros(self.out_features, rank))
        self.magnitude = nn.Parameter(torch.linalg.vector_norm(self.weight.float(), dim=1).to(self.weight.dtype))
        nn.init.kaiming_uniform_(self.lora_a, a=5**0.5)

    def effective_weight(self) -> torch.Tensor:
        direction = self.weight + (self.lora_b @ self.lora_a) * self.scaling
        norm = torch.linalg.vector_norm(direction.float(), dim=1, keepdim=True).to(direction.dtype).clamp_min(1e-6)
        return direction * (self.magnitude[:, None] / norm)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return nn.functional.linear(inputs, self.effective_weight(), self.bias)


TARGET_LINEAR_NAMES = {"q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"}


def inject_dora(module: nn.Module, rank: int = 8, alpha: float = 16.0) -> int:
    replaced = 0
    for name, child in list(module.named_children()):
        if isinstance(child, nn.Linear) and name in TARGET_LINEAR_NAMES:
            setattr(module, name, DoRALinear(child, rank=rank, alpha=alpha))
            replaced += 1
        else:
            replaced += inject_dora(child, rank=rank, alpha=alpha)
    return replaced


class BoundedDeltaMerger(nn.Module):
    def __init__(self, hidden_size: int, max_delta_ratio: float = 0.5):
        super().__init__()
        self.max_delta_ratio = max_delta_ratio
        self.gate = nn.Sequential(
            nn.Linear(hidden_size * 3, 128),
            nn.SiLU(),
            nn.Linear(128, 2),
        )
        self.cause_scale = nn.Parameter(torch.ones(hidden_size))
        self.safety_scale = nn.Parameter(torch.ones(hidden_size))

    def clip(self, delta: torch.Tensor, base: torch.Tensor) -> torch.Tensor:
        delta_norm = torch.linalg.vector_norm(delta.float(), dim=-1, keepdim=True)
        base_norm = torch.linalg.vector_norm(base.float(), dim=-1, keepdim=True).clamp_min(1e-6)
        maximum = base_norm * self.max_delta_ratio
        factor = torch.minimum(torch.ones_like(delta_norm), maximum / delta_norm.clamp_min(1e-6))
        return delta * factor.to(delta.dtype)

    def merge_update(self, base: torch.Tensor, cause_delta: torch.Tensor, safety_delta: torch.Tensor) -> torch.Tensor:
        cause = self.clip(cause_delta, base)
        safety = self.clip(safety_delta, base)
        gates = torch.sigmoid(self.gate(torch.cat((base, cause, safety), dim=-1)))
        return gates[..., 0:1] * cause * self.cause_scale + gates[..., 1:2] * safety * self.safety_scale

    def forward(self, base: torch.Tensor, cause_delta: torch.Tensor, safety_delta: torch.Tensor) -> torch.Tensor:
        return base + self.merge_update(base, cause_delta, safety_delta)


@dataclass
class TrackForward:
    logits: torch.Tensor
    base_middle: torch.Tensor
    cause_delta: torch.Tensor | None
    safety_delta: torch.Tensor | None
    merged_middle: torch.Tensor


class ParallelTrackQwen(nn.Module):
    """Qwen with one shared stem, two personal middle paths, and one shared tail."""

    def __init__(self, causal_lm: nn.Module, stem_end: int = 6, track_end: int = 22, rank: int = 8):
        super().__init__()
        if causal_lm.config.num_hidden_layers != 28:
            raise ValueError("Gate 5B is frozen for a 28-layer Qwen")
        if not (0 < stem_end < track_end < causal_lm.config.num_hidden_layers):
            raise ValueError("invalid layer split")
        self.config = causal_lm.config
        self.stem_end = stem_end
        self.track_end = track_end
        self.shared = causal_lm
        for parameter in self.shared.parameters():
            parameter.requires_grad = False
        middle = self.shared.model.layers[stem_end:track_end]
        self.cause_layers = nn.ModuleList(copy.deepcopy(middle))
        self.safety_layers = nn.ModuleList(copy.deepcopy(middle))
        cause_replaced = inject_dora(self.cause_layers, rank=rank)
        safety_replaced = inject_dora(self.safety_layers, rank=rank)
        if cause_replaced != safety_replaced or cause_replaced == 0:
            raise RuntimeError("DoRA injection failed")
        self.dora_modules_per_track = cause_replaced
        self.merger = BoundedDeltaMerger(self.config.hidden_size)
        self.freeze_all()

    def freeze_all(self) -> None:
        for parameter in self.parameters():
            parameter.requires_grad = False

    def set_trainable(self, part: str) -> None:
        self.freeze_all()
        if part == "cause":
            modules = self.cause_layers
        elif part == "safety":
            modules = self.safety_layers
        elif part == "merger":
            modules = self.merger
        else:
            raise ValueError(f"unknown trainable part: {part}")
        for name, parameter in modules.named_parameters():
            if part == "merger" or any(token in name for token in ("lora_a", "lora_b", "magnitude")):
                parameter.requires_grad = True

    def trainable_parameter_names(self) -> list[str]:
        return [name for name, parameter in self.named_parameters() if parameter.requires_grad]

    def _masks_and_positions(self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None):
        hidden = self.shared.model.embed_tokens(input_ids)
        position_ids = torch.arange(hidden.shape[1], device=hidden.device).unsqueeze(0)
        mask_kwargs = {
            "config": self.config,
            "inputs_embeds": hidden,
            "attention_mask": attention_mask,
            "past_key_values": None,
            "position_ids": position_ids,
        }
        masks = {"full_attention": create_causal_mask(**mask_kwargs)}
        if self.shared.model.has_sliding_layers:
            masks["sliding_attention"] = create_sliding_window_causal_mask(**mask_kwargs)
        position_embeddings = self.shared.model.rotary_emb(hidden, position_ids)
        return hidden, position_ids, masks, position_embeddings

    def _run_layers(self, layers, hidden, *, offset: int, masks, position_ids, position_embeddings):
        for local_index, layer in enumerate(layers):
            layer_index = offset + local_index
            hidden = layer(
                hidden,
                attention_mask=masks[self.config.layer_types[layer_index]],
                position_ids=position_ids,
                position_embeddings=position_embeddings,
                use_cache=False,
            )
        return hidden

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None, mode: str = "correct") -> TrackForward:
        hidden, position_ids, masks, position_embeddings = self._masks_and_positions(input_ids, attention_mask)
        stem = self._run_layers(
            self.shared.model.layers[: self.stem_end], hidden, offset=0, masks=masks,
            position_ids=position_ids, position_embeddings=position_embeddings,
        )
        base_middle = self._run_layers(
            self.shared.model.layers[self.stem_end : self.track_end], stem, offset=self.stem_end,
            masks=masks, position_ids=position_ids, position_embeddings=position_embeddings,
        )
        cause_delta = None
        safety_delta = None
        if mode in {"cause", "correct", "wrong_cause"}:
            cause_hidden = self._run_layers(
                self.cause_layers, stem, offset=self.stem_end, masks=masks,
                position_ids=position_ids, position_embeddings=position_embeddings,
            )
            cause_delta = cause_hidden - base_middle
        if mode in {"safety", "correct", "wrong_safety"}:
            safety_hidden = self._run_layers(
                self.safety_layers, stem, offset=self.stem_end, masks=masks,
                position_ids=position_ids, position_embeddings=position_embeddings,
            )
            safety_delta = safety_hidden - base_middle
        if mode == "base":
            merged = base_middle
        elif mode == "cause":
            merged = base_middle + self.merger.clip(cause_delta, base_middle)
        elif mode == "safety":
            merged = base_middle + self.merger.clip(safety_delta, base_middle)
        elif mode == "correct":
            merged = self.merger(base_middle, cause_delta, safety_delta)
        elif mode == "wrong_cause":
            merged = self.merger(base_middle, cause_delta, cause_delta)
        elif mode == "wrong_safety":
            merged = self.merger(base_middle, safety_delta, safety_delta)
        else:
            raise ValueError(f"unknown mode: {mode}")
        tail = self._run_layers(
            self.shared.model.layers[self.track_end :], merged, offset=self.track_end,
            masks=masks, position_ids=position_ids, position_embeddings=position_embeddings,
        )
        tail = self.shared.model.norm(tail)
        logits = self.shared.lm_head(tail)
        return TrackForward(logits, base_middle, cause_delta, safety_delta, merged)

    def adapter_state(self, part: str) -> dict[str, torch.Tensor]:
        prefix = {"cause": "cause_layers.", "safety": "safety_layers.", "merger": "merger."}[part]
        return {
            name: tensor.detach().cpu()
            for name, tensor in self.state_dict().items()
            if name.startswith(prefix) and (
                part == "merger" or any(token in name for token in ("lora_a", "lora_b", "magnitude"))
            )
        }
