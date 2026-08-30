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
WHOLE_CHAT_RUNNER = ROOT / "experiments/E007-harness-mvp/src/run_whole_chat_index.py"
WHOLE_CHAT_PROTOCOL = ROOT / "site/experiments/E007/whole-chat-index-protocol-v0.1.json"
WHOLE_CHAT_PUBLIC_BUILDER = ROOT / "experiments/E007-harness-mvp/src/build_whole_chat_index_public.py"
WHOLE_CHAT_READER_16D3 = ROOT / "experiments/E007-harness-mvp/src/run_whole_chat_reader_gate16d3.py"
WHOLE_CHAT_READER_16D3_PROTOCOL = ROOT / "site/experiments/E007/whole-chat-reader-gate16d3-protocol-v0.1.json"
WHOLE_CHAT_READER_16D3_PUBLIC = ROOT / "experiments/E007-harness-mvp/src/build_whole_chat_reader_gate16d3_public.py"
WHOLE_CHAT_READER_16D5_PROTOCOL = ROOT / "site/experiments/E007/whole-chat-reader-gate16d5-protocol-v0.1.json"
WHOLE_CHAT_READER_16D5_RESULT = ROOT / "site/experiments/E007/whole-chat-reader-gate16d5-result-v0.1.json"
ATOMIC_READER_16D6_PROTOCOL = ROOT / "site/experiments/E007/atomic-reader-gate16d6-protocol-v0.1.json"
ATOMIC_READER_16D6_RESULT = ROOT / "site/experiments/E007/atomic-reader-gate16d6-result-v0.1.json"
FACT_READER_16D7_PROTOCOL = ROOT / "site/experiments/E007/fact-reader-gate16d7-protocol-v0.1.json"
FACT_READER_16D7_RESULT = ROOT / "site/experiments/E007/fact-reader-gate16d7-result-v0.1.json"
SHELF_SYNTHESIS_16D8_PROTOCOL = ROOT / "site/experiments/E007/shelf-synthesis-gate16d8-protocol-v0.1.json"
SHELF_SYNTHESIS_16D8_RESULT = ROOT / "site/experiments/E007/shelf-synthesis-gate16d8-result-v0.1.json"
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

    def test_whole_chat_index_protocol_is_locked_and_has_unique_gold_queries(self):
        protocol = json.loads(WHOLE_CHAT_PROTOCOL.read_text())
        self.assertEqual(protocol["status"], "locked_before_embedding_run")
        self.assertEqual(len(protocol["queries"]), 10)
        self.assertEqual(len({item["id"] for item in protocol["queries"]}), 10)
        self.assertEqual(len({item["gold_card_id"] for item in protocol["queries"]}), 10)
        self.assertEqual(protocol["success_gate"]["recall_at_5"], "10/10")

    def test_cosine_prefers_identical_vector(self):
        runner = load(WHOLE_CHAT_RUNNER, "whole_chat_runner")
        class Vector:
            def __init__(self, values): self.values = values
            def __matmul__(self, other): return sum(a * b for a, b in zip(self.values, other.values))
        query = Vector([1.0, 0.0])
        self.assertGreater(runner.cosine(query, query), runner.cosine(query, Vector([0.0, 1.0])))

    def test_whole_chat_public_builder_drops_matched_message_coordinates(self):
        builder = load(WHOLE_CHAT_PUBLIC_BUILDER, "whole_chat_public_builder")
        private = {
            "experiment": "E007", "gate": "16D.2", "status": "FAIL",
            "model": "m", "fastembed": "0.8.0", "conversations": 1,
            "indexed_messages": 1, "runtime_seconds": 1, "summary": {},
            "claim_boundary": "retrieval only", "queries": [{
                "id": "Q", "question": "safe", "gold_card_id": "C",
                "gold_rank": 1, "top_5": [{
                    "card_id": "C", "message_id": "PRIVATE-COORDINATE", "score": 1.0,
                }],
            }],
        }
        public = builder.build(private)
        self.assertNotIn("PRIVATE-COORDINATE", json.dumps(public))

    def test_gate16d3_reader_protocol_has_balanced_locked_cases(self):
        protocol = json.loads(WHOLE_CHAT_READER_16D3_PROTOCOL.read_text())
        self.assertEqual(protocol["status"], "locked_before_qwen_run")
        self.assertEqual(sum(item["kind"] == "positive" for item in protocol["cases"]), 8)
        self.assertEqual(sum(item["kind"] == "negative" for item in protocol["cases"]), 8)
        self.assertEqual(len({item["id"] for item in protocol["cases"]}), 16)

    def test_gate16d3_reader_parses_exactly_one_tool(self):
        reader = load(WHOLE_CHAT_READER_16D3, "whole_chat_reader_16d3")
        name, arguments = reader.parse_call('<tool_call>{"name":"send_empty","arguments":{}}</tool_call>')
        self.assertEqual(name, "send_empty")
        self.assertEqual(arguments, {})
        with self.assertRaises(ValueError):
            reader.parse_call("no call")

    def test_gate16d3_public_builder_drops_raw_model_output(self):
        builder = load(WHOLE_CHAT_READER_16D3_PUBLIC, "whole_chat_reader_16d3_public")
        private = {
            "model": "m", "revision": "r", "rows": [{
                "id": case_id, "kind": "positive" if case_id.startswith("P") else "negative",
                "query_id": "Q", "card_id": "C", "receipt": "EMPTY",
                "claim": None, "evidence_message_ids": [], "input_tokens": 1,
                "runtime_seconds": 1, "raw": "PRIVATE RAW OUTPUT",
            } for case_id in builder.REVIEWS]
        }
        public = builder.build(private, {"queries": [{"id": "Q", "question": "safe"}]})
        self.assertNotIn("PRIVATE RAW OUTPUT", json.dumps(public))

    def test_gate16d5_has_ten_locked_questions_and_twenty_safe_rows(self):
        protocol = json.loads(WHOLE_CHAT_READER_16D5_PROTOCOL.read_text())
        result = json.loads(WHOLE_CHAT_READER_16D5_RESULT.read_text())
        self.assertEqual(len(protocol["questions"]), 10)
        self.assertEqual(len(protocol["negative_pairing"]), 10)
        self.assertEqual(len(result["rows"]), 20)
        self.assertEqual(result["summary"]["valid_receipts"], 20)
        public_text = WHOLE_CHAT_READER_16D5_RESULT.read_text()
        self.assertNotIn("raw_message", public_text)
        self.assertNotIn('"usage"', public_text)

    def test_gate16d6_preserves_failed_atomic_result_without_private_output(self):
        protocol = json.loads(ATOMIC_READER_16D6_PROTOCOL.read_text())
        result = json.loads(ATOMIC_READER_16D6_RESULT.read_text())
        self.assertEqual(len(protocol["questions"]), 10)
        self.assertEqual(sum(len(item["atoms"]) for item in protocol["questions"]), 20)
        self.assertEqual(len(result["questions"]), 10)
        self.assertEqual(result["summary"]["atom_meanings_preserved"], 14)
        self.assertEqual(result["summary"]["complete_answers"], 5)
        self.assertFalse(result["summary"]["gate_passed"])
        public_text = ATOMIC_READER_16D6_RESULT.read_text()
        self.assertNotIn("raw_message", public_text)
        self.assertNotIn('"usage"', public_text)

    def test_gate16d7_has_one_fact_calls_and_preserves_failed_result(self):
        protocol = json.loads(FACT_READER_16D7_PROTOCOL.read_text())
        result = json.loads(FACT_READER_16D7_RESULT.read_text())
        self.assertEqual(len(protocol["questions"]), 5)
        self.assertEqual(sum(len(item["facts"]) for item in protocol["questions"]), 25)
        self.assertEqual(result["summary"]["correct_message"], 21)
        self.assertEqual(result["summary"]["fact_meanings_preserved"], 17)
        self.assertEqual(result["summary"]["complete_hard_questions"], 2)
        self.assertFalse(result["summary"]["gate_passed"])
        public_text = FACT_READER_16D7_RESULT.read_text()
        self.assertNotIn("raw_message", public_text)
        self.assertNotIn('"usage"', public_text)

    def test_gate16d8_separates_completeness_from_grounding(self):
        protocol = json.loads(SHELF_SYNTHESIS_16D8_PROTOCOL.read_text())
        result = json.loads(SHELF_SYNTHESIS_16D8_RESULT.read_text())
        self.assertEqual(len(protocol["questions"]), 5)
        self.assertEqual(len(result["rows"]), 10)
        self.assertEqual(result["summary"]["retrieved_shelf_complete"], 4)
        self.assertEqual(result["summary"]["oracle_shelf_complete"], 5)
        self.assertEqual(result["summary"]["grounded_answers"], 7)
        self.assertTrue(result["summary"]["completeness_gate_passed"])
        self.assertFalse(result["summary"]["overall_gate_passed"])
        public_text = SHELF_SYNTHESIS_16D8_RESULT.read_text()
        self.assertNotIn("raw_message", public_text)
        self.assertNotIn('"usage"', public_text)
        self.assertNotIn("/home/", public_text)


if __name__ == "__main__":
    unittest.main()
