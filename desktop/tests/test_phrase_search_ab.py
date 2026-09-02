from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from pocket_i_core import Conversation, HybridChatIndex, Message


SCRIPT = Path(__file__).resolve().parents[2] / "site" / "experiments" / "E007" / "phrase-search-ab-v0.1.py"
SPEC = importlib.util.spec_from_file_location("phrase_search_ab", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PhraseSearchExperimentTests(unittest.TestCase):
    def test_discovers_unseen_phrases_from_the_question_without_a_domain_list(self):
        phrases = MODULE._query_ngrams("Should the ceramic valve remain closed during calibration?")

        self.assertIn(("ceramic", "valve"), phrases)
        self.assertIn(("remain", "closed"), phrases)

    def test_corpus_frequency_keeps_matching_rare_phrases(self):
        conversations = (
            Conversation("noise", "fixture", (Message("n1", "assistant", "Ask the user for permission."),)),
            Conversation(
                "target",
                "fixture",
                (Message("t1", "assistant", "Do not fail-closed on passive room display."),),
            ),
        )
        index = HybridChatIndex(conversations, lambda texts: [[1.0, 0.0] for _ in texts])

        phrases, scores = MODULE.corpus_phrase_scores(
            index,
            "Why should passive room messages not always fail closed?",
        )

        self.assertIn("passive room", phrases)
        self.assertIn("fail closed", phrases)
        self.assertGreater(scores[1], scores[0])


if __name__ == "__main__":
    unittest.main()
