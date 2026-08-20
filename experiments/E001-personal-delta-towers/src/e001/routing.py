"""Deterministic top-2 routing and completion-gated expert selection."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from math import isfinite

from .data import PrivateWorldTask, SPECIALTIES


@dataclass(frozen=True, slots=True)
class LogicalExpert:
    """A unique pocket i, not a physical replica of another expert."""

    logical_id: str
    specialty: str
    validation_quality: float

    def __post_init__(self) -> None:
        if not self.logical_id:
            raise ValueError("logical_id must not be empty")
        if not self.specialty:
            raise ValueError("specialty must not be empty")
        if not isfinite(self.validation_quality):
            raise ValueError("validation_quality must be finite")


@dataclass(frozen=True, slots=True)
class SpecialtyRoute:
    """Two independently learned candidate experts for one specialty."""

    specialty: str
    candidates: tuple[LogicalExpert, LogicalExpert]

    def __post_init__(self) -> None:
        first, second = self.candidates
        if first.logical_id == second.logical_id:
            raise ValueError("top-2 candidates must have distinct logical ids")
        if first.specialty != self.specialty or second.specialty != self.specialty:
            raise ValueError("every candidate must match the routed specialty")


@dataclass(frozen=True, slots=True)
class RoutingPlan:
    """Routes for the ordered specialties required by one task."""

    task_id: str
    routes: tuple[SpecialtyRoute, SpecialtyRoute]


def default_experts() -> tuple[LogicalExpert, ...]:
    """Return two distinct logical pocket i for each E001 specialty."""

    experts: list[LogicalExpert] = []
    for index, specialty in enumerate(SPECIALTIES):
        experts.extend(
            (
                LogicalExpert(
                    logical_id=f"{specialty}-i-a",
                    specialty=specialty,
                    validation_quality=0.90 - index * 0.01,
                ),
                LogicalExpert(
                    logical_id=f"{specialty}-i-b",
                    specialty=specialty,
                    validation_quality=0.80 - index * 0.01,
                ),
            )
        )
    return tuple(experts)


class TopTwoRouter:
    """Rank distinct logical experts by held-out validation quality."""

    def __init__(self, experts: Iterable[LogicalExpert]) -> None:
        by_specialty: dict[str, list[LogicalExpert]] = defaultdict(list)
        seen_ids: set[str] = set()
        for expert in experts:
            if expert.logical_id in seen_ids:
                raise ValueError(f"duplicate logical expert id: {expert.logical_id}")
            seen_ids.add(expert.logical_id)
            by_specialty[expert.specialty].append(expert)

        self._by_specialty: dict[str, tuple[LogicalExpert, ...]] = {}
        for specialty, candidates in by_specialty.items():
            self._by_specialty[specialty] = tuple(
                sorted(
                    candidates,
                    key=lambda candidate: (
                        -candidate.validation_quality,
                        candidate.logical_id,
                    ),
                )
            )

    def route_specialty(self, specialty: str) -> SpecialtyRoute:
        """Return the two best distinct logical experts for ``specialty``."""

        candidates = self._by_specialty.get(specialty, ())
        if len(candidates) < 2:
            raise LookupError(
                f"specialty {specialty!r} needs two distinct logical experts"
            )
        return SpecialtyRoute(
            specialty=specialty,
            candidates=(candidates[0], candidates[1]),
        )

    def route_task(self, task: PrivateWorldTask) -> RoutingPlan:
        """Route both task specialties while preserving their question order."""

        first, second = task.specialties
        return RoutingPlan(
            task_id=task.task_id,
            routes=(self.route_specialty(first), self.route_specialty(second)),
        )


class IncompleteContributionError(RuntimeError):
    """Raised when code tries to expose an unfinished expert payload."""


@dataclass(frozen=True, slots=True)
class ExpertContribution:
    """A buffered expert result whose payload is gated by completion.

    ``_payload`` may be any opaque object, including a torch tensor or a richer
    latent capsule.  An incomplete candidate may contain buffered partial state,
    but callers cannot obtain it through the public ``payload`` property.
    """

    logical_id: str
    specialty: str
    completed: bool
    _payload: object | None = field(default=None, repr=False)

    @classmethod
    def complete(
        cls, logical_id: str, specialty: str, payload: object
    ) -> "ExpertContribution":
        if payload is None:
            raise ValueError("a completed contribution must contain a payload")
        return cls(logical_id, specialty, True, payload)

    @classmethod
    def incomplete(
        cls,
        logical_id: str,
        specialty: str,
        partial_payload: object | None = None,
    ) -> "ExpertContribution":
        return cls(logical_id, specialty, False, partial_payload)

    @property
    def payload(self) -> object:
        if not self.completed:
            raise IncompleteContributionError(
                f"expert {self.logical_id!r} did not finish; partial output is discarded"
            )
        if self._payload is None:
            raise IncompleteContributionError(
                f"expert {self.logical_id!r} reported completion without a payload"
            )
        return self._payload


def select_first_complete(
    candidates: Iterable[ExpertContribution],
) -> ExpertContribution | None:
    """Select the first fully completed candidate in router-ranked order.

    Incomplete candidates are skipped atomically: none of their partial payload
    is returned or merged, even when they precede a successful backup.
    """

    for candidate in candidates:
        if candidate.completed and candidate._payload is not None:
            return candidate
    return None
