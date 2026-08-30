import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CLIENT = ROOT / "site/experiments/E007/topic-index-node-v0.1.py"
INDEXER = ROOT / "experiments/E007-harness-mvp/src/run_topic_index.py"
PROTOCOL = ROOT / "site/experiments/E007/topic-index-protocol-v0.1.json"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TopicIndexTest(unittest.TestCase):
    def test_protocol_has_no_semantic_prefilter(self):
        protocol = json.loads(PROTOCOL.read_text())
        self.assertEqual(protocol["status"], "locked_before_topic_extraction")
        self.assertFalse(protocol["library_contract"]["semantic_prefilter_before_indexing"])
        self.assertEqual(protocol["indexing"]["short_conversation_threshold_qwen_tokens"], 10000)

    def test_client_keeps_visible_messages_only(self):
        client = load(CLIENT, "topic_client")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "s.jsonl"
            rows = [
                {"type": "response_item", "payload": {"type": "message", "role": "user", "id": "u", "content": [{"type": "input_text", "text": "question"}]}},
                {"type": "response_item", "payload": {"type": "reasoning", "content": [{"text": "hidden"}]}},
                {"type": "response_item", "payload": {"type": "message", "role": "assistant", "id": "a", "content": [{"type": "output_text", "text": "answer"}]}},
            ]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            self.assertEqual([item["text"] for item in client.visible_messages([path])], ["question", "answer"])

    def test_blocks_never_exceed_target_for_normal_units(self):
        indexer = load(INDEXER, "topic_indexer")
        units = [{"tokens": 4000}, {"tokens": 4000}, {"tokens": 4000}]
        self.assertEqual([len(item) for item in indexer.blocks(units)], [2, 1])


if __name__ == "__main__":
    unittest.main()
