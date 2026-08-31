import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / ".." / "site" / "experiments" / "E007" / "two-real-turn-retrieval-v0.1.py"
SPEC = importlib.util.spec_from_file_location("turn_retrieval", SCRIPT.resolve())
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class TurnRetrievalTests(unittest.TestCase):
    def test_last_turn_uses_last_user_with_following_assistant(self):
        rows = [{"role":"user"},{"role":"assistant"},{"role":"user"},{"role":"assistant"},{"role":"assistant"}]
        self.assertEqual(module.last_turn(rows), (2, 3))

    def test_bm25_prefers_matching_document(self):
        scores = module.bm25_scores(["red apple", "blue ocean"], "apple")
        self.assertGreater(scores[0], scores[1])

    def test_codex_metadata_stops_at_prefix_without_tell_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.jsonl"
            path.write_text(
                json.dumps({"type":"session_meta","payload":{"id":"S1"}}) + "\n" +
                json.dumps({"type":"event_msg","payload":{"type":"user_message","message":"hello"}}) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(module.codex_metadata(path), ("S1", False))


if __name__ == "__main__":
    unittest.main()
