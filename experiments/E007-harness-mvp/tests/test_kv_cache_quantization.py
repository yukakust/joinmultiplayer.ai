import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "experiments/E007-harness-mvp/src"
sys.path.insert(0, str(SRC))
SPEC = importlib.util.spec_from_file_location("run_kv_cache_quantization", SRC / "run_kv_cache_quantization.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class KvCacheQuantizationTest(unittest.TestCase):
    def test_protocol_is_locked_and_isolates_cache(self):
        protocol = json.loads(MODULE.PROTOCOL.read_text(encoding="utf-8"))
        self.assertEqual(protocol["status"], "locked_before_inference")
        self.assertEqual([lane["kv_cache"] for lane in protocol["lanes"]], ["Q8_0", "Q4_0"])
        self.assertEqual(protocol["model"]["weight_quantization"], "Q4_K_M")

    def test_prompt_does_not_teach_a_fake_message_id(self):
        prompt = MODULE.build_prompt(MODULE.CASES[0], "[M0042] fact")
        self.assertIn("настоящий номер", prompt)
        self.assertNotIn('"M0001"', prompt)
        self.assertNotIn('"M0123"', prompt)
        self.assertNotIn('"answer":"краткий ответ"', prompt)
        self.assertIn("ровно три поля", prompt)


if __name__ == "__main__":
    unittest.main()
