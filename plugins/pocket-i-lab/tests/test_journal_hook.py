from __future__ import annotations

import importlib.util
import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "journal_hook.py"
SPEC = importlib.util.spec_from_file_location("journal_hook", MODULE_PATH)
assert SPEC and SPEC.loader
journal_hook = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(journal_hook)


class JournalHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = journal_hook.JournalState(Path(self.temp.name) / "journal.sqlite3")
        self.calls = []

    def tearDown(self):
        self.state.db.close()
        self.temp.cleanup()

    def fake_post(self, site, path, value, timeout=8.0):
        self.calls.append((path, value))
        if path == "/api/experiment-runs":
            return {
                "id": "R0042",
                "token": "private-run-token",
                "public_path": "/experiment/run/?id=R0042",
            }
        return {"ok": True}

    def start(self):
        data = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session-a",
            "turn_id": "turn-1",
            "cwd": self.temp.name,
            "prompt": "$pocket-i-lab start E002 as Morrow",
        }
        with patch.object(journal_hook, "post_json", side_effect=self.fake_post):
            context = journal_hook.handle(data, self.state, "https://example.test")
        self.assertIn("R0042", context)

    def test_inactive_hook_does_nothing(self):
        with patch.object(journal_hook, "post_json", side_effect=self.fake_post):
            result = journal_hook.handle(
                {
                    "hook_event_name": "Stop",
                    "session_id": "private-session",
                    "turn_id": "turn-private",
                    "last_assistant_message": "private answer",
                },
                self.state,
                "https://example.test",
            )
        self.assertEqual(result, "")
        self.assertEqual(self.calls, [])

    def test_start_is_explicit_and_token_stays_local(self):
        self.start()
        session = self.state.active("session-a")
        self.assertIsNotNone(session)
        self.assertEqual(session["token"], "private-run-token")
        events = [value for path, value in self.calls if path.endswith("/events")]
        self.assertTrue(all("token" not in event["payload"] for event in events))
        self.assertEqual([event["event_type"] for event in events], ["run_started", "user_message"])
        mode = stat.S_IMODE((Path(self.temp.name) / "journal.sqlite3").stat().st_mode)
        self.assertEqual(mode, 0o600)

    def test_prompt_and_answer_are_redacted(self):
        self.start()
        self.calls.clear()
        with patch.object(journal_hook, "post_json", side_effect=self.fake_post):
            journal_hook.handle(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "session-a",
                    "turn_id": "turn-2",
                    "prompt": "read /home/alice/private.txt api_key=supersecret123",
                },
                self.state,
                "https://example.test",
            )
            journal_hook.handle(
                {
                    "hook_event_name": "Stop",
                    "session_id": "session-a",
                    "turn_id": "turn-2",
                    "last_assistant_message": "Done from /Users/alice/work with sk-abcdefghijklmnop",
                },
                self.state,
                "https://example.test",
            )
        payloads = json.dumps(self.calls, ensure_ascii=False)
        self.assertNotIn("supersecret123", payloads)
        self.assertNotIn("/home/alice", payloads)
        self.assertNotIn("/Users/alice", payloads)
        self.assertNotIn("sk-abcdefghijklmnop", payloads)
        self.assertIn("<redacted-secret>", payloads)

    def test_post_tool_never_publishes_output_or_patch_body(self):
        self.start()
        self.calls.clear()
        with patch.object(journal_hook, "post_json", side_effect=self.fake_post):
            journal_hook.handle(
                {
                    "hook_event_name": "PostToolUse",
                    "session_id": "session-a",
                    "turn_id": "turn-2",
                    "tool_use_id": "tool-1",
                    "tool_name": "apply_patch",
                    "cwd": self.temp.name,
                    "tool_input": {
                        "command": "*** Begin Patch\n*** Update File: docs/result.md\n+SECRET BODY\n*** End Patch"
                    },
                    "tool_response": {"output": "PRIVATE TOOL OUTPUT"},
                },
                self.state,
                "https://example.test",
            )
        payloads = json.dumps(self.calls, ensure_ascii=False)
        self.assertIn("docs/result.md", payloads)
        self.assertNotIn("SECRET BODY", payloads)
        self.assertNotIn("PRIVATE TOOL OUTPUT", payloads)

    def test_finish_closes_only_current_session(self):
        self.start()
        self.calls.clear()
        with patch.object(journal_hook, "post_json", side_effect=self.fake_post):
            context = journal_hook.handle(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "session-a",
                    "turn_id": "turn-3",
                    "prompt": "$pocket-i-lab finish",
                },
                self.state,
                "https://example.test",
            )
        self.assertIn("completed", context)
        self.assertIsNone(self.state.active("session-a"))
        events = [value["event_type"] for path, value in self.calls if path.endswith("/events")]
        self.assertEqual(events, ["user_message", "run_completed"])


if __name__ == "__main__":
    unittest.main()
