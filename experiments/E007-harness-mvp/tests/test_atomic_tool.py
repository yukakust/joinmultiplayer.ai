import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
BUILDER_PATH = ROOT / "experiments/E007-harness-mvp/src/build_atomic_tool_world.py"
SPEC = importlib.util.spec_from_file_location("build_atomic_tool_world", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)

RUNNER_PATH = ROOT / "experiments/E007-harness-mvp/src/run_atomic_tool_test.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("run_atomic_tool_test", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(RUNNER)


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

    def test_tools_are_named_decisions_with_empty_arguments(self):
        self.assertEqual([item["function"]["name"] for item in RUNNER.tools_for("normal")], ["supported", "not_enough"])
        self.assertEqual([item["function"]["name"] for item in RUNNER.tools_for("reversed")], ["not_enough", "supported"])
        for definition in RUNNER.TOOL_DEFINITIONS.values():
            self.assertEqual(definition["function"]["parameters"]["properties"], {})

    def test_parser_is_conservative(self):
        yes = '<tool_call>\n{"name":"supported","arguments":{}}\n</tool_call>'
        no = '<tool_call>{"name":"not_enough","arguments":{}}</tool_call>'
        self.assertEqual(RUNNER.parse_tool_call(yes)["decision"], "supported")
        self.assertEqual(RUNNER.parse_tool_call(no)["decision"], "not_enough")
        for malformed in ("supported", yes + no, '<tool_call>{"name":"other","arguments":{}}</tool_call>',
                          '<tool_call>{"name":"supported","arguments":{"x":1}}</tool_call>'):
            parsed = RUNNER.parse_tool_call(malformed)
            self.assertFalse(parsed["valid"])
            self.assertEqual(parsed["decision"], "not_enough")

    def test_combiner_requires_three_supported_decisions(self):
        all_yes = {link: "supported" for link in RUNNER.LINKS}
        self.assertEqual(RUNNER.combine(all_yes), "use")
        for link in RUNNER.LINKS:
            one_no = dict(all_yes)
            one_no[link] = "not_enough"
            self.assertEqual(RUNNER.combine(one_no), "do_not_use")

    def test_prompts_show_only_one_atomic_comparison(self):
        case = self.world["cases"][0]
        source_prompt = RUNNER.prompt_for(case, "source_supports_rule")
        facts_prompt = RUNNER.prompt_for(case, "facts_support_condition")
        answer_prompt = RUNNER.prompt_for(case, "answer_follows_consequence")
        self.assertIn(case["source_window"], source_prompt)
        self.assertNotIn(case["current_facts"], source_prompt)
        self.assertIn(case["current_facts"], facts_prompt)
        self.assertNotIn(case["proposed_answer"], facts_prompt)
        self.assertIn(case["proposed_answer"], answer_prompt)
        self.assertNotIn(case["source_window"], answer_prompt)

    def test_order_audit_is_balanced(self):
        cases = {case["id"]: case for case in self.world["cases"]}
        expected = [cases[case_id]["expected"][link] for case_id, link in RUNNER.ORDER_AUDIT]
        self.assertEqual(expected.count("supported"), 4)
        self.assertEqual(expected.count("not_enough"), 4)

    def test_published_result_matches_locked_inputs(self):
        path = ROOT / "site/experiments/E007/atomic-tool-result-v0.1.json"
        if not path.exists():
            self.skipTest("result not published yet")
        result = json.loads(path.read_text())
        self.assertEqual(result["summary"]["total_cases"], 64)
        self.assertEqual(result["summary"]["total_main_tool_calls"], 192)
        self.assertEqual(len(result["records"]), 64)


if __name__ == "__main__":
    unittest.main()
