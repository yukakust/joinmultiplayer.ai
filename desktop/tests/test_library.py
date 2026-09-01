from __future__ import annotations

import json
import tempfile
import unittest
import zlib
from pathlib import Path

from pocket_i_core import count_local_conversations, scan_local_library


class LocalLibraryTests(unittest.TestCase):
    def test_count_only_inventory_reads_metadata_for_codex_and_claude(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex = home / ".codex" / "sessions"
            codex.mkdir(parents=True)
            (codex / "main.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"type": "session_meta", "payload": {"id": "main"}}),
                        "THIS MESSAGE BODY IS DELIBERATELY NOT JSON",
                    ]
                ),
                encoding="utf-8",
            )
            (codex / "child.jsonl").write_text(
                json.dumps({"type": "session_meta", "payload": {"id": "child", "parent_thread_id": "main"}}),
                encoding="utf-8",
            )
            claude = home / ".claude" / "projects" / "project"
            claude.mkdir(parents=True)
            (claude / "one.jsonl").write_text(
                json.dumps({"type": "user", "sessionId": "claude-one", "message": {"content": "PRIVATE"}}),
                encoding="utf-8",
            )

            counts = count_local_conversations(home=home)

            self.assertEqual(2, counts.total_conversations)
            self.assertEqual(
                {"codex": 1, "claude_code": 1},
                {item.source: item.conversations for item in counts.adapters},
            )

    def test_codex_keeps_only_visible_main_session_messages(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home / ".codex" / "sessions"
            root.mkdir(parents=True)
            main = [
                {"type": "session_meta", "payload": {"id": "main"}},
                {"type": "event_msg", "timestamp": "1", "payload": {"type": "user_message", "message": "Question"}},
                {"type": "response_item", "payload": {"type": "reasoning", "text": "hidden"}},
                {"type": "event_msg", "timestamp": "2", "payload": {"type": "agent_message", "message": "Answer"}},
                {"type": "event_msg", "timestamp": "3", "payload": {"type": "tool_output", "message": "secret output"}},
            ]
            child = [
                {"type": "session_meta", "payload": {"id": "child", "parent_thread_id": "main"}},
                {"type": "event_msg", "timestamp": "4", "payload": {"type": "agent_message", "message": "subagent text"}},
            ]
            (root / "main.jsonl").write_text("\n".join(json.dumps(item) for item in main), encoding="utf-8")
            (root / "child.jsonl").write_text("\n".join(json.dumps(item) for item in child), encoding="utf-8")

            library = scan_local_library(home=home, sources=("codex",))

            self.assertEqual(1, len(library.conversations))
            self.assertEqual(["Question", "Answer"], [item.text for item in library.conversations[0].messages])

    def test_claude_keeps_text_and_drops_thinking_tools_and_meta(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home / ".claude" / "projects" / "project"
            root.mkdir(parents=True)
            rows = [
                {"type": "user", "sessionId": "s1", "uuid": "u1", "message": {"role": "user", "content": "Question"}},
                {"type": "assistant", "sessionId": "s1", "uuid": "a1", "message": {"role": "assistant", "content": [
                    {"type": "thinking", "thinking": "hidden"},
                    {"type": "text", "text": "Answer"},
                    {"type": "tool_use", "input": {"command": "secret"}},
                ]}},
                {"type": "user", "sessionId": "s1", "uuid": "u2", "message": {"role": "user", "content": [{"type": "tool_result", "content": "secret result"}]}},
                {"type": "user", "sessionId": "s1", "uuid": "u3", "isMeta": True, "message": {"role": "user", "content": "meta"}},
            ]
            (root / "s1.jsonl").write_text("\n".join(json.dumps(item) for item in rows), encoding="utf-8")

            library = scan_local_library(home=home, sources=("claude_code",))

            self.assertEqual(["Question", "Answer"], [item.text for item in library.conversations[0].messages])

    def test_chatgpt_reads_known_local_json_container_and_fails_closed_on_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home / "Library" / "Application Support" / "com.openai.chat"
            root.mkdir(parents=True)
            mapping = {
                "1": {"message": {"create_time": 1, "author": {"role": "user"}, "content": {"content_type": "text", "parts": ["Question"]}}},
                "2": {"message": {"create_time": 2, "author": {"role": "assistant"}, "content": {"content_type": "text", "parts": ["Answer"]}}},
                "3": {"message": {"create_time": 3, "author": {"role": "tool"}, "content": {"content_type": "text", "parts": ["hidden"]}}},
            }
            (root / "conversations.json").write_bytes(zlib.compress(json.dumps([{"id": "g1", "mapping": mapping}]).encode()))
            unsupported = root / "conversations-v3-unknown"
            unsupported.mkdir()
            (unsupported / "one.data").write_bytes(b"unknown binary")

            library = scan_local_library(home=home, sources=("chatgpt_desktop",), environ={})

            self.assertEqual(["Question", "Answer"], [item.text for item in library.conversations[0].messages])
            self.assertEqual(1, library.adapters[0].unsupported_files)

    def test_public_summary_contains_no_text_paths_or_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home / ".codex" / "sessions"
            root.mkdir(parents=True)
            secret = "PRIVATE-TEXT-AND-ID"
            rows = [
                {"type": "session_meta", "payload": {"id": secret}},
                {"type": "event_msg", "timestamp": "1", "payload": {"type": "user_message", "message": secret}},
            ]
            (root / "private-name.jsonl").write_text("\n".join(json.dumps(item) for item in rows), encoding="utf-8")

            summary = scan_local_library(home=home, sources=("codex",)).public_summary()
            rendered = json.dumps(summary)

            self.assertNotIn(secret, rendered)
            self.assertNotIn(str(home), rendered)
            self.assertNotIn("private-name", rendered)
            self.assertEqual(1, summary["total_messages"])


if __name__ == "__main__":
    unittest.main()
