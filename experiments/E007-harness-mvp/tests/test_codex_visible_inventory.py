import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "experiments/E007-harness-mvp/src/inventory_codex_visible.py"
SPEC = importlib.util.spec_from_file_location("inventory_codex_visible", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_session(path, session_id, messages, parent=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [{"type": "session_meta", "payload": {"id": session_id, "parent_thread_id": parent}}]
    records.extend(messages)
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def message(identifier, role, text, phase=None):
    kind = "input_text" if role == "user" else "output_text"
    return {"type": "response_item", "payload": {"id": identifier, "type": "message", "role": role, "phase": phase, "content": [{"type": kind, "text": text}]}}


class CodexVisibleInventoryTests(unittest.TestCase):
    def test_deduplicates_visible_messages_and_ignores_tools(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shared = message("m1", "user", "one two")
            write_session(root / "a.jsonl", "root", [shared, message("m2", "assistant", "three", "commentary")])
            write_session(root / "b.jsonl", "root", [shared, {"type": "response_item", "payload": {"type": "function_call_output", "output": "secret"}}])
            write_session(root / "c.jsonl", "child", [message("m3", "assistant", "four five", "final_answer")], parent="root")

            result = MODULE.build_inventory(list(root.glob("*.jsonl")), lambda text: len(text.split()))

            self.assertEqual(result["unique_conversations"], 2)
            self.assertEqual(result["main_conversations"], 1)
            self.assertEqual(result["child_agent_conversations"], 1)
            self.assertEqual(result["duplicate_message_records_removed"], 1)
            self.assertEqual(result["visible_totals_after_dedup"]["messages"], 3)
            self.assertEqual(result["visible_totals_after_dedup"]["tokens"], 5)
            self.assertEqual(result["message_id_conflicts"], 0)


if __name__ == "__main__":
    unittest.main()
