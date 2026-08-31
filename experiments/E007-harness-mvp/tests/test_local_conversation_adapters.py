import importlib.util
import json
import tempfile
import unittest
import zlib
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / ".." / "site" / "experiments" / "E007" / "local-conversation-adapters-v0.5.py"
SPEC = importlib.util.spec_from_file_location("adapters", SCRIPT.resolve())
adapters = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapters)


class AdapterTests(unittest.TestCase):
    def test_claude_keeps_only_visible_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "projects" / "project"
            root.mkdir(parents=True)
            rows = [
                {"type":"user","sessionId":"s1","uuid":"u1","message":{"role":"user","content":"Human question"}},
                {"type":"assistant","sessionId":"s1","uuid":"a1","message":{"role":"assistant","content":[{"type":"thinking","thinking":"hidden"},{"type":"text","text":"Visible answer"},{"type":"tool_use","name":"Bash","input":{"command":"secret"}}]}},
                {"type":"user","sessionId":"s1","uuid":"u2","message":{"role":"user","content":[{"type":"tool_result","content":"terminal secret"}]}},
                {"type":"user","sessionId":"s1","uuid":"u3","isMeta":True,"message":{"role":"user","content":"system reminder"}},
            ]
            (root / "s1.jsonl").write_text("\n".join(json.dumps(row) for row in rows))
            result = adapters.extract_claude(Path(directory) / "projects")
            self.assertEqual([m["text"] for m in result[0]["messages"]], ["Human question", "Visible answer"])

    def test_chatgpt_keeps_only_user_and_assistant_text_parts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "conversations-cache.json"
            data = [{"id":"c1","mapping":{
                "1":{"id":"1","message":{"id":"m1","create_time":1,"author":{"role":"system"},"content":{"content_type":"text","parts":["hidden"]}}},
                "2":{"id":"2","message":{"id":"m2","create_time":2,"author":{"role":"user"},"content":{"content_type":"text","parts":["Human question"]}}},
                "3":{"id":"3","message":{"id":"m3","create_time":3,"author":{"role":"assistant"},"content":{"content_type":"text","parts":["Visible answer"]}}},
                "4":{"id":"4","message":{"id":"m4","create_time":4,"author":{"role":"tool"},"content":{"content_type":"text","parts":["tool output"]}}}
            }}]
            path.write_text(json.dumps(data))
            result = adapters.extract_chatgpt_file(path)
            self.assertEqual([m["text"] for m in result[0]["messages"]], ["Human question", "Visible answer"])

    def test_chatgpt_shape_probe_never_emits_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "Library" / "Application Support" / "com.openai.chat" / "conversations-v3-test"
            root.mkdir(parents=True)
            secret_text = "PRIVATE-CONVERSATION-TEXT"
            (root / "one.data").write_text(json.dumps({"conversation":{"messages":[{"role":"user","text":secret_text}]}}))
            result = adapters.chatgpt_container_shapes(Path(directory))
            self.assertEqual(result["files_scanned"], 1)
            self.assertNotIn(secret_text, json.dumps(result))

    def test_minimal_sample_reads_one_file_and_twenty_messages_per_source(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            claude = home / ".claude" / "projects" / "project"
            claude.mkdir(parents=True)
            claude_rows = [
                {"type":"user" if index % 2 else "assistant", "sessionId":"s1", "uuid":f"c{index}", "message":{"role":"user" if index % 2 else "assistant", "content":f"claude visible {index}"}}
                for index in range(1, 26)
            ]
            claude_rows.append({"type":"assistant","sessionId":"s1","uuid":"tool","message":{"role":"assistant","content":[{"type":"tool_use","input":"hidden"}]}})
            (claude / "s1.jsonl").write_text("\n".join(json.dumps(row) for row in claude_rows))
            chatgpt = home / "Library" / "Application Support" / "com.openai.chat" / "conversations-v3-test"
            chatgpt.mkdir(parents=True)
            mapping = {
                str(index): {"id":str(index),"message":{"id":f"g{index}","create_time":index,"author":{"role":"user" if index % 2 else "assistant"},"content":{"content_type":"text","parts":[f"chatgpt visible {index}"]}}}
                for index in range(1, 26)
            }
            (chatgpt / "one.data").write_text(json.dumps({"id":"g1","mapping":mapping}))
            private, public = adapters.minimal_sample(home)
            self.assertEqual(public["total_source_files_read"], 2)
            self.assertEqual([item["visible_messages"] for item in public["sources"].values()], [20, 20])
            self.assertEqual([len(item["messages"]) for item in private["sources"]], [20, 20])
            self.assertNotIn("hidden", json.dumps(private))

    def test_single_chatgpt_decoder_handles_zlib_json_without_printing_text(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home / "Library" / "Application Support" / "com.openai.chat" / "conversations-v3-test"
            root.mkdir(parents=True)
            mapping = {"1":{"id":"1","message":{"id":"m1","create_time":1,"author":{"role":"user"},"content":{"content_type":"text","parts":["private sample"]}}}}
            (root / "one.data").write_bytes(zlib.compress(json.dumps({"id":"c1","mapping":mapping}).encode()))
            private, public = adapters.single_chatgpt_decode(home)
            self.assertEqual(public["decoder"], "zlib_json")
            self.assertEqual(public["visible_messages"], 1)
            self.assertNotIn("private sample", json.dumps(public))
            self.assertIn("private sample", json.dumps(private))


if __name__ == "__main__":
    unittest.main()
