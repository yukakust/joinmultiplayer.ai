import importlib.util
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("e007_world", ROOT / "experiments/E007-harness-mvp/src/build_world.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class WorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = MODULE.build()
        cls.documents = {document["id"]: document for document in cls.world["documents"]}

    def test_exact_scope(self):
        self.assertEqual(64, len(self.world["pockets"]))
        self.assertEqual(30, len(self.world["tasks"]))
        self.assertEqual({"yukabox": 32, "owner-macbook": 32}, Counter(pocket["device"] for pocket in self.world["pockets"]))
        self.assertEqual(6, len({task["forbidden_canaries"][0] for task in self.world["tasks"] if task["forbidden_canaries"]}))

    def test_six_tasks_per_family(self):
        counts = Counter(task["family"] for task in self.world["tasks"])
        self.assertEqual(5, len(counts))
        self.assertEqual({6}, set(counts.values()))

    def test_every_pocket_has_separate_memory_and_five_to_twenty_documents(self):
        counts = Counter(document["owner"] for document in self.world["documents"])
        self.assertEqual(64, len(counts))
        self.assertTrue(all(5 <= count <= 20 for count in counts.values()))
        self.assertTrue(all(pocket["memory"] == "private_separate_store" for pocket in self.world["pockets"]))

    def test_sources_are_valid_and_distributed(self):
        pocket_ids = {pocket["id"] for pocket in self.world["pockets"]}
        self.assertTrue(all(document["owner"] in pocket_ids for document in self.world["documents"]))
        for task in self.world["tasks"]:
            self.assertEqual(len(task["all_candidate_sources"]), len(set(task["all_candidate_sources"])))
            self.assertTrue(all(source in self.documents for source in task["all_candidate_sources"]))
            self.assertGreaterEqual(len(task["required_pockets"]), 2)
            self.assertLessEqual(len(task["required_pockets"]), 4)

    def test_minority_lineage_and_secret_policy_are_visible(self):
        minority_tasks = [task for task in self.world["tasks"] if task["family"] == "preserve_supported_minority"]
        for task in minority_tasks:
            lineages = [self.documents[source]["lineage"] for source in task["distractor_sources"]]
            self.assertEqual(1, len(set(lineages)))
            self.assertIn("minority_to_preserve", task["expected"])
        secret_tasks = [task for task in self.world["tasks"] if task["family"] == "prevent_secret_leak"]
        for task in secret_tasks:
            canary = task["forbidden_canaries"][0]
            mixed = [self.documents[source] for source in task["required_sources"] if self.documents[source]["classification"] == "mixed_with_synthetic_secret"]
            self.assertEqual(1, len(mixed))
            self.assertIn(canary, mixed[0]["text"])
            self.assertNotIn(canary, mixed[0]["safe_excerpt"])
            owner = next(pocket for pocket in self.world["pockets"] if pocket["id"] == mixed[0]["owner"])
            self.assertNotIn(canary, " ".join(owner["published_capability_tags"]))

    def test_required_documents_are_discoverable_by_public_capability(self):
        pockets = {pocket["id"]: pocket for pocket in self.world["pockets"]}
        for task in self.world["tasks"]:
            for source in task["required_sources"]:
                document = self.documents[source]
                advertised = set(pockets[document["owner"]]["published_capability_tags"])
                useful_tags = set(document["tags"]) - {"contains-secret", "background-noise"}
                self.assertTrue(useful_tags & advertised)

    def test_no_inference_or_result_fields(self):
        self.assertEqual("deterministic_code_only_no_model", self.world["generation"])
        self.assertNotIn("results", self.world)
        self.assertTrue(all(pocket["status"] == "planned_not_running" for pocket in self.world["pockets"]))


if __name__ == "__main__":
    unittest.main()
