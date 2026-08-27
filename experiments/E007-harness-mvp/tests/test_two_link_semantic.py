import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
BUILDER_PATH = ROOT / "experiments/E007-harness-mvp/src/build_two_link_semantic_world.py"
SPEC = importlib.util.spec_from_file_location("build_two_link_semantic_world", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)

RUNNER_PATH = ROOT / "experiments/E007-harness-mvp/src/run_two_link_semantic_test.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("run_two_link_semantic_test", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(RUNNER)


class TwoLinkSemanticWorldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads((ROOT / "site/experiments/E007/two-link-semantic-protocol-v0.1.json").read_text())
        cls.world = json.loads((ROOT / "site/experiments/E007/two-link-semantic-world-v0.1.json").read_text())

    def test_protocol_and_world_are_frozen_before_inference(self):
        self.assertEqual(self.protocol["status"], "locked_before_inference")
        self.assertEqual(self.world["status"], "frozen_before_inference")

    def test_world_is_balanced_across_domains_and_quadrants(self):
        cases = self.world["cases"]
        self.assertEqual(len(cases), 32)
        self.assertEqual(len({case["domain"] for case in cases}), 8)
        counts = {name: sum(case["quadrant"] == name for case in cases) for name in ("yy", "ny", "yn", "nn")}
        self.assertEqual(counts, {"yy": 8, "ny": 8, "yn": 8, "nn": 8})

    def test_each_domain_exercises_all_four_relation_pairs(self):
        for domain in {case["domain"] for case in self.world["cases"]}:
            pairs = {case["quadrant"] for case in self.world["cases"] if case["domain"] == domain}
            self.assertEqual(pairs, {"yy", "ny", "yn", "nn"})

    def test_expected_final_is_derived_from_both_links(self):
        for case in self.world["cases"]:
            expected = case["expected"]
            derived = "take" if expected["quote_supports_claim"] == expected["claim_helps_question"] == "yes" else "drop"
            self.assertEqual(expected["expected_final"], derived)

    def test_builder_reproduces_published_world(self):
        self.assertEqual(BUILDER.build(), self.world)

    def test_combiner_is_plain_and_conservative(self):
        self.assertEqual(RUNNER.combine("yes", "yes"), "take")
        self.assertEqual(RUNNER.combine("yes", "no"), "drop")
        self.assertEqual(RUNNER.combine("no", "yes"), "drop")
        self.assertEqual(RUNNER.combine("not_sure", "yes"), "not_sure")

    def test_prompts_do_not_contain_hidden_expected_labels(self):
        for case in self.world["cases"]:
            for link in ("quote_to_claim", "claim_to_question"):
                prompt = RUNNER.prompt_for(case, link)
                self.assertIn(case["question"], prompt)
                self.assertIn(case["claim"], prompt)
                self.assertNotIn(str(case["expected"]), prompt)
            self.assertIn(case["exact_quote"], RUNNER.prompt_for(case, "quote_to_claim"))
            self.assertNotIn("EXACT SOURCE QUOTE", RUNNER.prompt_for(case, "claim_to_question"))

    def test_published_result_matches_locked_inputs(self):
        path = ROOT / "site/experiments/E007/two-link-semantic-result-v0.1.json"
        if not path.exists():
            self.skipTest("result not published yet")
        result = json.loads(path.read_text())
        self.assertEqual(result["summary"]["total"], 32)
        self.assertEqual(len(result["records"]), 32)


if __name__ == "__main__":
    unittest.main()
