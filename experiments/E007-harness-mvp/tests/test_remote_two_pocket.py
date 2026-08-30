import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CLIENT_PATH = ROOT / "site/experiments/E007/remote-two-pocket-node-v0.1.py"
WORKER_PATH = ROOT / "experiments/E007-harness-mvp/src/run_remote_two_pocket_worker.py"
PROTOCOL_PATH = ROOT / "site/experiments/E007/remote-two-pocket-protocol-v0.1.json"


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class RemoteTwoPocketTest(unittest.TestCase):
    def test_protocol_is_locked_and_has_two_workers(self):
        protocol = json.loads(PROTOCOL_PATH.read_text())
        self.assertEqual(protocol["status"], "locked_before_local_selection_or_model_inference")
        self.assertEqual([item["gpu"] for item in protocol["nodes"]], [0, 1])
        self.assertEqual(protocol["local_library"]["max_conversations_per_node"], 3)

    def test_worker_tool_parser(self):
        worker = module(WORKER_PATH, "remote_worker")
        self.assertEqual(worker.parse_tool('<tool_call>{"name":"send_empty","arguments":{}}</tool_call>')["status"], "EMPTY")
        found = worker.parse_tool('<tool_call>{"name":"send_found","arguments":{"claim":"x","evidence":["M0001"]}}</tool_call>')
        self.assertEqual(found, {"status": "FOUND", "claim": "x", "evidence": ["M0001"]})

    def test_visible_messages_exclude_tools(self):
        client = module(CLIENT_PATH, "remote_client")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "session.jsonl"
            rows = [
                {"type": "response_item", "payload": {"type": "message", "id": "u", "role": "user", "content": [{"type": "input_text", "text": "pocket harness"}]}},
                {"type": "response_item", "payload": {"type": "function_call", "name": "secret"}},
                {"type": "response_item", "payload": {"type": "message", "id": "a", "role": "assistant", "content": [{"type": "output_text", "text": "visible answer"}]}},
            ]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            self.assertEqual([item["text"] for item in client.visible_messages([path])], ["pocket harness", "visible answer"])


if __name__ == "__main__":
    unittest.main()
