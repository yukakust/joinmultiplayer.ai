import sys
import unittest
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evaluate_gate5c import CONDITIONS, SHELF_CONDITIONS, old_additive_records, write_checkpoint  # noqa: E402


class Gate5CEvaluationTest(unittest.TestCase):
    def test_frozen_condition_order_and_shelf_modes(self):
        self.assertEqual(CONDITIONS[0], "old_additive_merger")
        self.assertEqual(CONDITIONS[1], "separate_shelves_correct_pair")
        self.assertEqual(SHELF_CONDITIONS["separate_shelves_correct_pair"], "correct_shelves")
        self.assertEqual(SHELF_CONDITIONS["empty_shelves"], "empty")

    def test_old_additive_result_is_reused_without_renaming_its_score(self):
        source = {
            "records": [
                {"condition": "correct_neural_pair", "automatic_score": {"complete": True}},
                {"condition": "shared_qwen_alone", "automatic_score": {"complete": False}},
            ]
        }
        records = old_additive_records(source)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["condition"], "old_additive_merger")
        self.assertEqual(records[0]["source_condition"], "correct_neural_pair")
        self.assertTrue(records[0]["automatic_score"]["complete"])

    def test_generation_mask_may_have_a_gap_before_new_tokens(self):
        attention = torch.tensor([[1, 1, 0, 0, 1], [1, 1, 1, 0, 1]])
        physical = torch.arange(attention.shape[1]).unsqueeze(0)
        last_index = physical.masked_fill(attention == 0, -1).max(dim=1).values
        logical_position = attention.sum(dim=-1) - 1
        self.assertEqual(last_index.tolist(), [4, 4])
        self.assertEqual(logical_position.tolist(), [2, 3])

    def test_checkpoint_is_atomic_and_resumable(self):
        from tempfile import TemporaryDirectory
        from types import SimpleNamespace

        with TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            args = SimpleNamespace(output=output)
            records = [{"condition": "old_additive_merger", "question_id": "Q1"}]
            write_checkpoint(
                args,
                records,
                status="running_intermediate_not_result",
                metadata={"max_new_tokens": 256},
            )
            saved = __import__("json").loads(output.read_text())
            self.assertEqual(saved["records_completed"], 1)
            self.assertEqual(saved["records"], records)
            self.assertFalse(output.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
