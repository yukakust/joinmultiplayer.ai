import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CLIENT = ROOT / "site/experiments/E007/topic-index-node-v0.1.py"
CLIENT_V2 = ROOT / "site/experiments/E007/topic-index-node-v0.2.py"
INDEXER = ROOT / "experiments/E007-harness-mvp/src/run_topic_index.py"
PUBLIC_BUILDER = ROOT / "experiments/E007-harness-mvp/src/build_topic_index_public.py"
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

    def test_v2_uses_ui_events_and_ignores_model_input_roles(self):
        client = load(CLIENT_V2, "topic_client_v2")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "s.jsonl"
            rows = [
                {"timestamp": "1", "type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "runtime context"}]}},
                {"timestamp": "2", "type": "event_msg", "payload": {"type": "user_message", "message": "real question"}},
                {"timestamp": "3", "type": "event_msg", "payload": {"type": "agent_message", "message": "visible answer"}},
                {"timestamp": "4", "type": "event_msg", "payload": {"type": "task_complete", "message": "internal"}},
            ]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            messages = client.visible_ui_messages([path])
            self.assertEqual([item["text"] for item in messages], ["real question", "visible answer"])
            self.assertEqual([item["role"] for item in messages], ["user", "assistant"])

    def test_blocks_never_exceed_target_for_normal_units(self):
        indexer = load(INDEXER, "topic_indexer")
        units = [{"tokens": 4000}, {"tokens": 4000}, {"tokens": 4000}]
        self.assertEqual([len(item) for item in indexer.blocks(units)], [2, 1])

    def test_public_result_contains_metrics_but_no_private_topic_text(self):
        builder = load(PUBLIC_BUILDER, "topic_public_builder")
        private = {"cards": [{
            "card_id": "C0001", "qwen_tokens": 900,
            "blocks": 1, "status": "CARD", "errors": [],
            "topics": [{
                "name": "PRIVATE TOPIC", "summary": "PRIVATE SUMMARY",
                "evidence": [{"message_id": "PRIVATE-MESSAGE"}],
            }],
        }]}
        public = builder.build(private, 12)
        encoded = json.dumps(public)
        self.assertEqual(public["result"]["valid_cards"], 1)
        self.assertEqual(public["cards"][0]["topic_count"], 1)
        self.assertNotIn("PRIVATE TOPIC", encoded)
        self.assertNotIn("PRIVATE SUMMARY", encoded)
        self.assertNotIn("PRIVATE-MESSAGE", encoded)


if __name__ == "__main__":
    unittest.main()
