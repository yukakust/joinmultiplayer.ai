import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CLIENT_PATH = ROOT / "site" / "experiments" / "E007" / "local-offer-node-v0.1.py"
MEMORY_PATH = ROOT / "site" / "experiments" / "E007" / "local-memory-v0.1.json"
PROTOCOL_PATH = ROOT / "site" / "experiments" / "E007" / "local-offer-protocol-v0.1.json"
SPEC = importlib.util.spec_from_file_location("e007_local_offer", CLIENT_PATH)
CLIENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLIENT)


class LocalOfferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.memory = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        cls.protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))

    def test_locked_world_has_four_distinct_six_document_libraries(self):
        self.assertEqual(set(self.memory["libraries"]), {"ATT-Y1", "ATT-Y2", "ATT-M1", "ATT-M2"})
        all_ids = []
        for documents in self.memory["libraries"].values():
            self.assertEqual(len(documents), 6)
            all_ids.extend(document["id"] for document in documents)
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_every_required_source_exists_and_expected_matrix_is_complete(self):
        source_ids = {
            document["id"]
            for documents in self.memory["libraries"].values()
            for document in documents
        }
        for question in self.protocol["questions"]:
            self.assertEqual(set(question["expected"]), {"ATT-Y1", "ATT-Y2", "ATT-M1", "ATT-M2"})
            self.assertTrue(set(question["required_sources"]) <= source_ids)
        states = [
            state
            for question in self.protocol["questions"]
            for state in question["expected"].values()
        ]
        self.assertEqual(states.count("found"), 5)
        self.assertEqual(states.count("blocked"), 1)
        self.assertEqual(states.count("empty"), 18)

    def test_private_canary_is_only_a_placeholder_in_public_memory(self):
        private = next(
            document
            for document in self.memory["libraries"]["ATT-M1"]
            if document["id"] == "M1-PRIVATE-01"
        )
        self.assertEqual(private["permission"], "blocked")
        self.assertIsNone(private["capsule"])
        self.assertIn("{{SYNTHETIC_PRIVATE_CANARY}}", private["text"])
        self.assertNotRegex(private["text"], r"[A-Za-z0-9_-]{30,}")

    def test_threshold_maximises_f1_and_breaks_ties_upward(self):
        threshold, f1 = CLIENT.select_threshold([0.9, 0.8, 0.2, 0.1], [True, True, False, False])
        self.assertEqual(threshold, 0.8)
        self.assertEqual(f1, 1.0)

    def test_transparent_search_prefers_obvious_relevant_passages(self):
        query = "Как не выполнить задачу дважды после потери подтверждения?"
        relevant = "После потери подтверждения очередь повторила задачу; idempotency key остановил дубль."
        noise = "Улей прибавил два килограмма мёда."
        self.assertGreater(CLIENT.exact_term_score(query, relevant), CLIENT.exact_term_score(query, noise))
        self.assertGreater(CLIENT.chargram_score(query, relevant), CLIENT.chargram_score(query, noise))


if __name__ == "__main__":
    unittest.main()
