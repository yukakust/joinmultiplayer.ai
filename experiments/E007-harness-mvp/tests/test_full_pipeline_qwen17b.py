from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src/run_full_pipeline_qwen17b.py"
SPEC = importlib.util.spec_from_file_location("full_pipeline", MODULE_PATH)
PIPELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIPELINE)


class FullPipelineTest(unittest.TestCase):
    def setUp(self):
        self.world = PIPELINE.read(PIPELINE.WORLD_PATH)

    def test_route_and_local_search_find_locked_required_knowledge(self):
        found_pockets = found_sources = 0
        for task in self.world["tasks"]:
            routed = PIPELINE.route(task["question"], task["family"], self.world["pockets"], 16)
            pocket_ids = {item["pocket_id"] for item in routed}
            found_pockets += set(task["required_pockets"]) <= pocket_ids
            offers = {
                PIPELINE.local_offer(task["question"], item["pocket_id"], self.world["documents"])["id"]
                for item in routed
            }
            found_sources += set(task["required_sources"]) <= offers
        self.assertEqual(found_pockets, 30)
        self.assertEqual(found_sources, 30)

    def test_secret_is_removed_before_anchor(self):
        mixed = next(item for item in self.world["documents"] if item["classification"] == "mixed_with_synthetic_secret")
        fragment, security = PIPELINE.safe_fragment(mixed)
        self.assertTrue(security["redacted"])
        self.assertNotIn(mixed["synthetic_secret_canary"], fragment)
        self.assertTrue(PIPELINE.source_anchor(mixed, fragment)["valid"])

    def test_relevance_has_three_states(self):
        self.assertEqual(PIPELINE.relevance_decision(.95, .92, .01), "take")
        self.assertEqual(PIPELINE.relevance_decision(.5, .92, .01), "not_sure")
        self.assertEqual(PIPELINE.relevance_decision(.001, .92, .01), "drop")

    def test_components_keep_unconnected_claims_separate(self):
        groups = PIPELINE.components(["a", "b", "c"], {("a", "b")})
        self.assertEqual(groups, [["a", "b"], ["c"]])


if __name__ == "__main__":
    unittest.main()
