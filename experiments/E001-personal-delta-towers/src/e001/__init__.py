"""Core deterministic primitives for experiment E001."""

from .data import (
    SPECIALTIES,
    FactRef,
    PrivateWorld,
    PrivateWorldTask,
    SplitName,
    TaskSplits,
    build_private_world,
    generate_tasks,
    split_name,
    split_tasks,
)
from .routing import (
    ExpertContribution,
    IncompleteContributionError,
    LogicalExpert,
    RoutingPlan,
    SpecialtyRoute,
    TopTwoRouter,
    default_experts,
    select_first_complete,
)

__all__ = [
    "SPECIALTIES",
    "ExpertContribution",
    "FactRef",
    "IncompleteContributionError",
    "LogicalExpert",
    "PrivateWorld",
    "PrivateWorldTask",
    "RoutingPlan",
    "SpecialtyRoute",
    "SplitName",
    "TaskSplits",
    "TopTwoRouter",
    "build_private_world",
    "default_experts",
    "generate_tasks",
    "select_first_complete",
    "split_name",
    "split_tasks",
]
