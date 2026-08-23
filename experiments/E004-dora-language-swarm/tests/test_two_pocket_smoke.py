import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "two_pocket_dora_smoke.py"
SPEC = importlib.util.spec_from_file_location("two_pocket_dora_smoke", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TwoPocketSmokeTests(unittest.TestCase):
    def test_books_are_disjoint_and_nonbinary(self):
        first = set(MODULE.POCKETS["I01"].values())
        second = set(MODULE.POCKETS["I02"].values())
        self.assertTrue(first.isdisjoint(second))
        self.assertEqual(len(first | second), 6)
        self.assertTrue(all(len(value) >= 4 for value in first | second))

    def test_normalization_finds_generated_code(self):
        self.assertEqual(MODULE.normalize_answer("VEKU"), "VEKU")
        self.assertEqual(MODULE.normalize_answer(" VEKU\nextra"), "VEKU")


if __name__ == "__main__":
    unittest.main()
