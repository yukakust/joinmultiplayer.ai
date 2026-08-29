import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).parents[1] / "src/run_kv_cache_reuse.py"
SPEC = importlib.util.spec_from_file_location("kv_cache_reuse", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class KVCacheReuseTest(unittest.TestCase):
    def test_common_prefix(self):
        self.assertEqual(MODULE.common_prefix([[1, 2, 3], [1, 2, 4]]), [1, 2])

    def test_questions_are_different(self):
        self.assertEqual(len(MODULE.QUESTIONS), 2)
        self.assertNotEqual(MODULE.QUESTIONS[0]["question"], MODULE.QUESTIONS[1]["question"])

    def test_cache_size_formula_for_qwen8b(self):
        tokens = 10_000
        expected = tokens * 36 * 8 * 128 * 2 * 2
        self.assertEqual(expected, 1_474_560_000)


if __name__ == "__main__":
    unittest.main()
