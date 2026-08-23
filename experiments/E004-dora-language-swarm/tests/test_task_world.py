import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task_world", ROOT / "src" / "task_world.py")
task_world = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(task_world)


class TaskWorldTests(unittest.TestCase):
    def setUp(self):
        self.sample = task_world.build_sample()
        self.books = {book["pocket_id"]: book for book in self.sample["books"]}

    def test_population_contract_separates_surrogates_final_and_public_demo(self):
        population = self.sample["population_contract"]
        groups = [
            set(population["surrogate_ids"]),
            set(population["final_ids"]),
            {population["post_freeze_plugin_id"]},
            set(population["public_demo_ids"]),
        ]
        self.assertEqual([len(group) for group in groups], [16, 8, 1, 8])
        for index, group in enumerate(groups):
            for other in groups[index + 1 :]:
                self.assertTrue(group.isdisjoint(other))

    def test_public_books_have_unique_facts_rule_update_and_deletion(self):
        all_keys = set()
        procedures = set()
        for book in self.sample["books"]:
            self.assertEqual(len(book["preview_facts"]), 8)
            self.assertEqual(sum(fact["status"] == "deleted" for fact in book["preview_facts"]), 1)
            self.assertEqual(sum(fact["current_version"] == 2 for fact in book["preview_facts"]), 2)
            keys = {fact["key"] for fact in book["preview_facts"]}
            self.assertTrue(all_keys.isdisjoint(keys))
            all_keys.update(keys)
            procedures.add((book["procedure"]["multiplier"], book["procedure"]["bias"]))
        self.assertEqual(len(procedures), 8)

    def test_every_public_answer_recomputes_from_current_book_state(self):
        for task in self.sample["tasks"]:
            expected = []
            for item in task["derivation"]["contributions"]:
                book = self.books[item["pocket_id"]]
                fact = task_world.find_fact(book, item["fact_key"])
                self.assertEqual(fact["current_version"], item["fact_version"])
                result = task_world.apply_procedure(book, fact)
                self.assertEqual(result, item["result"])
                expected.append(result)
            if any(result is None for result in expected):
                answer = " | ".join(
                    f"{item['pocket_id']}:ABSTAIN"
                    for item in task["derivation"]["contributions"]
                )
            else:
                seal = sum((index + 2) * value for index, value in enumerate(expected)) % task_world.MODULUS
                segments = " | ".join(
                    f"{item['pocket_id']}:{item['result']:03d}"
                    for item in task["derivation"]["contributions"]
                )
                answer = f"{segments} | SEAL:{seal:03d}"
            self.assertEqual(task["answer"], answer)

    def test_answer_space_is_not_a_binary_guess(self):
        self.assertEqual(self.sample["largest_complete_answer_space"], 997**3)
        self.assertEqual(self.sample["triple_blind_guess_probability"], 1 / (997**3))
        self.assertEqual(self.sample["pair_missing_segment_guess_probability"], 1 / 997)
        triple_tasks = [task for task in self.sample["tasks"] if task["type"] == "triple"]
        self.assertTrue(triple_tasks)
        self.assertTrue(all(task["answer_space"] == 997**3 for task in triple_tasks))

    def test_updates_and_deletions_are_visible(self):
        updated = [task for task in self.sample["tasks"] if task["type"] == "updated_fact"]
        deleted = [task for task in self.sample["tasks"] if task["type"] == "deletion"]
        self.assertEqual(len(updated), 1)
        self.assertEqual(len(deleted), 2)
        self.assertTrue(all("ABSTAIN" in task["answer"] for task in deleted))
        for item in updated[0]["derivation"]["contributions"]:
            self.assertEqual(item["fact_version"], 2)

    def test_generator_is_deterministic_and_contains_no_locked_material(self):
        self.assertEqual(self.sample, task_world.build_sample())
        self.assertEqual(self.sample["status"], "public_demo_not_locked")
        self.assertEqual(self.sample["claim_status"], "not_a_result")
        serialized = json.dumps(self.sample).lower()
        self.assertNotIn("locked_seed", serialized)
        self.assertNotIn("private_salt", serialized)
        self.assertIn("no locked salt", self.sample["locked_data_boundary"].lower())

    def test_cli_shape_matches_in_memory_generator(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sample.json"
            output.write_text(
                json.dumps(task_world.build_sample(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), self.sample)


if __name__ == "__main__":
    unittest.main()
