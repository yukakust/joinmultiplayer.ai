import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "experiments/E007-harness-mvp/src"
sys.path.insert(0, str(SRC))
SPEC = importlib.util.spec_from_file_location("run_bf16_rocm", SRC / "run_bf16_rocm.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class Bf16RocmTest(unittest.TestCase):
    def test_protocol_is_locked_and_unquantized(self):
        protocol = json.loads(MODULE.PROTOCOL.read_text(encoding="utf-8"))
        self.assertEqual(protocol["status"], "locked_before_inference")
        self.assertEqual(protocol["model"]["source_weight_type"], "BF16")
        self.assertEqual(protocol["model"]["revision"], "b968826d9c46dd6066d109eabc6255188de91218")
        self.assertEqual(protocol["runtime"]["reasoning"], "off")
        self.assertEqual(protocol["runtime"]["kv_cache"], "Q8_0")
        self.assertEqual(protocol["input"]["prompt"], "Exactly the Gate 16B.1 three-question prompt")


if __name__ == "__main__":
    unittest.main()
