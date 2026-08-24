from __future__ import annotations

import ast
import importlib.util
import json
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
SOURCE = EXPERIMENT / "src" / "run_base_preflight.py"
RESULT = EXPERIMENT.parents[1] / "site" / "experiments" / "E005" / "base-preflight-public-v0.1.json"


class BasePreflightContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_runner_never_imports_training_or_adapter_packages(self) -> None:
        imported = {
            alias.name
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("peft", imported)
        self.assertNotIn("trl", imported)

    def test_runner_uses_greedy_generation_and_local_model_only(self) -> None:
        self.assertIn("do_sample=False", self.source)
        self.assertIn("local_files_only=True", self.source)
        self.assertIn('"rag": False', self.source)
        self.assertIn('"documents_in_prompt": False', self.source)

    def test_prompt_templates_do_not_contain_fixture_entities_or_answers(self) -> None:
        spec = importlib.util.spec_from_file_location("e005_base_preflight", SOURCE)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        serialized = " ".join(module.PROMPTS.values()).lower()
        for forbidden in ("kest", "orin", "vela", "aster", "mira", "rill", "niv-3", "t4"):
            self.assertNotIn(forbidden, serialized)

    def test_all_six_tasks_have_bilingual_review_markers(self) -> None:
        spec = importlib.util.spec_from_file_location("e005_base_preflight_markers", SOURCE)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual(set(module.TARGET_MARKERS), {f"PUBLIC-{index:02d}" for index in range(1, 7)})
        self.assertTrue(all(set(markers) == {"en", "ru"} for markers in module.TARGET_MARKERS.values()))

    def test_public_result_preserves_all_twelve_raw_generations(self) -> None:
        result = json.loads(RESULT.read_text(encoding="utf-8"))
        self.assertEqual(len(result["rows"]), 6)
        self.assertTrue(all(set(row["outputs"]) == {"en", "ru"} for row in result["rows"]))
        self.assertTrue(all(row["outputs"][language]["output"] for row in result["rows"] for language in ("en", "ru")))
        self.assertFalse(result["model"]["training_or_weight_update"])
        self.assertFalse(result["inference"]["rag"])
        self.assertIsNone(result["inference"]["adapter"])

    def test_manual_review_summary_matches_labels(self) -> None:
        result = json.loads(RESULT.read_text(encoding="utf-8"))
        labels = [row["outputs"][language]["manual_review"] for row in result["rows"] for language in ("en", "ru")]
        safe_incomplete = sum(label == "safe_but_incomplete" for label in labels)
        wrong = sum(label.startswith("wrong_") for label in labels)
        self.assertEqual(result["summary"]["generations"], len(labels))
        self.assertEqual(result["summary"]["safe_but_incomplete_generations"], safe_incomplete)
        self.assertEqual(result["summary"]["hallucinated_or_wrong_generations"], wrong)
        self.assertEqual(result["summary"]["fully_correct_generations"], 0)


if __name__ == "__main__":
    unittest.main()
