import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arena_common import (  # noqa: E402
    Contribution,
    assemble,
    exact_rag_contribution,
    harness_self_test,
    load_world,
)
from run_rag_swarm import adversarial_controls  # noqa: E402


class ArenaCommonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = load_world(ROOT / "sample-tasks.json")

    def test_harness_recomputes_every_answer(self):
        result = harness_self_test(self.world)
        self.assertEqual(result["status"], "passed")
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(result["exact_rag_control"]["complete_exact_match"], 1.0)

    def test_atomic_assembly_rejects_partial_duplicate_and_wrong_task(self):
        task = self.world["tasks"][5]
        full = [exact_rag_contribution(self.world, task, pocket) for pocket in task["required_pockets"]]
        self.assertEqual(assemble(task, full[:-1]).reason, "missing_required_pocket")
        partial = [*full[:-1], Contribution(task["id"], full[-1].pocket_id, full[-1].result, False)]
        self.assertEqual(assemble(task, partial).reason, "partial_contribution")
        self.assertEqual(assemble(task, [*full, full[0]]).reason, "duplicate_pocket")
        wrong = [Contribution("OTHER", item.pocket_id, item.result) for item in full]
        self.assertEqual(assemble(task, wrong).reason, "task_id_mismatch")

    def test_out_of_range_and_unexpected_pockets_are_rejected(self):
        task = self.world["tasks"][0]
        self.assertEqual(
            assemble(task, [Contribution(task["id"], "P01", 997)]).reason,
            "result_out_of_range",
        )
        self.assertEqual(
            assemble(task, [Contribution(task["id"], "P09", 1)]).reason,
            "unexpected_pocket",
        )

    def test_rag_controls_expose_stale_record_limitation(self):
        controls = adversarial_controls(self.world)
        self.assertEqual(controls["missing_required_safe_rate"], 1.0)
        self.assertEqual(controls["partial_safe_rate"], 1.0)
        self.assertEqual(controls["duplicate_rejection_rate"], 1.0)
        self.assertEqual(controls["irrelevant_rejection_rate"], 1.0)
        self.assertEqual(controls["stale_detection_rate"], 0.0)
        self.assertGreater(len(controls["stale_failures"]), 0)


if __name__ == "__main__":
    unittest.main()
