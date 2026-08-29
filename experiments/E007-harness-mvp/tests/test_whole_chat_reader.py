import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src/run_whole_chat_reader.py"
SPEC = importlib.util.spec_from_file_location("whole_chat_reader", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WholeChatReaderTest(unittest.TestCase):
    def test_automatic_blocks_are_not_user_memory(self):
        self.assertTrue(MODULE.is_automatic_user_block("<recommended_plugins>\nsecret"))
        self.assertTrue(MODULE.is_automatic_user_block("  <environment_context>x"))
        self.assertFalse(MODULE.is_automatic_user_block("обычное сообщение"))

    def test_visible_messages_accept_only_visible_text(self):
        records = [
            {"type": "response_item", "payload": {"id": "u1", "type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]}},
            {"type": "response_item", "payload": {"id": "a1", "type": "message", "role": "assistant", "phase": "commentary", "content": [{"type": "output_text", "text": "visible"}]}},
            {"type": "response_item", "payload": {"id": "r1", "type": "reasoning", "role": "assistant", "content": [{"type": "output_text", "text": "hidden"}]}},
            {"type": "response_item", "payload": {"id": "p1", "type": "message", "role": "user", "content": [{"type": "input_text", "text": "<recommended_plugins>noise"}]}},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.jsonl"
            path.write_text("\n".join(__import__("json").dumps(item) for item in records), encoding="utf-8")
            messages = MODULE.visible_messages([path])
        self.assertEqual([item["text"] for item in messages], ["hello", "visible"])

    def test_prompt_has_no_location_hint(self):
        rendered = MODULE.prompt(MODULE.CASES[0], "[M0001] example")
        self.assertIn("[M0001] example", rendered)
        self.assertNotIn("gold", rendered)
        self.assertNotIn(MODULE.CASES[0]["questions"][0]["gold"], rendered)


if __name__ == "__main__":
    unittest.main()
