from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from pocket_i_core import Conversation, HybridChatIndex, Message


SCRIPT = Path(__file__).resolve().parents[2] / "site" / "experiments" / "E007" / "anchor-search-ab-v0.1.py"
SPEC = importlib.util.spec_from_file_location("anchor_search_ab", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AnchorSearchExperimentTests(unittest.TestCase):
    def test_preserves_routes_models_and_numbers_as_exact_anchors(self):
        anchors = set(MODULE.technical_anchors("Use /x with DeBERTa-v3, Qwen3-8B and limit 499."))

        self.assertTrue({"/x", "deberta-v3", "qwen3-8b", "499"}.issubset(anchors))
        self.assertNotIn("x", anchors)

    def test_exact_route_anchor_can_raise_the_matching_conversation(self):
        conversations = (
            Conversation("noise", "fixture", (Message("n1", "assistant", "A deployed share feature in unrelated code."),)),
            Conversation("target", "fixture", (Message("t1", "assistant", "The /x route was absent from the Caddy allowlist."),)),
        )

        def embed(texts):
            return [[1.0, 0.0] if "share" in text.casefold() else [0.0, 1.0] for text in texts]

        index = HybridChatIndex(conversations, embed)
        route, anchors, _scores = MODULE.candidate_route(index, "Why was the /x share feature unreachable?", top_k=2)

        self.assertIn("/x", anchors)
        self.assertEqual("target", route[0])


if __name__ == "__main__":
    unittest.main()
