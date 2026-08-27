import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
MODULE_PATH = ROOT / "experiments/E007-harness-mvp/src/run_chunking_test.py"
SPEC = importlib.util.spec_from_file_location("run_chunking_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ChunkingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = json.loads((ROOT / "site/experiments/E007/chunking-world-v0.1.json").read_text())
        cls.source, cls.ranges = MODULE.build_source(cls.world["source"]["blocks"])

    def test_source_ranges_round_trip(self):
        data = self.source.encode("utf-8")
        for block in self.world["source"]["blocks"]:
            start, end = self.ranges[block["id"]]
            self.assertEqual(data[start:end].decode("utf-8"), block["text"])

    def test_fixed_chunks_do_not_overlap(self):
        chunks = MODULE.fixed_word_chunks(self.source, self.ranges)
        for left, right in zip(chunks, chunks[1:]):
            self.assertLess(left["byte_end"], right["byte_start"])

    def test_structure_window_preserves_neighbours(self):
        chunks = MODULE.structure_windows(self.source, self.world["source"]["blocks"], self.ranges)
        a06 = next(item for item in chunks if item["focus_atom"] == "A06")
        self.assertEqual(a06["atoms"], ["A05", "A06", "A07"])
        a14 = next(item for item in chunks if item["focus_atom"] == "A14")
        self.assertEqual(a14["atoms"], ["A13", "A14", "A15"])

    def test_decision_uses_frozen_band(self):
        policy = {"reject_at_or_below": 0.1, "accept_at_or_above": 0.9}
        self.assertEqual(MODULE.decision(0.95, policy), "take")
        self.assertEqual(MODULE.decision(0.50, policy), "not_sure")
        self.assertEqual(MODULE.decision(0.01, policy), "drop")

    def test_evaluator_does_not_hide_missing_atom(self):
        chunks = [{"id":"X","byte_start":0,"byte_end":1,"text":"x","atoms":[]}]
        questions = [{"id":"Q","text":"q","required_atoms":["A1"]}]
        result = MODULE.evaluate_method("test", chunks, questions, [[0.99]], {"reject_at_or_below":0.1,"accept_at_or_above":0.9})
        self.assertEqual(result["summary"]["complete_questions"], 0)
        self.assertEqual(result["records"][0]["missing_atoms"], ["A1"])


if __name__ == "__main__":
    unittest.main()
