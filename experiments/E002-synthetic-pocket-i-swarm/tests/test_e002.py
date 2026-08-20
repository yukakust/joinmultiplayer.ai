from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from e002.core import CLASSES, Pocket, circular_merge, make_pair_tasks, make_private_world, make_tasks, train_pocket, uniform_capsule  # noqa: E402
from e002.run import run  # noqa: E402


class CoreTests(unittest.TestCase):
    def test_private_namespaces_are_disjoint_and_all_answers_are_possible(self) -> None:
        tables = make_private_world(7, 32, 8)
        keys = [key for table in tables for key in table.keys]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(CLASSES, 256)
        # The operation is modulo 256, so each offset maps any fixed private
        # sum bijectively onto every possible answer.
        self.assertEqual({(offset + 91) % CLASSES for offset in range(CLASSES)}, set(range(CLASSES)))

    def test_each_pocket_really_learns_distinct_personal_weights(self) -> None:
        first, second = make_private_world(11, 2, 8)
        models = [Pocket(first), Pocket(second)]
        before = [model.logits.weight.detach().clone() for model in models]
        for model in models:
            curve = train_pocket(model, 40, 4.0)
            self.assertLess(curve[-1], curve[0])
        self.assertTrue(all(torch.count_nonzero(model.logits.weight.detach() != old) > 0 for model, old in zip(models, before, strict=True)))
        self.assertFalse(torch.equal(models[0].logits.weight, models[1].logits.weight))

    def test_fixed_workload_evenly_covers_ordered_pairs(self) -> None:
        tables = make_private_world(3, 4, 8)
        tasks = make_pair_tasks(5, tables, 24)
        pairs = [task.pocket_ids for task in tasks]
        self.assertEqual(len(set(pairs)), 12)
        self.assertTrue(all(pairs.count(pair) == 2 for pair in set(pairs)))

    def test_z0_and_every_capsule_are_causally_required(self) -> None:
        tables = make_private_world(13, 2, 8); pockets = [Pocket(t) for t in tables]
        for pocket in pockets: train_pocket(pocket, 40, 4.0)
        task = make_tasks(19, tables, 1)[0]
        capsules = [p.capsule(k) for p, k in zip(pockets, task.key_indices, strict=True)]
        full = circular_merge(capsules, task.signs, task.offset)
        missing = circular_merge([capsules[0], uniform_capsule()], task.signs, task.offset)
        self.assertEqual(int(full.argmax()), task.answer)
        self.assertTrue(torch.allclose(missing, uniform_capsule(), atol=1e-6))


class RunnerTests(unittest.TestCase):
    def test_development_run_writes_inspectable_immutable_artifacts(self) -> None:
        config = json.loads((ROOT / "configs" / "draft-r0001.json").read_text())
        config = copy.deepcopy(config); config["swarm_sizes"] = [2, 4]; config["tasks_per_size"] = 4; config["fixed_workload_tasks"] = 12
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            summary = run(config, REPO, artifacts, "test-run")
            self.assertEqual(summary["status"], "development_unlocked_protocol_draft")
            self.assertEqual(summary["answer_classes"], 256)
            self.assertEqual([x["n"] for x in summary["scaling"]], [2, 4])
            self.assertTrue(summary["all_personal_weights_changed"])
            self.assertEqual(len(summary["fixed_workload_curve"]), 2)
            self.assertLess(summary["fixed_workload_curve"][0]["accuracy"], summary["fixed_workload_curve"][1]["accuracy"])
            self.assertIsNotNone(summary["git_revision"])
            self.assertTrue((artifacts / "test-run" / "summary.json").is_file())
            self.assertTrue((artifacts / "test-run" / "tasks.jsonl").is_file())
            manifest = json.loads((artifacts / "test-run" / "manifest.json").read_text())
            self.assertEqual(set(manifest), {"summary.json", "tasks.jsonl", "microscope.html"})
            self.assertTrue(all(len(item["sha256"]) == 64 for item in manifest.values()))
            task = json.loads((artifacts / "test-run" / "tasks.jsonl").read_text().splitlines()[0])
            self.assertEqual(len(task["remove_each_i_predictions"]), task["n"])
            self.assertEqual(task["interruption"]["selected"], "backup")
            self.assertEqual(task["partial_payloads_merged"], 0)
            html = (artifacts / "test-run" / "microscope.html").read_text()
            self.assertIn("PROTOCOL DRAFT", html)
            self.assertIn("Two-pocket training microscope", html)
            with self.assertRaises(FileExistsError):
                run(config, REPO, artifacts, "test-run")

    def test_locked_config_is_rejected(self) -> None:
        config = json.loads((ROOT / "configs" / "draft-r0001.json").read_text())
        config["stage"] = "locked"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "unlocked draft"):
                run(config, REPO, Path(directory), "invalid")


if __name__ == "__main__":
    unittest.main()
