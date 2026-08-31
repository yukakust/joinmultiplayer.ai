import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / ".." / "site" / "experiments" / "E007" / "local-conversation-adapters-v0.2.py"
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


if __name__ == "__main__":
    unittest.main()
