from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
ROOT = EXPERIMENT.parents[1]
SPEC = importlib.util.spec_from_file_location("e005_gate4_data", EXPERIMENT / "src/build_gate4_data.py")
DATA = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(DATA)


class Gate4DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = DATA.build()

    def test_counts_and_languages_are_balanced(self) -> None:
        for skill in ("archivist", "safety_keeper"):
            for split, count in DATA.COUNTS.items():
                rows = [row for row in self.data["examples"] if row["skill"] == skill and row["split"] == split]
                self.assertEqual(len(rows), count)
                self.assertEqual(sum(row["language"] == "en" for row in rows), count // 2)
                self.assertEqual(sum(row["language"] == "ru" for row in rows), count // 2)

    def test_train_and_held_out_entities_do_not_overlap(self) -> None:
        for skill in DATA.ENTITIES:
            train = {row["entity"] for row in self.data["examples"] if row["skill"] == skill and row["split"] == "train"}
            held = {row["entity"] for row in self.data["examples"] if row["skill"] == skill and row["split"] == "held_out"}
            self.assertTrue(train.isdisjoint(held))

    def test_no_exact_input_or_target_crosses_splits(self) -> None:
        for skill in DATA.ENTITIES:
            train = [row for row in self.data["examples"] if row["skill"] == skill and row["split"] == "train"]
            held = [row for row in self.data["examples"] if row["skill"] == skill and row["split"] == "held_out"]
            self.assertTrue({row["input"] for row in train}.isdisjoint(row["input"] for row in held))
            self.assertTrue({row["target"] for row in train}.isdisjoint(row["target"] for row in held))

    def test_gate3_names_never_appear(self) -> None:
        serialized = json.dumps(self.data, ensure_ascii=False).lower()
        for entity in ("kest-7", "orin-4", "vela-2", "aster-9", "mira-3", "rill-5"):
            self.assertNotIn(entity, serialized)

    def test_build_is_deterministic(self) -> None:
        self.assertEqual(DATA.build(), DATA.build())


if __name__ == "__main__":
    unittest.main()
