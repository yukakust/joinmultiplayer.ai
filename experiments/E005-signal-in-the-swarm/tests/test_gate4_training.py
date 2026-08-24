from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
ROOT = EXPERIMENT.parents[1]
sys.path.insert(0, str(EXPERIMENT / "src"))
SPEC = importlib.util.spec_from_file_location("e005_gate4_train", EXPERIMENT / "src/train_gate4.py")
TRAIN = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(TRAIN)
DATA_PATH = ROOT / "site/experiments/E005/gate-4-data-v0.1.json"
SMOKE_PATH = ROOT / "site/experiments/E005/gate-4-smoke-v0.1.json"


class FakeTokenizer:
    eos_token = "<eos>"

    def __call__(self, value, **kwargs):
        ids = [ord(char) % 127 + 1 for char in value]
        max_length = kwargs.get("max_length")
        if max_length:
            ids = ids[:max_length]
            mask = [1] * len(ids)
            if kwargs.get("padding") == "max_length":
                mask += [0] * (max_length - len(ids))
                ids += [0] * (max_length - len(ids))
            if kwargs.get("return_tensors") == "pt":
                import torch
                return {"input_ids": torch.tensor([ids]), "attention_mask": torch.tensor([mask])}
        return {"input_ids": ids}


class Gate4TrainingTests(unittest.TestCase):
    def test_runner_uses_real_dora_and_keeps_base_separate(self) -> None:
        source = (EXPERIMENT / "src/train_gate4.py").read_text(encoding="utf-8")
        self.assertIn("use_dora=True", source)
        self.assertIn('target_modules=["q_proj", "v_proj"]', source)
        self.assertIn("base_hash_before == base_hash_after", source)

    def test_only_training_split_is_loaded(self) -> None:
        _payload, rows = TRAIN.load_rows(DATA_PATH, "archivist", "correct")
        self.assertEqual(len(rows), 96)
        self.assertEqual({row["split"] for row in rows}, {"train"})

    def test_shuffled_control_changes_targets_but_not_inputs(self) -> None:
        _payload, correct = TRAIN.load_rows(DATA_PATH, "safety_keeper", "correct")
        _payload, shuffled = TRAIN.load_rows(DATA_PATH, "safety_keeper", "shuffled")
        self.assertEqual([row["input"] for row in correct], [row["input"] for row in shuffled])
        self.assertNotEqual([row["target"] for row in correct], [row["target"] for row in shuffled])
        for correct_row, shuffled_row in zip(correct, shuffled, strict=True):
            self.assertIn(correct_row["entity"], shuffled_row["target"])
            self.assertEqual(correct_row["language"], shuffled_row["language"])
            if correct_row["language"] == "ru":
                self.assertNotIn("The required evidence", shuffled_row["target"])

    def test_prompt_tokens_are_hidden_from_loss(self) -> None:
        _payload, rows = TRAIN.load_rows(DATA_PATH, "archivist", "correct")
        encoded = TRAIN.encode_row(FakeTokenizer(), rows[0], 512)
        labels = encoded["labels"]
        self.assertTrue((labels == -100).any())
        self.assertTrue((labels != -100).any())

    def test_public_smoke_is_not_claimed_as_skill_evidence(self) -> None:
        smoke = json.loads(SMOKE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(smoke["claim_status"], "plumbing_only_not_skill_evidence")
        self.assertTrue(smoke["result"]["base_unchanged"])
        self.assertEqual(smoke["method"]["adapter"], "DoRA")


if __name__ == "__main__":
    unittest.main()
