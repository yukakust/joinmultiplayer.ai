"""Deterministic synthetic data for experiment E001.

The private world is deliberately small and inspectable.  Each specialty owns a
private key-to-bit table.  A task asks for one key from each of two *ordered*
specialties, and the two bits form a four-class target::

    answer_class = 2 * first_bit + second_bit

No process-randomized Python ``hash`` values are used, so a seed produces the
same world, task ids, and splits on every machine.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Literal


SPECIALTIES: tuple[str, ...] = (
    "chess",
    "navigation",
    "botany",
    "mechanics",
)

SplitName = Literal["train", "validation", "test"]


def _stable_digest(value: str) -> bytes:
    return sha256(value.encode("utf-8")).digest()


def _stable_bit(value: str) -> int:
    return _stable_digest(value)[0] & 1


@dataclass(frozen=True, slots=True)
class FactRef:
    """A reference to one private fact, without revealing its bit."""

    specialty: str
    key: str


@dataclass(frozen=True, slots=True)
class PrivateWorld:
    """Four specialty-specific private maps used to generate questions."""

    seed: int
    world_id: str
    facts: Mapping[str, Mapping[str, int]]

    def __post_init__(self) -> None:
        if tuple(self.facts) != SPECIALTIES:
            raise ValueError(f"a private world must contain {SPECIALTIES!r} in order")

        frozen_facts: dict[str, Mapping[str, int]] = {}
        for specialty, key_bits in self.facts.items():
            if not key_bits:
                raise ValueError(f"specialty {specialty!r} has no private facts")
            copied = dict(key_bits)
            if any(bit not in (0, 1) for bit in copied.values()):
                raise ValueError("private facts must map keys to bits (0 or 1)")
            frozen_facts[specialty] = MappingProxyType(copied)
        object.__setattr__(self, "facts", MappingProxyType(frozen_facts))

    def bit_for(self, ref: FactRef) -> int:
        """Return the private bit associated with ``ref``."""

        try:
            return self.facts[ref.specialty][ref.key]
        except KeyError as exc:
            raise KeyError(f"unknown private fact: {ref.specialty}/{ref.key}") from exc


@dataclass(frozen=True, slots=True)
class PrivateWorldTask:
    """One ordered two-specialty question and its exact four-class target."""

    task_id: str
    first: FactRef
    second: FactRef
    first_bit: int
    second_bit: int
    answer_class: int

    def __post_init__(self) -> None:
        if self.first.specialty == self.second.specialty:
            raise ValueError("a task must combine two distinct specialties")
        if self.first_bit not in (0, 1) or self.second_bit not in (0, 1):
            raise ValueError("task bits must be 0 or 1")
        expected = 2 * self.first_bit + self.second_bit
        if self.answer_class != expected:
            raise ValueError(
                f"answer_class must be 2 * first_bit + second_bit ({expected})"
            )

    @property
    def specialties(self) -> tuple[str, str]:
        """The required specialties, preserving question order."""

        return self.first.specialty, self.second.specialty


@dataclass(frozen=True, slots=True)
class TaskSplits:
    """Non-overlapping deterministic train, validation, and test partitions."""

    train: tuple[PrivateWorldTask, ...]
    validation: tuple[PrivateWorldTask, ...]
    test: tuple[PrivateWorldTask, ...]

    @property
    def val(self) -> tuple[PrivateWorldTask, ...]:
        """Short alias useful in training loops."""

        return self.validation


def build_private_world(*, seed: int = 0, keys_per_specialty: int = 8) -> PrivateWorld:
    """Build a deterministic four-specialty world.

    Keys are public identifiers; their bits represent the knowledge available
    only to a pocket i specializing in that domain.
    """

    if keys_per_specialty < 2:
        raise ValueError("keys_per_specialty must be at least 2")

    facts: dict[str, dict[str, int]] = {}
    serialized: list[str] = []
    for specialty in SPECIALTIES:
        key_bits: dict[str, int] = {}
        for index in range(keys_per_specialty):
            key = f"key-{index:03d}"
            bit = _stable_bit(f"e001:{seed}:{specialty}:{key}")
            key_bits[key] = bit
            serialized.append(f"{specialty}:{key}:{bit}")
        facts[specialty] = key_bits

    identity = f"seed={seed};" + ";".join(serialized)
    world_id = _stable_digest(identity).hex()[:16]
    return PrivateWorld(seed=seed, world_id=world_id, facts=facts)


def generate_tasks(world: PrivateWorld) -> tuple[PrivateWorldTask, ...]:
    """Generate every ordered pair of keys from two distinct specialties."""

    tasks: list[PrivateWorldTask] = []
    for first_specialty in SPECIALTIES:
        for second_specialty in SPECIALTIES:
            if first_specialty == second_specialty:
                continue
            for first_key, first_bit in world.facts[first_specialty].items():
                for second_key, second_bit in world.facts[second_specialty].items():
                    task_id = (
                        f"{world.world_id}:{first_specialty}/{first_key}"
                        f">{second_specialty}/{second_key}"
                    )
                    tasks.append(
                        PrivateWorldTask(
                            task_id=task_id,
                            first=FactRef(first_specialty, first_key),
                            second=FactRef(second_specialty, second_key),
                            first_bit=first_bit,
                            second_bit=second_bit,
                            answer_class=2 * first_bit + second_bit,
                        )
                    )
    return tuple(tasks)


def split_name(
    task_id: str,
    *,
    train_fraction: float = 0.8,
    validation_fraction: float = 0.1,
) -> SplitName:
    """Assign a task id to a configured split using a stable hash."""

    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1")
    if not 0 <= validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train and validation fractions must leave a test split")

    bucket = int.from_bytes(_stable_digest(task_id)[:8], "big") / 2**64
    if bucket < train_fraction:
        return "train"
    if bucket < train_fraction + validation_fraction:
        return "validation"
    return "test"


def split_tasks(
    tasks: Iterable[PrivateWorldTask],
    *,
    train_fraction: float = 0.8,
    validation_fraction: float = 0.1,
) -> TaskSplits:
    """Partition tasks without depending on their input order."""

    partitions: dict[SplitName, list[PrivateWorldTask]] = {
        "train": [],
        "validation": [],
        "test": [],
    }
    seen_ids: set[str] = set()
    for task in tasks:
        if task.task_id in seen_ids:
            raise ValueError(f"duplicate task id: {task.task_id}")
        seen_ids.add(task.task_id)
        partitions[
            split_name(
                task.task_id,
                train_fraction=train_fraction,
                validation_fraction=validation_fraction,
            )
        ].append(task)

    for partition in partitions.values():
        partition.sort(key=lambda task: task.task_id)
    return TaskSplits(
        train=tuple(partitions["train"]),
        validation=tuple(partitions["validation"]),
        test=tuple(partitions["test"]),
    )


def split_tasks_by_keys(
    world: PrivateWorld,
    *,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
) -> TaskSplits:
    """Build deterministic key-disjoint splits for merger evaluation.

    Within each specialty, keys are stably permuted using only the public seed,
    specialty, and key name.  Labels and ``world_id`` never affect placement.
    A task is included only when both of its references belong to the same
    partition, preventing a held-out key from leaking through another task.

    The train and validation sizes are ``floor(n * fraction)`` and the test
    split receives the remainder.  Invalid configurations that make any group
    empty are rejected explicitly.
    """

    if not 0.0 < train_fraction < 1.0:
        raise ValueError("train_fraction must be between 0 and 1")
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("validation_fraction must be between 0 and 1")
    if train_fraction + validation_fraction >= 1.0:
        raise ValueError("train and validation fractions must leave room for test")

    key_partition: dict[tuple[str, str], SplitName] = {}
    for specialty in SPECIALTIES:
        ordered_keys = sorted(
            world.facts[specialty],
            key=lambda key: (
                _stable_digest(
                    f"e001:key-split:v1:{world.seed}:{specialty}:{key}"
                ),
                key,
            ),
        )
        train_size = int(len(ordered_keys) * train_fraction)
        validation_size = int(len(ordered_keys) * validation_fraction)
        test_size = len(ordered_keys) - train_size - validation_size
        if min(train_size, validation_size, test_size) < 1:
            raise ValueError(
                "fractions and keys_per_specialty must make every split non-empty"
            )

        slices: tuple[tuple[SplitName, list[str]], ...] = (
            ("train", ordered_keys[:train_size]),
            (
                "validation",
                ordered_keys[train_size : train_size + validation_size],
            ),
            ("test", ordered_keys[train_size + validation_size :]),
        )
        for partition_name, partition_keys in slices:
            for key in partition_keys:
                key_partition[(specialty, key)] = partition_name

    partitions: dict[SplitName, list[PrivateWorldTask]] = {
        "train": [],
        "validation": [],
        "test": [],
    }
    for task in generate_tasks(world):
        first_partition = key_partition[(task.first.specialty, task.first.key)]
        second_partition = key_partition[(task.second.specialty, task.second.key)]
        if first_partition == second_partition:
            partitions[first_partition].append(task)

    return TaskSplits(
        train=tuple(partitions["train"]),
        validation=tuple(partitions["validation"]),
        test=tuple(partitions["test"]),
    )
