import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
BUILDER_PATH = ROOT / "experiments/E007-harness-mvp/src/build_atomic_button_world.py"
SPEC = importlib.util.spec_from_file_location("build_atomic_button_world", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)

RUNNER_PATH = ROOT / "experiments/E007-harness-mvp/src/run_atomic_button_test.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("run_atomic_button_test", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(RUNNER)


class AtomicButtonWorldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads((ROOT / "site/experiments/E007/atomic-button-protocol-v0.1.json").read_text())
        cls.world = json.loads((ROOT / "site/experiments/E007/atomic-button-world-v0.1.json").read_text())

    def test_inputs_are_frozen(self):
        self.assertEqual(self.protocol["status"], "locked_before_inference")
        self.assertEqual(self.world["status"], "frozen_before_inference")

    def test_exactly_ten_unique_questions(self):
        cases = self.world["cases"]
        self.assertEqual(len(cases), 10)
        self.assertEqual(len({case["question"] for case in cases}), 10)
        self.assertEqual(len({case["domain"] for case in cases}), 10)

    def test_three_useful_and_seven_traps(self):
        counts = {name: sum(case["expected"]["final"] == name for case in self.world["cases"])
                  for name in ("use", "do_not_use")}
        self.assertEqual(counts, {"use": 3, "do_not_use": 7})

    def test_each_single_failure_is_visible(self):
        combinations = {case["combination"] for case in self.world["cases"]}
        self.assertTrue({"011", "101", "110"}.issubset(combinations))

    def test_builder_reproduces_world(self):
        self.assertEqual(BUILDER.build(), self.world)

    def test_actions_are_one_token(self):
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(RUNNER.MODEL_PATH, local_files_only=True)
        self.assertEqual([len(tokenizer.encode(action, add_special_tokens=False)) for action in RUNNER.ACTIONS], [1, 1])

    def test_combiner_requires_three_accepts(self):
        all_accept = {link: "accept" for link in RUNNER.LINKS}
        self.assertEqual(RUNNER.combine(all_accept), "use")
        for link in RUNNER.LINKS:
            decisions = dict(all_accept)
            decisions[link] = "reject"
            self.assertEqual(RUNNER.combine(decisions), "do_not_use")

    def test_each_prompt_contains_only_its_comparison(self):
        case = self.world["cases"][0]
        source = RUNNER.prompt_for(case, "source_supports_rule")
        facts = RUNNER.prompt_for(case, "facts_support_condition")
        answer = RUNNER.prompt_for(case, "answer_follows_consequence")
        self.assertIn(case["source_window"], source)
        self.assertNotIn(case["current_facts"], source)
        self.assertIn(case["current_facts"], facts)
        self.assertNotIn(case["proposed_answer"], facts)
        self.assertIn(case["proposed_answer"], answer)
        self.assertNotIn(case["source_window"], answer)

    def test_result_has_ten_visible_records_if_published(self):
        path = ROOT / "site/experiments/E007/atomic-button-result-v0.1.json"
        if not path.exists():
            self.skipTest("result not published yet")
        result = json.loads(path.read_text())
        self.assertEqual(result["summary"]["total_cases"], 10)
        self.assertEqual(result["summary"]["total_button_decisions"], 30)
        self.assertEqual(len(result["records"]), 10)


if __name__ == "__main__":
    unittest.main()
