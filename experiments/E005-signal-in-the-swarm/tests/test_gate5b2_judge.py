import importlib.util
import json
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "judge_gate5b2.py"
SPEC = importlib.util.spec_from_file_location("judge_gate5b2", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Gate5B2JudgeTests(unittest.TestCase):
    def test_protocol_has_twelve_bilingual_calibration_cases(self):
        self.assertEqual(len(MODULE.CALIBRATION_CASES), 12)
        self.assertEqual({row["language"] for row in MODULE.CALIBRATION_CASES}, {"en", "ru"})
        self.assertEqual(len({row["case_id"] for row in MODULE.CALIBRATION_CASES}), 12)
        self.assertTrue(all(row["case_id"].startswith("CAL3-") for row in MODULE.CALIBRATION_CASES))
        self.assertTrue(next(row for row in MODULE.CALIBRATION_CASES if row["case_id"] == "CAL3-RU-01")["question"].startswith("Объясните"))
        self.assertTrue(all("phase drift" not in json.dumps(row, ensure_ascii=False).lower() for row in MODULE.CALIBRATION_CASES))

    def test_blind_order_is_stable_and_hides_condition_from_prompt(self):
        rows = [
            {"question_id": "Q2", "language": "en", "condition": "secret-b", "question": "q", "expected_cause": "c", "expected_safety": "s", "answer": "a"},
            {"question_id": "Q1", "language": "ru", "condition": "secret-a", "question": "q", "expected_cause": "c", "expected_safety": "s", "answer": "a"},
        ]
        self.assertEqual(MODULE.blind_order(rows), MODULE.blind_order(list(reversed(rows))))
        prompt = MODULE.render_prompt(rows[0])
        self.assertNotIn("secret-b", prompt)
        self.assertNotIn("Q2", prompt)

    def test_exact_quote_is_required(self):
        answer = "Thermal rebound is present, so keep the auxiliary vent closed."
        valid = {
            "cause": "correct", "cause_quote": "Thermal rebound is present",
            "safe_action": "correct", "safe_action_quote": "keep the auxiliary vent closed",
            "reason": "Both meanings are present.", "confidence": 0.9,
        }
        judged = MODULE.validate_judgment(valid, answer)
        self.assertEqual(judged["overall"], "correct")
        self.assertFalse(judged["contradiction"])
        invalid = dict(valid, cause_quote="retained heat")
        with self.assertRaisesRegex(ValueError, "exact answer substring"):
            MODULE.validate_judgment(invalid, answer)

    def test_negation_derives_incorrect_overall(self):
        value = {
            "cause": "incorrect", "cause_quote": "not thermal rebound",
            "safe_action": "correct", "safe_action_quote": "vent closed",
            "reason": "The cause conflicts.", "confidence": 0.8,
        }
        judged = MODULE.validate_judgment(value, "This is not thermal rebound. Keep the vent closed.")
        self.assertTrue(judged["contradiction"])
        self.assertEqual(judged["overall"], "incorrect")

    def test_structured_retry_preserves_record(self):
        outputs = iter([
            "not json",
            json.dumps({
                "cause": "correct", "cause_quote": "temperature bounced back",
                "safe_action": "absent", "safe_action_quote": None,
                "reason": "Only the cause is present.", "confidence": 0.8,
            }),
        ])
        row = MODULE.CALIBRATION_CASES[1]
        judgment, _, retries = MODULE.judge_one(lambda _system, _prompt: next(outputs), row)
        self.assertEqual(judgment["overall"], "partial")
        self.assertEqual(retries, 1)


if __name__ == "__main__":
    unittest.main()
