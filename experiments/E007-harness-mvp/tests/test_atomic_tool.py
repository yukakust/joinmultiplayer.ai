import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
BUILDER_PATH = ROOT / "experiments/E007-harness-mvp/src/build_atomic_tool_world.py"
SPEC = importlib.util.spec_from_file_location("build_atomic_tool_world", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class AtomicToolWorldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads((ROOT / "site/experiments/E007/atomic-tool-protocol-v0.1.json").read_text())
        cls.world = json.loads((ROOT / "site/experiments/E007/atomic-tool-world-v0.1.json").read_text())

    def test_protocol_and_world_are_frozen_before_inference(self):
        self.assertEqual(self.protocol["status"], "locked_before_inference")
        self.assertEqual(self.world["status"], "frozen_before_inference")

    def test_world_has_every_combination_in_every_domain(self):
        cases = self.world["cases"]
        self.assertEqual(len(cases), 64)
        self.assertEqual(len({case["domain"] for case in cases}), 8)
        expected = set(BUILDER.COMBINATIONS)
        for domain in {case["domain"] for case in cases}:
            self.assertEqual({case["combination"] for case in cases if case["domain"] == domain}, expected)

    def test_each_atomic_link_is_balanced(self):
        for key in ("source_supports_rule", "facts_support_condition", "answer_follows_consequence"):
            counts = {decision: sum(case["expected"][key] == decision for case in self.world["cases"])
                      for decision in ("supported", "not_enough")}
            self.assertEqual(counts, {"supported": 32, "not_enough": 32})

    def test_only_all_supported_is_used(self):
        useful = [case for case in self.world["cases"] if case["expected"]["final"] == "use"]
        self.assertEqual(len(useful), 8)
        self.assertTrue(all(case["combination"] == "111" for case in useful))

    def test_builder_reproduces_published_world(self):
        self.assertEqual(BUILDER.build(), self.world)


if __name__ == "__main__":
    unittest.main()
