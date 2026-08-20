"""Train and evaluate the deterministic E001 Personal Delta Tower pilot.

This runner intentionally keeps every boundary visible.  Pocket i capsules are
computed and buffered before the source merger runs, top-2 candidates are
different logical experts, and an incomplete primary contribution is never
read by the merger.  The synthetic Private World makes every answer auditable.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import random
import resource
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from .artifacts import (
    environment_record,
    git_revision,
    run_id,
    utc_timestamp,
    write_json,
    write_jsonl,
)
from .data import (
    SPECIALTIES,
    FactRef,
    PrivateWorldTask,
    TaskSplits,
    build_private_world,
    generate_tasks,
    split_tasks_by_keys,
)
from .model import (
    BaseTowerTemplate,
    PersonalDeltaTower,
    SharedStem,
    SourceMerger,
    sanitize_and_clip,
)
from .routing import (
    ExpertContribution,
    LogicalExpert,
    TopTwoRouter,
    select_first_complete,
)


@dataclass(slots=True)
class TrainedPocketI:
    logical_id: str
    specialty: str
    depth: int
    tower: PersonalDeltaTower
    capsules: dict[str, Tensor]
    validation_quality: float
    stats: dict[str, Any]


def _development_gate_defaults() -> dict[str, float]:
    """Visible convenience thresholds; locked configs must state their own."""

    return {
        "fresh_delta_max": 2e-6,
        "collective_lift_min": 0.10,
        "macro_collective_lift_min": 0.10,
        "causal_loss_min": 0.10,
        "backup_loss_max": 0.10,
        "z0_norm_error_max": 1e-6,
    }


def _repo_root() -> Path:
    source = Path(__file__).resolve()
    for candidate in source.parents:
        if (candidate / ".git").exists():
            return candidate
    # The Docker image contains the experiment rather than the full repository.
    return source.parents[2]


def _stable_fraction(value: str) -> float:
    integer = int.from_bytes(sha256(value.encode("utf-8")).digest()[:8], "big")
    return integer / 2**64


def _json_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _seed_everything(seed: int, *, threads: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(max(1, threads))
    torch.use_deterministic_algorithms(True)


def _canonical_targets(bits: Tensor, abi_dim: int) -> Tensor:
    """The neural ABI: bit 0 and bit 1 have the same code for every pocket i."""

    if abi_dim < 2:
        raise ValueError("E001 requires abi_dim >= 2")
    target = torch.zeros((bits.shape[0], abi_dim), dtype=torch.float32)
    target[torch.arange(bits.shape[0]), bits.long()] = 1.0
    return target


def _cached_capsule(
    tower: PersonalDeltaTower,
    stem_hidden: Tensor,
    base_cls: Tensor,
) -> Tensor:
    """Equivalent to ``tower(stem_hidden)`` with the frozen base precomputed."""

    personal_cls = tower._personal_forward(stem_hidden)[:, 0, :]
    raw_delta = personal_cls - base_cls
    projected = tower.abi_projection(raw_delta)
    return sanitize_and_clip(projected, tower.max_capsule_norm)


def _accuracy(predictions: Sequence[int], labels: Sequence[int]) -> float:
    if len(predictions) != len(labels):
        raise ValueError("predictions and labels must have equal length")
    if not labels:
        return 0.0
    return sum(int(pred == label) for pred, label in zip(predictions, labels)) / len(
        labels
    )


def _accuracy_breakdown(
    predictions: Sequence[int], labels: Sequence[int]
) -> dict[str, Any]:
    per_class: dict[str, dict[str, float | int | None]] = {}
    present_accuracies: list[float] = []
    for class_id in range(4):
        indices = [index for index, label in enumerate(labels) if label == class_id]
        correct = sum(predictions[index] == class_id for index in indices)
        class_accuracy = correct / len(indices) if indices else None
        if class_accuracy is not None:
            present_accuracies.append(class_accuracy)
        per_class[str(class_id)] = {
            "tasks": len(indices),
            "correct": correct,
            "accuracy": class_accuracy,
        }
    return {
        "micro_accuracy": _accuracy(predictions, labels),
        "macro_accuracy": (
            sum(present_accuracies) / len(present_accuracies)
            if present_accuracies
            else 0.0
        ),
        "macro_definition": "unweighted mean of accuracies for classes present in this split",
        "per_class": per_class,
    }


def _fact_key_id(ref: FactRef) -> int:
    try:
        return int(ref.key.rsplit("-", 1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"unsupported Private World key: {ref.key!r}") from exc


def _validation_keys(
    tasks: Sequence[PrivateWorldTask], specialty: str, fallback: Iterable[str]
) -> tuple[str, ...]:
    keys: set[str] = set()
    for task in tasks:
        if task.first.specialty == specialty:
            keys.add(task.first.key)
        if task.second.specialty == specialty:
            keys.add(task.second.key)
    return tuple(sorted(keys)) or tuple(sorted(fallback))


def _train_one_expert(
    *,
    logical_id: str,
    specialty: str,
    depth: int,
    expert_seed: int,
    stem_hidden: Tensor,
    base_cls: Tensor,
    keys: Sequence[str],
    bits: Tensor,
    validation_keys: Sequence[str],
    base: BaseTowerTemplate,
    abi_dim: int,
    max_delta_norm: float,
    steps: int,
    learning_rate: float,
) -> TrainedPocketI:
    torch.manual_seed(expert_seed)
    tower = PersonalDeltaTower(
        base,
        depth=depth,
        abi_dim=abi_dim,
        max_capsule_norm=max_delta_norm,
    )
    tower.eval()
    with torch.no_grad():
        fresh = tower(stem_hidden)
        fresh_max_norm = float(torch.linalg.vector_norm(fresh, dim=-1).max().item())

    parameters = list(tower.personal_blocks.parameters()) + list(
        tower.abi_projection.parameters()
    )
    optimizer = torch.optim.AdamW(parameters, lr=learning_rate, weight_decay=1e-4)
    targets = _canonical_targets(bits, abi_dim)
    final_loss = math.nan
    tower.train()
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        capsules = _cached_capsule(tower, stem_hidden, base_cls)
        classification = F.cross_entropy(capsules[:, :2] * 4.0, bits)
        alignment = F.mse_loss(capsules, targets) * abi_dim
        loss = classification + 0.25 * alignment
        loss.backward()
        torch.nn.utils.clip_grad_norm_(parameters, 1.0)
        optimizer.step()
        final_loss = float(loss.detach().item())

    tower.eval()
    with torch.no_grad():
        learned = _cached_capsule(tower, stem_hidden, base_cls).detach().clone()
    predictions = learned[:, :2].argmax(dim=-1)
    all_accuracy = float((predictions == bits).float().mean().item())
    key_to_index = {key: index for index, key in enumerate(keys)}
    validation_indices = torch.tensor(
        [key_to_index[key] for key in validation_keys], dtype=torch.long
    )
    validation_accuracy = float(
        (predictions[validation_indices] == bits[validation_indices])
        .float()
        .mean()
        .item()
    )
    capsule_map = {key: learned[index] for index, key in enumerate(keys)}
    stats = {
        "logical_id": logical_id,
        "specialty": specialty,
        "depth": depth,
        "seed": expert_seed,
        "train_steps": steps,
        "final_loss": final_loss,
        "fact_accuracy": all_accuracy,
        "held_out_task_reference_accuracy": validation_accuracy,
        "validation_reference_count": len(validation_keys),
        "fresh_max_delta_norm": fresh_max_norm,
        "mean_learned_capsule_norm": float(
            torch.linalg.vector_norm(learned, dim=-1).mean().item()
        ),
        "trainable_parameters": sum(parameter.numel() for parameter in parameters),
    }
    return TrainedPocketI(
        logical_id=logical_id,
        specialty=specialty,
        depth=depth,
        tower=tower,
        capsules=capsule_map,
        validation_quality=validation_accuracy,
        stats=stats,
    )


def _completion_for_role(
    *,
    task_id: str,
    role_index: int,
    ref: FactRef,
    router: TopTwoRouter,
    trained: Mapping[str, TrainedPocketI],
    failure_probability: float,
    failure_seed: int,
    force_primary_failure: bool,
    poison_variant: int,
) -> tuple[Tensor, dict[str, Any]]:
    route = router.route_specialty(ref.specialty)
    primary_meta, backup_meta = route.candidates
    primary_capsule = trained[primary_meta.logical_id].capsules[ref.key]
    backup_capsule = trained[backup_meta.logical_id].capsules[ref.key]
    primary_fails = force_primary_failure or (
        _stable_fraction(f"{failure_seed}:{task_id}:{role_index}:primary")
        < failure_probability
    )

    if primary_fails:
        # Deliberately make the buffered partial state visibly unsafe.  The
        # completion gate must skip it atomically and select only the backup.
        if poison_variant == 1:
            poison = torch.full_like(primary_capsule, 123_456.0)
        elif poison_variant == 2:
            poison = torch.arange(
                primary_capsule.numel(), dtype=primary_capsule.dtype
            ).reshape_as(primary_capsule) - 98_765.0
        else:
            raise ValueError("poison_variant must be 1 or 2")
        primary = ExpertContribution.incomplete(
            primary_meta.logical_id,
            ref.specialty,
            partial_payload=poison,
        )
        poison_hash = _json_hash(poison.tolist())
    else:
        primary = ExpertContribution.complete(
            primary_meta.logical_id, ref.specialty, primary_capsule
        )
        poison_hash = None
    backup = ExpertContribution.complete(
        backup_meta.logical_id, ref.specialty, backup_capsule
    )
    selected = select_first_complete((primary, backup))
    if selected is None:
        raise RuntimeError(f"no complete pocket i for {task_id}/{ref.specialty}")
    payload = selected.payload
    if not isinstance(payload, Tensor):
        raise TypeError("E001 expert payload must be a torch tensor")
    audit = {
        "specialty": ref.specialty,
        "key": ref.key,
        "candidates": [primary_meta.logical_id, backup_meta.logical_id],
        "candidate_completed": [primary.completed, backup.completed],
        "primary_failed": primary_fails,
        "selected": selected.logical_id,
        "selected_complete": selected.completed,
        "partial_payload_merged": False,
        "partial_poison_variant": poison_variant if primary_fails else None,
        "partial_poison_sha256": poison_hash,
    }
    return payload, audit


def _task_capsules(
    task: PrivateWorldTask,
    *,
    router: TopTwoRouter,
    trained: Mapping[str, TrainedPocketI],
    failure_probability: float,
    failure_seed: int,
    force_primary_failure: bool = False,
    poison_variant: int = 1,
) -> tuple[Tensor, Tensor, tuple[dict[str, Any], dict[str, Any]]]:
    first, first_audit = _completion_for_role(
        task_id=task.task_id,
        role_index=0,
        ref=task.first,
        router=router,
        trained=trained,
        failure_probability=failure_probability,
        failure_seed=failure_seed,
        force_primary_failure=force_primary_failure,
        poison_variant=poison_variant,
    )
    second, second_audit = _completion_for_role(
        task_id=task.task_id,
        role_index=1,
        ref=task.second,
        router=router,
        trained=trained,
        failure_probability=failure_probability,
        failure_seed=failure_seed,
        force_primary_failure=force_primary_failure,
        poison_variant=poison_variant,
    )
    return first, second, (first_audit, second_audit)


def _trusted_source_z0(first_cls: Tensor, second_cls: Tensor) -> Tensor:
    """Fixed order-aware source ABI: Normalize(I·first + P2·second).

    ``P2`` is the fixed cyclic coordinate permutation implemented by
    ``torch.roll(..., 1)``.  The transform is orthogonal, label-free, and has
    no parameters.  Swapping task roles therefore changes the local state.
    """

    if first_cls.shape != second_cls.shape or first_cls.ndim < 1:
        raise ValueError("source CLS tensors must have the same non-scalar shape")
    if first_cls.shape[-1] < 2:
        raise ValueError("source ABI needs at least two coordinates")
    combined = first_cls + torch.roll(second_cls, shifts=1, dims=-1)
    return F.normalize(combined, dim=-1).detach()


def _features_for_tasks(
    tasks: Sequence[PrivateWorldTask],
    *,
    router: TopTwoRouter,
    trained: Mapping[str, TrainedPocketI],
    failure_probability: float,
    failure_seed: int,
    source_cls: Mapping[tuple[str, str], Tensor],
    force_primary_failure: bool = False,
    poison_variant: int = 1,
) -> tuple[
    Tensor,
    Tensor,
    Tensor,
    Tensor,
    list[tuple[dict[str, Any], dict[str, Any]]],
]:
    source_states: list[Tensor] = []
    first_capsules: list[Tensor] = []
    second_capsules: list[Tensor] = []
    labels: list[int] = []
    audits: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for task in tasks:
        first, second, audit = _task_capsules(
            task,
            router=router,
            trained=trained,
            failure_probability=failure_probability,
            failure_seed=failure_seed,
            force_primary_failure=force_primary_failure,
            poison_variant=poison_variant,
        )
        # Fixed, source-owned ABI transform.  It sees no label and has no
        # trainable parameters; normalization keeps a bounded merge update
        # comparable to the local path instead of drowning in ||base||≈sqrt(d).
        z0 = _trusted_source_z0(
            source_cls[(task.first.specialty, task.first.key)],
            source_cls[(task.second.specialty, task.second.key)],
        )
        source_states.append(z0)
        first_capsules.append(first)
        second_capsules.append(second)
        labels.append(task.answer_class)
        audits.append(audit)
    return (
        torch.stack(source_states).detach(),
        torch.stack(first_capsules),
        torch.stack(second_capsules),
        torch.tensor(labels, dtype=torch.long),
        audits,
    )


def _train_heads(
    *,
    z0: Tensor,
    first: Tensor,
    second: Tensor,
    control_first: Tensor,
    control_second: Tensor,
    labels: Tensor,
    abi_dim: int,
    hidden_dim: int,
    steps: int,
    learning_rate: float,
    seed: int,
) -> tuple[dict[str, SourceMerger], Tensor, dict[str, float]]:
    torch.manual_seed(seed)
    heads = {
        "pdt": SourceMerger(abi_dim=abi_dim, hidden_dim=hidden_dim),
        "pdt_without_z0": SourceMerger(abi_dim=abi_dim, hidden_dim=hidden_dim),
        "base_only": SourceMerger(abi_dim=abi_dim, hidden_dim=hidden_dim),
        "fresh_clones": SourceMerger(abi_dim=abi_dim, hidden_dim=hidden_dim),
        "single_first": SourceMerger(abi_dim=abi_dim, hidden_dim=hidden_dim),
        "single_second": SourceMerger(abi_dim=abi_dim, hidden_dim=hidden_dim),
    }
    # Learning four free logits is the strongest possible no-input baseline:
    # it converges to the empirical class prior without pretending to know a fact.
    prior_logits = nn.Parameter(torch.zeros(4))
    parameters = [
        parameter for head in heads.values() for parameter in head.parameters()
    ] + [prior_logits]
    optimizer = torch.optim.AdamW(parameters, lr=learning_rate, weight_decay=1e-4)
    generator = torch.Generator().manual_seed(seed + 1)
    batch_size = min(256, labels.shape[0])
    losses: dict[str, float] = {}
    for _ in range(steps):
        if batch_size == labels.shape[0]:
            indices = torch.arange(labels.shape[0])
        else:
            indices = torch.randint(
                labels.shape[0], (batch_size,), generator=generator
            )
        batch_first = first[indices]
        batch_second = second[indices]
        batch_control_first = control_first[indices]
        batch_control_second = control_second[indices]
        batch_z0 = z0[indices]
        batch_labels = labels[indices]
        zero = torch.zeros_like(batch_first)
        optimizer.zero_grad(set_to_none=True)
        pdt_loss = F.cross_entropy(
            heads["pdt"](batch_z0, batch_first, batch_second), batch_labels
        )
        pdt_without_z0_loss = F.cross_entropy(
            heads["pdt_without_z0"](zero, batch_first, batch_second), batch_labels
        )
        # Base-only omits Merge entirely.  Fresh clones preserve the declared
        # depth/interface but have no personalization and emit zero deltas;
        # this is not a claim of executed-FLOP matching in the buffered pilot.
        base_loss = F.cross_entropy(
            heads["base_only"].final_layers(batch_z0), batch_labels
        )
        clone_loss = F.cross_entropy(
            heads["fresh_clones"](batch_z0, zero, zero), batch_labels
        )
        first_loss = F.cross_entropy(
            heads["single_first"](batch_z0, batch_control_first, zero), batch_labels
        )
        second_loss = F.cross_entropy(
            heads["single_second"](batch_z0, zero, batch_control_second), batch_labels
        )
        prior_loss = F.cross_entropy(
            prior_logits.unsqueeze(0).expand(batch_labels.shape[0], -1),
            batch_labels,
        )
        total = (
            pdt_loss
            + pdt_without_z0_loss
            + base_loss
            + clone_loss
            + first_loss
            + second_loss
            + prior_loss
        )
        total.backward()
        optimizer.step()
        losses = {
            "pdt": float(pdt_loss.detach().item()),
            "pdt_without_z0": float(pdt_without_z0_loss.detach().item()),
            "base_only_z0": float(base_loss.detach().item()),
            "fresh_clone_no_personalization": float(clone_loss.detach().item()),
            "single_first": float(first_loss.detach().item()),
            "single_second": float(second_loss.detach().item()),
            "no_knowledge_prior": float(prior_loss.detach().item()),
        }
    for head in heads.values():
        head.eval()
    return heads, prior_logits.detach(), losses


def _predict(module: nn.Module, *inputs: Tensor) -> list[int]:
    with torch.no_grad():
        return module(*inputs).argmax(dim=-1).tolist()


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("experiment_id") != "E001":
        raise ValueError("config experiment_id must be E001")
    stage = config.get("stage", "development")
    if stage not in ("development", "locked_pilot"):
        raise ValueError("stage must be development or locked_pilot")
    required_gates = set(_development_gate_defaults())
    supplied_gates = config.get("gates")
    if stage == "locked_pilot":
        if not isinstance(supplied_gates, Mapping):
            raise ValueError("locked_pilot config requires an explicit gates object")
        missing = required_gates - set(supplied_gates)
        if missing:
            raise ValueError(
                "locked_pilot config is missing required gates: "
                + ", ".join(sorted(missing))
            )
    if supplied_gates is not None:
        if not isinstance(supplied_gates, Mapping):
            raise ValueError("gates must be a JSON object")
        unknown = set(supplied_gates) - required_gates
        if unknown:
            raise ValueError("unknown gates: " + ", ".join(sorted(unknown)))
        for name, value in supplied_gates.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"gate {name} must be numeric")
            if not math.isfinite(float(value)) or float(value) < 0:
                raise ValueError(f"gate {name} must be finite and non-negative")
    world = config["world"]
    model = config["model"]
    if world["specialties"] != len(SPECIALTIES):
        raise ValueError(f"E001 requires exactly {len(SPECIALTIES)} specialties")
    if world["experts_per_specialty"] != 2:
        raise ValueError("E001 requires exactly two distinct pocket i per specialty")
    if len(model["tower_depths"]) != len(SPECIALTIES) * 2:
        raise ValueError("tower_depths must provide one depth for each of eight pocket i")
    train_fraction = float(world["train_fraction"])
    validation_fraction = float(world["validation_fraction"])
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1")
    if not 0 <= validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("configured fractions must leave a non-empty test share")


def _effective_config(config: Mapping[str, Any], smoke: bool) -> dict[str, Any]:
    effective = copy.deepcopy(dict(config))
    effective.setdefault("stage", "development")
    gate_values = _development_gate_defaults()
    gate_values.update(effective.get("gates", {}))
    effective["gates"] = gate_values
    if smoke:
        # 70/15/15 with eight keys yields a useful 5/1/2 train/validation/test
        # partition per specialty while remaining tiny.
        effective["world"]["keys"] = 8
        effective["training"]["expert_steps"] = min(
            3, int(effective["training"]["expert_steps"])
        )
        effective["training"]["merger_steps"] = min(
            8, int(effective["training"]["merger_steps"])
        )
    return effective


def _class_counts(tasks: Sequence[PrivateWorldTask]) -> list[int]:
    return [sum(task.answer_class == class_id for task in tasks) for class_id in range(4)]


def _key_sets_for_split(tasks: Sequence[PrivateWorldTask]) -> dict[str, list[str]]:
    return {
        specialty: sorted(
            {
                ref.key
                for task in tasks
                for ref in (task.first, task.second)
                if ref.specialty == specialty
            }
        )
        for specialty in SPECIALTIES
    }


def _key_split_audit(splits: TaskSplits) -> dict[str, Any]:
    key_sets = {
        "train": _key_sets_for_split(splits.train),
        "validation": _key_sets_for_split(splits.validation),
        "test": _key_sets_for_split(splits.test),
    }
    pairwise: dict[str, bool] = {}
    for first_name, second_name in (
        ("train", "validation"),
        ("train", "test"),
        ("validation", "test"),
    ):
        pairwise[f"{first_name}_vs_{second_name}"] = all(
            set(key_sets[first_name][specialty]).isdisjoint(
                key_sets[second_name][specialty]
            )
            for specialty in SPECIALTIES
        )
    all_disjoint = all(pairwise.values())
    if not all_disjoint:
        raise RuntimeError(f"key-disjoint split invariant failed: {pairwise}")
    return {
        "sets": key_sets,
        "counts": {
            split_name: {
                specialty: len(keys) for specialty, keys in specialties.items()
            }
            for split_name, specialties in key_sets.items()
        },
        "pairwise_disjoint": pairwise,
        "all_disjoint": all_disjoint,
    }


def _unique_run_dir(root: Path, identifier: str) -> Path:
    candidate = root / identifier
    counter = 1
    while candidate.exists():
        candidate = root / f"{identifier}-{counter}"
        counter += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def _resolve_artifacts_root(
    config: Mapping[str, Any], artifacts_root: Path | None
) -> Path:
    if artifacts_root is not None:
        return artifacts_root
    configured_root = Path(str(config["artifacts_dir"]))
    if configured_root.is_absolute():
        return configured_root
    repo_root = _repo_root()
    if repo_root.name == "E001-personal-delta-towers":
        return repo_root / "artifacts"
    return repo_root / configured_root


def _run_labels(*, stage: str, smoke: bool, gates_passed: bool) -> tuple[str, str]:
    if smoke:
        return "development_smoke", "informational_smoke_only"
    if stage == "locked_pilot":
        return (
            "locked_pilot",
            "seed_passed_await_locked_suite"
            if gates_passed
            else "do_not_advance",
        )
    return (
        "development",
        "development_gates_passed_not_locked"
        if gates_passed
        else "development_gates_failed",
    )


def _mean_min_max(values: Sequence[float]) -> dict[str, float]:
    if not values:
        raise ValueError("cannot aggregate an empty sequence")
    return {
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }


def run_experiment(
    config: Mapping[str, Any],
    *,
    smoke: bool = False,
    artifacts_root: Path | None = None,
    identifier: str | None = None,
) -> dict[str, Any]:
    """Run E001 and return the same summary written to ``summary.json``."""

    _validate_config(config)
    effective = _effective_config(config, smoke)
    seed = int(effective["seed"])
    _seed_everything(seed, threads=1 if smoke else 8)
    started_at = utc_timestamp()
    started_clock = time.perf_counter()
    phase_seconds: dict[str, float] = {}

    world_config = effective["world"]
    model_config = effective["model"]
    training_config = effective["training"]
    evaluation_config = effective["evaluation"]
    world = build_private_world(
        seed=seed, keys_per_specialty=int(world_config["keys"])
    )
    all_tasks = generate_tasks(world)
    splits: TaskSplits = split_tasks_by_keys(
        world,
        train_fraction=float(world_config["train_fraction"]),
        validation_fraction=float(world_config["validation_fraction"]),
    )
    if not splits.train or not splits.validation or not splits.test:
        raise RuntimeError("configured deterministic split produced an empty partition")
    train_tasks = tuple(splits.train)
    test_tasks = tuple(splits.test)
    key_split_audit = _key_split_audit(splits)
    config_sha256 = _json_hash(effective)
    data_sha256 = _json_hash(
        {
            "world_id": world.world_id,
            "facts": {
                specialty: dict(world.facts[specialty]) for specialty in SPECIALTIES
            },
            "split_task_ids": {
                "train": [task.task_id for task in splits.train],
                "validation": [task.task_id for task in splits.validation],
                "test": [task.task_id for task in splits.test],
            },
        }
    )

    d_model = int(model_config["d_model"])
    abi_dim = d_model
    nhead = int(model_config["nhead"])
    feedforward = int(model_config["feedforward"])
    torch.manual_seed(seed)
    stem = SharedStem(
        specialty_vocab_size=len(SPECIALTIES),
        key_vocab_size=int(world_config["keys"]),
        d_model=d_model,
        nhead=nhead,
        dim_feedforward=feedforward,
    )
    base = BaseTowerTemplate(
        d_model=d_model, nhead=nhead, dim_feedforward=feedforward
    )
    stem.requires_grad_(False).eval()
    base.requires_grad_(False).eval()

    hidden_by_specialty: dict[str, Tensor] = {}
    base_cls_by_depth_and_specialty: dict[tuple[int, str], Tensor] = {}
    source_cls_by_ref: dict[tuple[str, str], Tensor] = {}
    keys_by_specialty: dict[str, tuple[str, ...]] = {}
    bits_by_specialty: dict[str, Tensor] = {}
    with torch.no_grad():
        for specialty_index, specialty in enumerate(SPECIALTIES):
            keys = tuple(world.facts[specialty])
            key_ids = torch.tensor([_fact_key_id(FactRef(specialty, key)) for key in keys])
            specialty_ids = torch.full_like(key_ids, specialty_index)
            hidden = stem(specialty_ids, key_ids).detach()
            hidden_by_specialty[specialty] = hidden
            keys_by_specialty[specialty] = keys
            bits_by_specialty[specialty] = torch.tensor(
                [world.facts[specialty][key] for key in keys], dtype=torch.long
            )
        for depth in sorted(set(int(value) for value in model_config["tower_depths"])):
            for specialty in SPECIALTIES:
                base_cls_by_depth_and_specialty[(depth, specialty)] = base(
                    hidden_by_specialty[specialty], depth=depth
                )[:, 0, :].detach()
        # z0 always comes from the complete trusted 24-layer source path,
        # independently of the depths assigned to remote pocket i.
        for specialty in SPECIALTIES:
            source_batch = base(hidden_by_specialty[specialty], depth=24)[:, 0, :]
            for index, key in enumerate(keys_by_specialty[specialty]):
                source_cls_by_ref[(specialty, key)] = source_batch[index].detach()

    setup_done = time.perf_counter()
    phase_seconds["world_and_shared_model"] = setup_done - started_clock

    trained: dict[str, TrainedPocketI] = {}
    expert_stats: list[dict[str, Any]] = []
    depths = [int(value) for value in model_config["tower_depths"]]
    roster_index = 0
    for specialty in SPECIALTIES:
        validation_keys = _validation_keys(
            splits.validation, specialty, keys_by_specialty[specialty]
        )
        for letter in ("a", "b"):
            logical_id = f"{specialty}-i-{letter}"
            depth = depths[roster_index]
            expert = _train_one_expert(
                logical_id=logical_id,
                specialty=specialty,
                depth=depth,
                expert_seed=seed + 1000 + roster_index,
                stem_hidden=hidden_by_specialty[specialty],
                base_cls=base_cls_by_depth_and_specialty[(depth, specialty)],
                keys=keys_by_specialty[specialty],
                bits=bits_by_specialty[specialty],
                validation_keys=validation_keys,
                base=base,
                abi_dim=abi_dim,
                max_delta_norm=float(model_config["max_delta_norm"]),
                steps=int(training_config["expert_steps"]),
                learning_rate=float(training_config["expert_learning_rate"]),
            )
            trained[logical_id] = expert
            expert_stats.append(expert.stats)
            roster_index += 1

    # Personal learning ends here.  Central heads must never update the shared
    # encoder, base reference, or any pocket i.
    for expert in trained.values():
        expert.tower.zero_grad(set_to_none=True)
        expert.tower.requires_grad_(False).eval()
    frozen_assertions = {
        "stem": all(not parameter.requires_grad for parameter in stem.parameters()),
        "base": all(not parameter.requires_grad for parameter in base.parameters()),
        "all_personal_towers": all(
            not parameter.requires_grad
            for expert in trained.values()
            for parameter in expert.tower.parameters()
        ),
        "all_cached_capsules_detached": all(
            not capsule.requires_grad
            for expert in trained.values()
            for capsule in expert.capsules.values()
        ),
    }
    if not all(frozen_assertions.values()):
        raise RuntimeError(f"frozen-boundary assertion failed: {frozen_assertions}")

    experts_done = time.perf_counter()
    phase_seconds["train_eight_pocket_i"] = experts_done - setup_done
    router = TopTwoRouter(
        LogicalExpert(
            logical_id=expert.logical_id,
            specialty=expert.specialty,
            validation_quality=expert.validation_quality,
        )
        for expert in trained.values()
    )
    train_z0, train_first, train_second, train_labels, _ = _features_for_tasks(
        train_tasks,
        router=router,
        trained=trained,
        failure_probability=float(training_config["failure_training_probability"]),
        failure_seed=seed + 2000,
        source_cls=source_cls_by_ref,
    )
    (
        train_control_z0,
        train_control_first,
        train_control_second,
        train_control_labels,
        _,
    ) = _features_for_tasks(
        train_tasks,
        router=router,
        trained=trained,
        failure_probability=0.0,
        failure_seed=seed + 2100,
        source_cls=source_cls_by_ref,
    )
    if not torch.equal(train_z0, train_control_z0) or not torch.equal(
        train_labels, train_control_labels
    ):
        raise RuntimeError("control and PDT training batches must share z0 and labels")
    heads, prior_logits, head_losses = _train_heads(
        z0=train_z0,
        first=train_first,
        second=train_second,
        control_first=train_control_first,
        control_second=train_control_second,
        labels=train_labels,
        abi_dim=abi_dim,
        hidden_dim=2 * abi_dim,
        steps=int(training_config["merger_steps"]),
        learning_rate=float(training_config["merger_learning_rate"]),
        seed=seed + 3000,
    )
    heads_done = time.perf_counter()
    phase_seconds["train_source_and_baselines"] = heads_done - experts_done

    normal_z0, normal_first, normal_second, labels, normal_audits = _features_for_tasks(
        test_tasks,
        router=router,
        trained=trained,
        failure_probability=0.0,
        failure_seed=seed + 4000,
        source_cls=source_cls_by_ref,
    )
    reversed_z0 = torch.stack(
        [
            _trusted_source_z0(
                source_cls_by_ref[(task.second.specialty, task.second.key)],
                source_cls_by_ref[(task.first.specialty, task.first.key)],
            )
            for task in test_tasks
        ]
    )
    order_distances = torch.linalg.vector_norm(normal_z0 - reversed_z0, dim=-1)
    nonidentical_source_refs = [
        not torch.equal(
            source_cls_by_ref[(task.first.specialty, task.first.key)],
            source_cls_by_ref[(task.second.specialty, task.second.key)],
        )
        for task in test_tasks
    ]
    order_aware_count = sum(
        bool(distance > 1e-6) and nonidentical
        for distance, nonidentical in zip(
            order_distances.tolist(), nonidentical_source_refs, strict=True
        )
    )
    nonidentical_count = sum(nonidentical_source_refs)
    source_z0_order_aware = order_aware_count == nonidentical_count
    if not source_z0_order_aware:
        raise RuntimeError("trusted source z0 did not preserve ordered task roles")
    configured_z0, configured_first, configured_second, _, configured_audits = _features_for_tasks(
        test_tasks,
        router=router,
        trained=trained,
        failure_probability=float(evaluation_config["preferred_failure_probability"]),
        failure_seed=seed + 5000,
        source_cls=source_cls_by_ref,
    )
    forced_z0, forced_first, forced_second, _, forced_audits = _features_for_tasks(
        test_tasks,
        router=router,
        trained=trained,
        failure_probability=1.0,
        failure_seed=seed + 6000,
        source_cls=source_cls_by_ref,
        force_primary_failure=True,
        poison_variant=1,
    )
    poison_two_z0, poison_two_first, poison_two_second, _, poison_two_audits = (
        _features_for_tasks(
            test_tasks,
            router=router,
            trained=trained,
            failure_probability=1.0,
            failure_seed=seed + 6000,
            source_cls=source_cls_by_ref,
            force_primary_failure=True,
            poison_variant=2,
        )
    )
    poisoned_partial_selection_identical = bool(
        torch.equal(forced_z0, poison_two_z0)
        and torch.equal(forced_first, poison_two_first)
        and torch.equal(forced_second, poison_two_second)
        and all(
            first_role["selected"] == second_role["selected"]
            for first_audit, second_audit in zip(
                forced_audits, poison_two_audits, strict=True
            )
            for first_role, second_role in zip(
                first_audit, second_audit, strict=True
            )
        )
    )
    poison_one_hashes = {
        role["partial_poison_sha256"] for audit in forced_audits for role in audit
    }
    poison_two_hashes = {
        role["partial_poison_sha256"] for audit in poison_two_audits for role in audit
    }
    poisoned_partials_distinct = bool(
        poison_one_hashes
        and poison_two_hashes
        and poison_one_hashes.isdisjoint(poison_two_hashes)
    )
    if not poisoned_partial_selection_identical or not poisoned_partials_distinct:
        raise RuntimeError("transaction invariant failed for distinct poisoned partials")
    zero = torch.zeros_like(normal_first)
    predictions = {
        "pdt_normal": _predict(heads["pdt"], normal_z0, normal_first, normal_second),
        "pdt_configured_failures": _predict(
            heads["pdt"], configured_z0, configured_first, configured_second
        ),
        "pdt_forced_primary_failures": _predict(
            heads["pdt"], forced_z0, forced_first, forced_second
        ),
        "pdt_without_z0": _predict(
            heads["pdt_without_z0"], zero, normal_first, normal_second
        ),
        "base_only_z0": _predict(heads["base_only"].final_layers, normal_z0),
        "fresh_clone_no_personalization": _predict(
            heads["fresh_clones"], normal_z0, zero, zero
        ),
        "single_first_learned": _predict(
            heads["single_first"], normal_z0, normal_first, zero
        ),
        "single_second_learned": _predict(
            heads["single_second"], normal_z0, zero, normal_second
        ),
        "causal_drop_first": _predict(
            heads["pdt"], normal_z0, zero, normal_second
        ),
        "causal_drop_second": _predict(
            heads["pdt"], normal_z0, normal_first, zero
        ),
    }
    poison_two_predictions = _predict(
        heads["pdt"], poison_two_z0, poison_two_first, poison_two_second
    )
    poisoned_partial_result_identical = bool(
        poisoned_partial_selection_identical
        and poison_two_predictions == predictions["pdt_forced_primary_failures"]
    )
    if not poisoned_partial_result_identical:
        raise RuntimeError("poisoned partial changed the selected model result")
    prior_prediction = int(prior_logits.argmax().item())
    predictions["matched_no_knowledge_prior"] = [prior_prediction] * len(test_tasks)
    predictions["oracle_memory"] = labels.tolist()
    label_list = labels.tolist()
    accuracy_breakdowns = {
        name: _accuracy_breakdown(values, label_list)
        for name, values in predictions.items()
    }
    accuracies = {
        name: float(breakdown["micro_accuracy"])
        for name, breakdown in accuracy_breakdowns.items()
    }
    macro_accuracies = {
        name: float(breakdown["macro_accuracy"])
        for name, breakdown in accuracy_breakdowns.items()
    }
    accuracies["best_single_role"] = max(
        accuracies["single_first_learned"],
        accuracies["single_second_learned"],
    )
    strict_flags = [
        predictions["pdt_normal"][index] == label
        and predictions["single_first_learned"][index] != label
        and predictions["single_second_learned"][index] != label
        for index, label in enumerate(label_list)
    ]
    strict_rate = sum(strict_flags) / len(strict_flags)
    causal_retained = max(
        accuracies["causal_drop_first"], accuracies["causal_drop_second"]
    )
    causal_loss = accuracies["pdt_normal"] - causal_retained
    primary_control_names = (
        "base_only_z0",
        "fresh_clone_no_personalization",
        "single_first_learned",
        "single_second_learned",
    )
    strongest_control_name = max(
        primary_control_names, key=lambda name: accuracies[name]
    )
    strongest_control_accuracy = accuracies[strongest_control_name]
    collective_lift = accuracies["pdt_normal"] - strongest_control_accuracy
    strongest_macro_control_name = max(
        primary_control_names, key=lambda name: macro_accuracies[name]
    )
    strongest_macro_control_accuracy = macro_accuracies[
        strongest_macro_control_name
    ]
    macro_collective_lift = (
        macro_accuracies["pdt_normal"] - strongest_macro_control_accuracy
    )
    source_z0_contribution = {
        "pass_fail_gate": False,
        "micro_accuracy_difference": accuracies["pdt_normal"]
        - accuracies["pdt_without_z0"],
        "macro_accuracy_difference": macro_accuracies["pdt_normal"]
        - macro_accuracies["pdt_without_z0"],
        "interpretation": (
            "Positive means the full PDT head outperformed a separately trained "
            "two-delta head whose trusted source state was replaced by zero."
        ),
    }
    backup_loss = (
        accuracies["pdt_normal"]
        - accuracies["pdt_forced_primary_failures"]
    )
    per_ordered_specialty_pair: dict[str, Any] = {}
    for first_specialty in SPECIALTIES:
        for second_specialty in SPECIALTIES:
            if first_specialty == second_specialty:
                continue
            indices = [
                index
                for index, task in enumerate(test_tasks)
                if task.specialties == (first_specialty, second_specialty)
            ]
            pair_labels = [label_list[index] for index in indices]
            pair_accuracy = {
                name: _accuracy([values[index] for index in indices], pair_labels)
                for name, values in predictions.items()
            }
            pair_control = max(
                primary_control_names, key=lambda name: pair_accuracy[name]
            )
            per_ordered_specialty_pair[
                f"{first_specialty}>{second_specialty}"
            ] = {
                "tasks": len(indices),
                "class_counts": [
                    sum(label == class_id for label in pair_labels)
                    for class_id in range(4)
                ],
                "accuracy": pair_accuracy,
                "strongest_control": pair_control,
                "collective_lift": pair_accuracy["pdt_normal"]
                - pair_accuracy[pair_control],
                "strict_joint_ablation_count": sum(strict_flags[index] for index in indices),
                "strict_joint_ablation_rate": (
                    sum(strict_flags[index] for index in indices) / len(indices)
                ),
            }

    records: list[dict[str, Any]] = []
    for index, task in enumerate(test_tasks):
        task_predictions = {name: values[index] for name, values in predictions.items()}
        task_predictions["best_single_role_correct"] = bool(
            task_predictions["single_first_learned"] == task.answer_class
            or task_predictions["single_second_learned"] == task.answer_class
        )
        records.append(
            {
                "task_id": task.task_id,
                "first": {
                    "specialty": task.first.specialty,
                    "key": task.first.key,
                    "private_bit": task.first_bit,
                },
                "second": {
                    "specialty": task.second.specialty,
                    "key": task.second.key,
                    "private_bit": task.second_bit,
                },
                "answer_class": task.answer_class,
                "source_z0_norm": float(
                    torch.linalg.vector_norm(normal_z0[index]).item()
                ),
                "source_z0_reversal_distance": float(order_distances[index].item()),
                "predictions": task_predictions,
                "strict_collaborative_success": strict_flags[index],
                "routing": {
                    "normal": normal_audits[index],
                    "configured_failures": configured_audits[index],
                    "forced_primary_failures": forced_audits[index],
                },
            }
        )

    all_routes_distinct = all(
        len(set(role["candidates"])) == 2
        for record in records
        for mode in record["routing"].values()
        for role in mode
    )
    partial_merged_count = sum(
        int(role["partial_payload_merged"])
        for record in records
        for mode in record["routing"].values()
        for role in mode
    )
    all_forced_used_backup = all(
        role["primary_failed"]
        and role["selected"] == role["candidates"][1]
        and role["selected_complete"]
        for record in records
        for role in record["routing"]["forced_primary_failures"]
    )
    fresh_max = max(stat["fresh_max_delta_norm"] for stat in expert_stats)
    z0_norms = torch.linalg.vector_norm(normal_z0, dim=-1)
    z0_max_unit_error = float((z0_norms - 1.0).abs().max().item())
    gate_config = effective["gates"]
    gates = {
        "key_disjoint_merger_split": {
            "pass": key_split_audit["all_disjoint"],
            "configured_threshold": {"expected": True},
        },
        "frozen_information_boundary": {
            "pass": all(frozen_assertions.values()),
            "assertions": frozen_assertions,
            "configured_threshold": {"expected": True},
        },
        "trusted_source_z0_normalized": {
            "pass": z0_max_unit_error <= gate_config["z0_norm_error_max"],
            "max_unit_norm_error": z0_max_unit_error,
            "configured_threshold": {
                "operator": "<=",
                "value": gate_config["z0_norm_error_max"],
            },
        },
        "fresh_delta_within_tolerance": {
            "pass": fresh_max <= gate_config["fresh_delta_max"],
            "value": fresh_max,
            "configured_threshold": {
                "operator": "<=",
                "value": gate_config["fresh_delta_max"],
            },
        },
        "distinct_top_two": {
            "pass": all_routes_distinct,
            "configured_threshold": {"expected": True},
        },
        "transactional_partial_discard": {
            "pass": partial_merged_count == 0
            and all_forced_used_backup
            and poisoned_partial_result_identical
            and poisoned_partials_distinct,
            "partial_payloads_merged": partial_merged_count,
            "all_forced_routes_used_backup": all_forced_used_backup,
            "distinct_poisoned_partials": poisoned_partials_distinct,
            "selected_backup_and_result_identical": poisoned_partial_result_identical,
            "configured_threshold": {"partial_payloads_merged": 0},
        },
        "backup_quality_preserved": {
            "pass": backup_loss <= gate_config["backup_loss_max"],
            "normal_minus_forced_accuracy": backup_loss,
            "configured_threshold": {
                "operator": "<=",
                "value": gate_config["backup_loss_max"],
            },
        },
        "collective_lift": {
            "pass": collective_lift >= gate_config["collective_lift_min"],
            "value": collective_lift,
            "configured_threshold": {
                "operator": ">=",
                "value": gate_config["collective_lift_min"],
            },
        },
        "macro_collective_lift": {
            "pass": macro_collective_lift
            >= gate_config["macro_collective_lift_min"],
            "value": macro_collective_lift,
            "configured_threshold": {
                "operator": ">=",
                "value": gate_config["macro_collective_lift_min"],
            },
        },
        "causal_specialty_loss": {
            "pass": causal_loss >= gate_config["causal_loss_min"],
            "value": causal_loss,
            "configured_threshold": {
                "operator": ">=",
                "value": gate_config["causal_loss_min"],
            },
        },
    }
    pilot_gate_pass = all(bool(gate["pass"]) for gate in gates.values())
    evaluated_done = time.perf_counter()
    phase_seconds["evaluate_and_audit"] = evaluated_done - heads_done

    repo_root = _repo_root()
    root = _resolve_artifacts_root(effective, artifacts_root)
    output_dir = _unique_run_dir(root, identifier or run_id(seed))
    tasks_path = output_dir / "tasks.jsonl"
    summary_path = output_dir / "summary.json"
    write_jsonl(tasks_path, records)
    tasks_sha256 = sha256(tasks_path.read_bytes()).hexdigest()
    total_seconds = time.perf_counter() - started_clock
    max_rss_kib = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    status, advancement_decision = _run_labels(
        stage=str(effective["stage"]), smoke=smoke, gates_passed=pilot_gate_pass
    )
    summary: dict[str, Any] = {
        "schema_version": 3,
        "experiment_id": "E001",
        "stage": effective["stage"],
        "status": status,
        "started_at": started_at,
        "completed_at": utc_timestamp(),
        "seed": seed,
        "git_revision": git_revision(repo_root),
        "environment": environment_record(),
        "requested_config": copy.deepcopy(dict(config)),
        "effective_config": effective,
        "hashes": {
            "effective_config_sha256": config_sha256,
            "private_world_and_splits_sha256": data_sha256,
            "task_jsonl_sha256": tasks_sha256,
        },
        "world": {
            "world_id": world.world_id,
            "specialties": list(SPECIALTIES),
            "keys_per_specialty": int(world_config["keys"]),
            "task_counts": {
                "all": len(all_tasks),
                "train_split": len(splits.train),
                "validation_split": len(splits.validation),
                "test_split": len(splits.test),
                "train_used": len(train_tasks),
                "test_used": len(test_tasks),
                "cross_partition_tasks_excluded": len(all_tasks)
                - len(splits.train)
                - len(splits.validation)
                - len(splits.test),
            },
            "configured_split_fractions": {
                "train": float(world_config["train_fraction"]),
                "validation": float(world_config["validation_fraction"]),
                "test": round(
                    1.0
                    - float(world_config["train_fraction"])
                    - float(world_config["validation_fraction"]),
                    12,
                ),
            },
            "key_split": key_split_audit,
            "class_distribution": {
                "train": _class_counts(splits.train),
                "validation": _class_counts(splits.validation),
                "test": _class_counts(splits.test),
            },
        },
        "neural_abi": {
            "equation": "logits = FinalLayers(z0 + Clip(Merge(delta_first, delta_second)))",
            "trusted_source_z0": "L2Normalize(I·Base24CLS(first_ref) + P2·Base24CLS(second_ref)); P2=cyclic coordinate roll by 1",
            "z0_is_source_owned": True,
            "z0_is_order_aware": source_z0_order_aware,
            "z0_order_audit": {
                "nonidentical_reference_pairs": nonidentical_count,
                "pairs_changed_when_roles_reversed": order_aware_count,
                "minimum_reversal_distance": float(order_distances.min().item()),
            },
            "z0_transform_trainable": False,
            "z0_transform_label_access": False,
            "dimension": abi_dim,
            "canonical_bit_codes": {
                "0": [1.0, 0.0] + [0.0] * (abi_dim - 2),
                "1": [0.0, 1.0] + [0.0] * (abi_dim - 2),
            },
            "max_capsule_norm": float(model_config["max_delta_norm"]),
        },
        "experts": expert_stats,
        "router": {
            specialty: [
                {
                    "logical_id": candidate.logical_id,
                    "validation_quality": candidate.validation_quality,
                }
                for candidate in router.route_specialty(specialty).candidates
            ]
            for specialty in SPECIALTIES
        },
        "training": {
            "final_head_losses": head_losses,
            "central_head_conditions": {
                "pdt": "z0 + two complete routed deltas; preferred failures sampled during training",
                "pdt_without_z0": "zero source state + two complete routed deltas; separately trained diagnostic",
                "base_only": "FinalLayers(z0), with Merge omitted",
                "fresh_clone_no_personalization": "z0 + two canonical zero deltas from depth/interface-matched fresh clones; executed FLOPs are not matched",
                "single_first": "z0 + primary first-role delta + zero",
                "single_second": "z0 + zero + primary second-role delta",
                "no_knowledge_prior": "four learned class logits and no task input",
            },
        },
        "information_boundaries": {
            "pocket_i_training": "Each pocket i sees the complete private key-to-bit table for only its specialty.",
            "router_selection": "Only key-disjoint validation tasks determine held-out routing quality.",
            "central_head_training": "All central heads see only train-partition task labels, trusted z0, and the capsules allowed by their control condition.",
            "locked_test_boundary": "Test keys and task labels are used only after all pocket i are frozen and all central heads finish training.",
            "base_and_stem": "Shared stem and 24-layer base are random, frozen, source-owned, and never see private labels.",
            "frozen_assertions_before_head_training": frozen_assertions,
        },
        "metrics": {
            "accuracy": accuracies,
            "accuracy_by_condition": accuracy_breakdowns,
            "primary_strongest_control": strongest_control_name,
            "primary_strongest_control_accuracy": strongest_control_accuracy,
            "collective_lift_over_strongest_control": collective_lift,
            "macro_strongest_control": strongest_macro_control_name,
            "macro_strongest_control_accuracy": strongest_macro_control_accuracy,
            "macro_collective_lift_over_strongest_control": macro_collective_lift,
            "source_z0_contribution_diagnostic": source_z0_contribution,
            "strict_joint_ablation_diagnostic": {
                "pass_fail_gate": False,
                "count": sum(strict_flags),
                "rate": strict_rate,
                "definition": "PDT correct while both separately trained single-role SourceMergers are wrong.",
            },
            "causal_loss_vs_best_one-specialty-drop": causal_loss,
            "forced_backup_accuracy_loss": backup_loss,
            "configured_failure_role_count": sum(
                int(role["primary_failed"])
                for audit in configured_audits
                for role in audit
            ),
            "forced_failure_role_count": len(test_tasks) * 2,
            "learned_no_knowledge_class": prior_prediction,
            "train_class_counts": [
                int((train_labels == class_id).sum().item()) for class_id in range(4)
            ],
            "per_ordered_specialty_pair": per_ordered_specialty_pair,
        },
        "gates": gates,
        "pilot_gate_pass": pilot_gate_pass,
        "advancement_decision": advancement_decision,
        "audit": {
            "task_records": len(records),
            "partial_payloads_merged": partial_merged_count,
            "all_top_two_logical_ids_distinct": all_routes_distinct,
            "all_forced_primary_failures_recovered_by_complete_backup": all_forced_used_backup,
            "distinct_poisoned_partial_hash_sets": poisoned_partials_distinct,
            "poison_variant_one_hashes": sorted(poison_one_hashes),
            "poison_variant_two_hashes": sorted(poison_two_hashes),
            "poisoned_partial_selected_result_invariant": poisoned_partial_result_identical,
            "task_jsonl": str(tasks_path),
        },
        "resources": {
            "wall_seconds": total_seconds,
            "phase_seconds": phase_seconds,
            "max_rss_kib": max_rss_kib,
            "task_jsonl_bytes": tasks_path.stat().st_size,
            "shared_parameters": sum(parameter.numel() for parameter in stem.parameters())
            + sum(parameter.numel() for parameter in base.parameters()),
            "personal_trainable_parameters": sum(
                stat["trainable_parameters"] for stat in expert_stats
            ),
            "source_and_baseline_trainable_parameters": sum(
                parameter.numel()
                for head in heads.values()
                for parameter in head.parameters()
            )
            + prior_logits.numel(),
        },
        "limitations": [
            "Synthetic key-to-bit facts are a mechanism test, not language understanding.",
            "Routing is oracle by specialty; discovery and adversarial routing are not tested.",
            "Capsules are buffered on one CPU process; WAN streaming is not tested.",
            "Every backup completes; simultaneous loss of both candidates is not tested.",
            "Pocket i train on their complete private fact tables; key-disjoint validation and test measure central composition, not unseen-fact learning inside a pocket i.",
        ],
    }
    write_json(summary_path, summary)
    summary["audit"]["summary_json"] = str(summary_path)
    summary["resources"]["summary_json_bytes"] = summary_path.stat().st_size
    write_json(summary_path, summary)
    return summary


def run_suite(
    config: Mapping[str, Any],
    seeds: Sequence[int],
    artifacts_root: Path | None = None,
    identifier: str | None = None,
    *,
    smoke: bool = False,
) -> dict[str, Any]:
    """Run independent seeds and write one non-statistical suite aggregate.

    The task rows across seeds are not assumed IID, so this function reports
    transparent mean/min/max summaries and deliberately does not manufacture a
    confidence interval from them.
    """

    _validate_config(config)
    normalized_seeds = tuple(int(seed) for seed in seeds)
    if not normalized_seeds:
        raise ValueError("run_suite requires at least one seed")
    if len(set(normalized_seeds)) != len(normalized_seeds):
        raise ValueError("run_suite seeds must be distinct")

    suite_config = _effective_config(config, smoke=False)
    root = _resolve_artifacts_root(suite_config, artifacts_root)
    default_identifier = (
        run_id(normalized_seeds[0]).split("-seed-", 1)[0]
        + f"-suite-{len(normalized_seeds)}-seeds"
    )
    suite_dir = _unique_run_dir(root, identifier or default_identifier)
    started = time.perf_counter()
    seed_summaries: list[dict[str, Any]] = []
    for seed in normalized_seeds:
        seed_config = copy.deepcopy(suite_config)
        seed_config["seed"] = seed
        seed_summaries.append(
            run_experiment(
                seed_config,
                smoke=smoke,
                artifacts_root=suite_dir,
                identifier=f"seed-{seed}",
            )
        )

    condition_names = tuple(
        sorted(seed_summaries[0]["metrics"]["accuracy_by_condition"])
    )
    per_seed: list[dict[str, Any]] = []
    for seed, summary in zip(normalized_seeds, seed_summaries, strict=True):
        conditions = {
            name: {
                "micro_accuracy": summary["metrics"]["accuracy_by_condition"][name][
                    "micro_accuracy"
                ],
                "macro_accuracy": summary["metrics"]["accuracy_by_condition"][name][
                    "macro_accuracy"
                ],
            }
            for name in condition_names
        }
        per_seed.append(
            {
                "seed": seed,
                "status": summary["status"],
                "summary_json": summary["audit"]["summary_json"],
                "tasks_jsonl": summary["audit"]["task_jsonl"],
                "conditions": conditions,
                "pdt_accuracy": summary["metrics"]["accuracy"]["pdt_normal"],
                "strongest_control": summary["metrics"][
                    "primary_strongest_control"
                ],
                "strongest_control_accuracy": summary["metrics"][
                    "primary_strongest_control_accuracy"
                ],
                "collective_lift": summary["metrics"][
                    "collective_lift_over_strongest_control"
                ],
                "macro_strongest_control": summary["metrics"][
                    "macro_strongest_control"
                ],
                "macro_strongest_control_accuracy": summary["metrics"][
                    "macro_strongest_control_accuracy"
                ],
                "macro_collective_lift": summary["metrics"][
                    "macro_collective_lift_over_strongest_control"
                ],
                "backup_accuracy": summary["metrics"]["accuracy"][
                    "pdt_forced_primary_failures"
                ],
                "backup_accuracy_loss": summary["metrics"][
                    "forced_backup_accuracy_loss"
                ],
                "all_gates_passed": summary["pilot_gate_pass"],
            }
        )

    condition_aggregate = {
        name: {
            metric: _mean_min_max(
                [float(seed["conditions"][name][metric]) for seed in per_seed]
            )
            for metric in ("micro_accuracy", "macro_accuracy")
        }
        for name in condition_names
    }
    core_aggregate = {
        metric: _mean_min_max([float(seed[metric]) for seed in per_seed])
        for metric in (
            "pdt_accuracy",
            "strongest_control_accuracy",
            "collective_lift",
            "macro_strongest_control_accuracy",
            "macro_collective_lift",
            "backup_accuracy",
            "backup_accuracy_loss",
        )
    }
    all_seeds_passed = all(seed["all_gates_passed"] for seed in per_seed)
    requested_stage = str(suite_config["stage"])
    if smoke:
        suite_status = "development_smoke_suite"
        advancement = "informational_smoke_only"
    elif requested_stage == "locked_pilot":
        suite_status = "locked_pilot_suite"
        advancement = "advance" if all_seeds_passed else "do_not_advance"
    else:
        suite_status = "development_suite"
        advancement = (
            "development_all_gates_passed_not_locked"
            if all_seeds_passed
            else "development_gates_failed"
        )

    suite_path = suite_dir / "suite-summary.json"
    suite_summary: dict[str, Any] = {
        "schema_version": 1,
        "experiment_id": "E001",
        "status": suite_status,
        "requested_stage": requested_stage,
        "seeds": list(normalized_seeds),
        "seed_count": len(normalized_seeds),
        "all_seeds_passed": all_seeds_passed,
        "advancement_decision": advancement,
        "advancement_rule": (
            "A locked pilot advances only when every configured seed passes every gate."
        ),
        "per_seed": per_seed,
        "aggregate": {
            "core_metrics": core_aggregate,
            "conditions": condition_aggregate,
            "method": "mean, minimum, and maximum across independently executed seeds",
            "iid_task_confidence_interval": None,
            "uncertainty_note": (
                "No task-level IID confidence interval is reported because tasks within "
                "and across synthetic worlds are structured, not independent samples."
            ),
        },
        "requested_config": suite_config,
        "config_sha256": _json_hash(suite_config),
        "environment": environment_record(),
        "wall_seconds": time.perf_counter() - started,
        "suite_summary_json": str(suite_path),
    }
    write_json(suite_path, suite_summary)
    return suite_summary


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("config root must be a JSON object")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    seed_group = parser.add_mutually_exclusive_group()
    seed_group.add_argument(
        "--seed",
        type=int,
        help="override config.seed for one run",
    )
    seed_group.add_argument(
        "--all-seeds",
        action="store_true",
        help="run every distinct seed listed in config evaluation.seeds",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="run only a tiny deterministic development check",
    )
    args = parser.parse_args(argv)
    config = _load_config(args.config)
    if args.all_seeds:
        seeds = config.get("evaluation", {}).get("seeds", ())
        summary = run_suite(config, seeds, smoke=args.smoke)
        print(
            json.dumps(
                {
                    "status": summary["status"],
                    "all_seeds_passed": summary["all_seeds_passed"],
                    "advancement_decision": summary["advancement_decision"],
                    "suite_summary": summary["suite_summary_json"],
                },
                indent=2,
            )
        )
        return 0
    if args.seed is not None:
        config = copy.deepcopy(config)
        config["seed"] = args.seed
    summary = run_experiment(config, smoke=args.smoke)
    print(json.dumps({
        "status": summary["status"],
        "pilot_gate_pass": summary["pilot_gate_pass"],
        "advancement_decision": summary["advancement_decision"],
        "summary": summary["audit"]["summary_json"],
        "tasks": summary["audit"]["task_jsonl"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
