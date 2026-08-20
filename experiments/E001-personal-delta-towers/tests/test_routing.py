import sys
import unittest
from pathlib import Path


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT_ROOT / "src"))

from e001.data import build_private_world, generate_tasks  # noqa: E402
from e001.routing import (  # noqa: E402
    ExpertContribution,
    IncompleteContributionError,
    LogicalExpert,
    TopTwoRouter,
    default_experts,
    select_first_complete,
)


class RoutingTests(unittest.TestCase):
    def test_router_returns_two_distinct_logical_experts_ranked_by_quality(
        self,
    ) -> None:
        router = TopTwoRouter(
            (
                LogicalExpert("chess-c", "chess", 0.72),
                LogicalExpert("chess-a", "chess", 0.95),
                LogicalExpert("chess-b", "chess", 0.83),
            )
        )

        route = router.route_specialty("chess")

        self.assertEqual(
            tuple(expert.logical_id for expert in route.candidates),
            ("chess-a", "chess-b"),
        )
        self.assertEqual(len({expert.logical_id for expert in route.candidates}), 2)

    def test_default_roster_routes_two_distinct_experts_for_each_task_specialty(
        self,
    ) -> None:
        task = generate_tasks(build_private_world(seed=1, keys_per_specialty=2))[0]
        plan = TopTwoRouter(default_experts()).route_task(task)

        self.assertEqual(tuple(route.specialty for route in plan.routes), task.specialties)
        for route in plan.routes:
            self.assertEqual(
                len({candidate.logical_id for candidate in route.candidates}), 2
            )

    def test_incomplete_primary_is_discarded_and_complete_backup_is_selected(
        self,
    ) -> None:
        partial_capsule = object()
        backup_capsule = object()
        primary = ExpertContribution.incomplete(
            "chess-primary", "chess", partial_capsule
        )
        backup = ExpertContribution.complete(
            "chess-backup", "chess", backup_capsule
        )

        selected = select_first_complete((primary, backup))

        self.assertIs(selected, backup)
        self.assertIs(selected.payload, backup_capsule)
        with self.assertRaises(IncompleteContributionError):
            _ = primary.payload

    def test_no_complete_candidate_returns_none(self) -> None:
        candidates = (
            ExpertContribution.incomplete("chess-primary", "chess", object()),
            ExpertContribution.incomplete("chess-backup", "chess", object()),
        )

        self.assertIsNone(select_first_complete(candidates))


if __name__ == "__main__":
    unittest.main()
