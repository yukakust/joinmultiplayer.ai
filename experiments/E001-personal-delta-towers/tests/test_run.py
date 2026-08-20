import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT_ROOT / "src"))

from e001.run import _run_labels, run_experiment, run_suite  # noqa: E402


class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(
            (EXPERIMENT_ROOT / "configs" / "pilot.json").read_text(encoding="utf-8")
        )

    def test_smoke_run_is_auditable_and_transactional(self) -> None:
        config = copy.deepcopy(self.config)
        with tempfile.TemporaryDirectory() as temporary:
            summary = run_experiment(
                config,
                smoke=True,
                artifacts_root=Path(temporary),
                identifier="unit-smoke",
            )

            self.assertEqual(summary["status"], "development_smoke")
            self.assertEqual(summary["advancement_decision"], "informational_smoke_only")
            self.assertEqual(len(summary["experts"]), 8)
            self.assertEqual(
                len({expert["logical_id"] for expert in summary["experts"]}), 8
            )
            self.assertEqual(
                summary["world"]["configured_split_fractions"],
                {"train": 0.7, "validation": 0.15, "test": 0.15},
            )
            for candidates in summary["router"].values():
                self.assertEqual(len(candidates), 2)
                self.assertNotEqual(
                    candidates[0]["logical_id"], candidates[1]["logical_id"]
                )

            self.assertEqual(summary["audit"]["partial_payloads_merged"], 0)
            self.assertTrue(
                summary["audit"][
                    "all_forced_primary_failures_recovered_by_complete_backup"
                ]
            )
            self.assertTrue(summary["world"]["key_split"]["all_disjoint"])
            self.assertEqual(
                summary["world"]["key_split"]["counts"]["train"],
                {specialty: 5 for specialty in summary["world"]["specialties"]},
            )
            self.assertEqual(
                summary["world"]["key_split"]["counts"]["validation"],
                {specialty: 1 for specialty in summary["world"]["specialties"]},
            )
            self.assertEqual(
                summary["world"]["key_split"]["counts"]["test"],
                {specialty: 2 for specialty in summary["world"]["specialties"]},
            )
            self.assertTrue(
                all(
                    summary["information_boundaries"][
                        "frozen_assertions_before_head_training"
                    ].values()
                )
            )
            self.assertIn("z0 + Clip(Merge", summary["neural_abi"]["equation"])
            self.assertFalse(summary["neural_abi"]["z0_transform_trainable"])
            self.assertEqual(len(summary["metrics"]["per_ordered_specialty_pair"]), 12)
            self.assertEqual(
                sum(summary["world"]["class_distribution"]["test"]),
                summary["world"]["task_counts"]["test_split"],
            )
            self.assertEqual(len(summary["hashes"]["effective_config_sha256"]), 64)
            self.assertEqual(
                len(summary["hashes"]["private_world_and_splits_sha256"]), 64
            )
            self.assertTrue(summary["audit"]["distinct_poisoned_partial_hash_sets"])
            self.assertTrue(
                summary["audit"]["poisoned_partial_selected_result_invariant"]
            )
            self.assertIn("matched_no_knowledge_prior", summary["metrics"]["accuracy"])
            self.assertIn("base_only_z0", summary["metrics"]["accuracy"])
            self.assertIn("zero_clone_compute_matched", summary["metrics"]["accuracy"])
            self.assertIn("single_first_learned", summary["metrics"]["accuracy"])
            self.assertIn("single_second_learned", summary["metrics"]["accuracy"])
            self.assertIn("oracle_memory", summary["metrics"]["accuracy"])

            summary_path = Path(summary["audit"]["summary_json"])
            tasks_path = Path(summary["audit"]["task_jsonl"])
            self.assertTrue(summary_path.is_file())
            self.assertTrue(tasks_path.is_file())
            persisted = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["world"]["world_id"], summary["world"]["world_id"])
            records = [
                json.loads(line)
                for line in tasks_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(records), summary["audit"]["task_records"])
            self.assertGreater(len(records), 0)
            for record in records:
                self.assertAlmostEqual(record["source_z0_norm"], 1.0, places=5)
                for role in record["routing"]["forced_primary_failures"]:
                    self.assertTrue(role["primary_failed"])
                    self.assertEqual(role["selected"], role["candidates"][1])
                    self.assertFalse(role["partial_payload_merged"])

            # Integration-level transaction test: the runner generated two
            # genuinely different poisoned partial buffers, yet both selected
            # the exact same complete backup capsules and model result.
            self.assertTrue(
                set(summary["audit"]["poison_variant_one_hashes"]).isdisjoint(
                    summary["audit"]["poison_variant_two_hashes"]
                )
            )

    def test_rejects_wrong_number_of_experts(self) -> None:
        config = copy.deepcopy(self.config)
        config["world"]["experts_per_specialty"] = 1
        with self.assertRaisesRegex(ValueError, "exactly two"):
            run_experiment(config, smoke=True, artifacts_root=Path("/tmp/unused"))

    def test_stage_labels_never_advance_from_one_locked_seed(self) -> None:
        self.assertEqual(
            _run_labels(stage="development", smoke=False, gates_passed=True),
            ("development", "development_gates_passed_not_locked"),
        )
        self.assertEqual(
            _run_labels(stage="locked_pilot", smoke=False, gates_passed=True),
            ("locked_pilot", "seed_passed_await_locked_suite"),
        )
        self.assertEqual(
            _run_labels(stage="locked_pilot", smoke=True, gates_passed=True),
            ("development_smoke", "informational_smoke_only"),
        )

    def test_two_seed_smoke_suite_has_separate_runs_and_honest_aggregate(self) -> None:
        config = copy.deepcopy(self.config)
        config["stage"] = "locked_pilot"
        with tempfile.TemporaryDirectory() as temporary:
            summary = run_suite(
                config,
                (101, 102),
                artifacts_root=Path(temporary),
                identifier="unit-two-seed-suite",
                smoke=True,
            )

            self.assertEqual(summary["status"], "development_smoke_suite")
            self.assertEqual(summary["requested_stage"], "locked_pilot")
            self.assertEqual(summary["advancement_decision"], "informational_smoke_only")
            self.assertEqual(summary["seeds"], [101, 102])
            self.assertEqual(len(summary["per_seed"]), 2)
            seed_dirs = {
                Path(seed["summary_json"]).parent for seed in summary["per_seed"]
            }
            self.assertEqual(len(seed_dirs), 2)
            self.assertTrue(all(path.parent.name == "unit-two-seed-suite" for path in seed_dirs))
            self.assertTrue(
                all(seed["status"] == "development_smoke" for seed in summary["per_seed"])
            )
            self.assertIsNone(
                summary["aggregate"]["iid_task_confidence_interval"]
            )
            pdt = summary["aggregate"]["conditions"]["pdt_normal"]
            self.assertEqual(set(pdt), {"micro_accuracy", "macro_accuracy"})
            self.assertEqual(
                set(pdt["micro_accuracy"]), {"mean", "min", "max"}
            )
            self.assertTrue(Path(summary["suite_summary_json"]).is_file())


if __name__ == "__main__":
    unittest.main()
