from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "site/app.js"


class Gate4CUITests(unittest.TestCase):
    def test_gate4c_pages_use_the_real_global_language_name(self):
        source = APP.read_text(encoding="utf-8")
        gate4c = source[source.index("function e005Gate4LessonsShell"):source.index("function e005MethodName")]
        gate4c += source[source.index("async function loadE005Gate4Lessons"):source.index("async function loadE005()")]
        self.assertNotRegex(gate4c, r"\[lang\]|===\s+lang(?!uage)|toLocaleString\(lang\)")


if __name__ == "__main__":
    unittest.main()
