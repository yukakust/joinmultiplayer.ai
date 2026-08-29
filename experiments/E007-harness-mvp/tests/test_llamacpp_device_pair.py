import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "experiments/E007-harness-mvp/src"
sys.path.insert(0, str(SRC))
SPEC = importlib.util.spec_from_file_location("run_llamacpp_device_pair", SRC / "run_llamacpp_device_pair.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class LlamaCppDevicePairTest(unittest.TestCase):
    def test_protocol_locks_one_file_and_two_devices(self):
        protocol = json.loads(MODULE.PROTOCOL.read_text(encoding="utf-8"))
        self.assertEqual(protocol["status"], "locked_before_inference")
        self.assertEqual(protocol["model"]["gguf_weight_type"], "BF16")
        self.assertEqual(protocol["constant"]["questions"], 6)
        self.assertEqual([lane["id"] for lane in protocol["lanes"]], ["llamacpp_cpu", "llamacpp_rocm"])


if __name__ == "__main__":
    unittest.main()
