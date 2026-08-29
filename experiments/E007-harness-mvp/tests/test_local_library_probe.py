import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROBE_PATH = ROOT / "site" / "experiments" / "E007" / "local-library-probe-v0.1.py"
SPEC = importlib.util.spec_from_file_location("local_library_probe", PROBE_PATH)
PROBE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROBE
SPEC.loader.exec_module(PROBE)


class LocalLibraryProbeTests(unittest.TestCase):
    def test_finds_only_three_named_app_libraries_without_reading_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            codex = home / ".codex" / "sessions"
            claude = home / ".claude" / "projects" / "demo"
            chatgpt = home / "Library" / "Application Support" / "ChatGPT"
            unrelated = home / "Documents" / "private"
            for directory in (codex, claude, chatgpt, unrelated):
                directory.mkdir(parents=True)
            secret = "THIS CONVERSATION MUST NEVER APPEAR IN THE REPORT"
            (codex / "one.jsonl").write_text(secret, encoding="utf-8")
            (claude / "two.jsonl").write_text(secret, encoding="utf-8")
            (chatgpt / "three.sqlite").write_text(secret, encoding="utf-8")
            (unrelated / "four.jsonl").write_text(secret, encoding="utf-8")

            report = PROBE.run_probe(home, "Darwin", {}, include_files=True)
            rendered = str(report)
            by_source = {item["source"]: item for item in report["sources"]}

            self.assertEqual(by_source["codex"]["candidate_files"], 1)
            self.assertEqual(by_source["claude_code"]["candidate_files"], 1)
            self.assertEqual(by_source["chatgpt_desktop"]["candidate_files"], 1)
            self.assertNotIn(secret, rendered)
            self.assertNotIn("Documents/private", rendered)
            self.assertFalse(report["privacy"]["conversation_text_emitted"])
            self.assertEqual(report["privacy"]["network_calls"], 0)
            self.assertEqual(report["segmentation_decision"], "not_started")

    def test_probe_does_not_modify_candidate_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            session = home / ".codex" / "sessions" / "one.jsonl"
            session.parent.mkdir(parents=True)
            session.write_bytes(b"unchanged")
            before = (session.read_bytes(), session.stat().st_mtime_ns)
            PROBE.run_probe(home, "Linux", {}, include_files=False)
            after = (session.read_bytes(), session.stat().st_mtime_ns)
            self.assertEqual(before, after)

    def test_missing_apps_are_reported_without_guessing(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = PROBE.run_probe(Path(temporary), "Darwin", {}, include_files=False)
            self.assertEqual({item["status"] for item in report["sources"]}, {"not_found"})


if __name__ == "__main__":
    unittest.main()
