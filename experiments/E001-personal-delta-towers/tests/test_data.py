import sys
import unittest
from pathlib import Path


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT_ROOT / "src"))

from e001.data import (  # noqa: E402
    SPECIALTIES,
    build_private_world,
    generate_tasks,
    split_tasks,
    split_tasks_by_keys,
)


class PrivateWorldDataTests(unittest.TestCase):
    def test_private_world_is_reproducible(self) -> None:
        first = build_private_world(seed=73, keys_per_specialty=5)
        second = build_private_world(seed=73, keys_per_specialty=5)

        self.assertEqual(first.world_id, second.world_id)
        self.assertEqual(first.facts, second.facts)
        self.assertEqual(generate_tasks(first), generate_tasks(second))
        self.assertEqual(tuple(first.facts), SPECIALTIES)

    def test_questions_use_ordered_specialty_pairs_and_exact_class(self) -> None:
        world = build_private_world(seed=11, keys_per_specialty=3)
        tasks = generate_tasks(world)

        self.assertEqual(len(tasks), 4 * 3 * 3 * 3)
        self.assertTrue(
            any(
                task.first.specialty == "chess"
                and task.second.specialty == "botany"
                for task in tasks
            )
        )
        self.assertTrue(
            any(
                task.first.specialty == "botany"
                and task.second.specialty == "chess"
                for task in tasks
            )
        )
        for task in tasks:
            self.assertNotEqual(task.first.specialty, task.second.specialty)
            self.assertEqual(task.answer_class, 2 * task.first_bit + task.second_bit)
            self.assertIn(task.answer_class, range(4))

    def test_stable_splits_have_no_overlap(self) -> None:
        tasks = generate_tasks(build_private_world(seed=5, keys_per_specialty=8))
        first = split_tasks(tasks)
        second = split_tasks(reversed(tasks))

        self.assertEqual(first, second)
        train_ids = {task.task_id for task in first.train}
        validation_ids = {task.task_id for task in first.validation}
        test_ids = {task.task_id for task in first.test}

        self.assertTrue(train_ids)
        self.assertTrue(validation_ids)
        self.assertTrue(test_ids)
        self.assertTrue(train_ids.isdisjoint(validation_ids))
        self.assertTrue(train_ids.isdisjoint(test_ids))
        self.assertTrue(validation_ids.isdisjoint(test_ids))
        self.assertEqual(
            train_ids | validation_ids | test_ids,
            {task.task_id for task in tasks},
        )

    def test_configured_split_fractions_are_used(self) -> None:
        tasks = generate_tasks(build_private_world(seed=17, keys_per_specialty=12))
        splits = split_tasks(
            tasks,
            train_fraction=0.7,
            validation_fraction=0.15,
        )
        total = len(tasks)

        self.assertAlmostEqual(len(splits.train) / total, 0.7, delta=0.04)
        self.assertAlmostEqual(len(splits.validation) / total, 0.15, delta=0.03)
        self.assertAlmostEqual(len(splits.test) / total, 0.15, delta=0.03)

    def test_merger_splits_are_deterministic_and_key_disjoint(self) -> None:
        world = build_private_world(seed=29, keys_per_specialty=20)
        first = split_tasks_by_keys(
            world, train_fraction=0.70, validation_fraction=0.15
        )
        second = split_tasks_by_keys(
            world, train_fraction=0.70, validation_fraction=0.15
        )

        self.assertEqual(first, second)
        split_refs: list[set[tuple[str, str]]] = []
        for tasks in (first.train, first.validation, first.test):
            refs = {
                (ref.specialty, ref.key)
                for task in tasks
                for ref in (task.first, task.second)
            }
            split_refs.append(refs)
            for task in tasks:
                self.assertIn((task.first.specialty, task.first.key), refs)
                self.assertIn((task.second.specialty, task.second.key), refs)

        train_refs, validation_refs, test_refs = split_refs
        self.assertTrue(train_refs.isdisjoint(validation_refs))
        self.assertTrue(train_refs.isdisjoint(test_refs))
        self.assertTrue(validation_refs.isdisjoint(test_refs))
        for specialty in SPECIALTIES:
            self.assertEqual(
                sum(ref_specialty == specialty for ref_specialty, _ in train_refs),
                14,
            )
            self.assertEqual(
                sum(
                    ref_specialty == specialty
                    for ref_specialty, _ in validation_refs
                ),
                3,
            )
            self.assertEqual(
                sum(ref_specialty == specialty for ref_specialty, _ in test_refs),
                3,
            )

        self.assertEqual(len(first.train), 4 * 3 * 14 * 14)
        self.assertEqual(len(first.validation), 4 * 3 * 3 * 3)
        self.assertEqual(len(first.test), 4 * 3 * 3 * 3)


if __name__ == "__main__":
    unittest.main()
