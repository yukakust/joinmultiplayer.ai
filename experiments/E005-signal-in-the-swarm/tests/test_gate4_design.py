from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DESIGN = json.loads((ROOT / "site/experiments/E005/gate-4-design-v0.1.json").read_text(encoding="utf-8"))
DATA = json.loads((ROOT / "site/experiments/E005/gate-4-data-v0.1.json").read_text(encoding="utf-8"))


class Gate4DesignTests(unittest.TestCase):
    def test_design_cannot_claim_training_or_results(self) -> None:
        self.assertEqual(DESIGN["status"], "training_authorized_data_frozen")
        self.assertEqual(DESIGN["claim_status"], "design_only_no_results")
        self.assertFalse(DESIGN["weights_changed"])
        self.assertTrue(DESIGN["base_model"]["frozen"])
        self.assertTrue(DESIGN["owner_authorization"]["approved"])
        self.assertEqual(DESIGN["dataset"]["examples"], 336)
        self.assertEqual(DESIGN["dataset"]["content_sha256"], DATA["content_sha256"])

    def test_personal_skills_have_disjoint_entities(self) -> None:
        all_train = set()
        all_held_out = set()
        for pocket in DESIGN["pockets"]:
            train = set(pocket["train_entities"])
            held_out = set(pocket["held_out_entities"])
            self.assertTrue(train.isdisjoint(held_out))
            all_train.update(train)
            all_held_out.update(held_out)
        self.assertTrue(all_train.isdisjoint(all_held_out))

    def test_gate3_entities_are_not_reused(self) -> None:
        serialized = json.dumps(DESIGN, ensure_ascii=False).lower()
        for entity in ("kest-7", "orin-4", "vela-2", "aster-9", "mira-3", "rill-5"):
            self.assertNotIn(entity, serialized)

    def test_controls_can_detect_skill_and_memorization(self) -> None:
        controls = set(DESIGN["comparison"])
        self.assertIn("frozen base without adapter", controls)
        self.assertIn("the wrong pocket's DoRA adapter", controls)
        self.assertIn("a DoRA adapter trained on shuffled actions", controls)
        self.assertIn("memorization_guard", DESIGN["pass_fail"])


if __name__ == "__main__":
    unittest.main()
