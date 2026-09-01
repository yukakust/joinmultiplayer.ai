from __future__ import annotations

import json
import unittest

from pocket_i_core import Conversation, HarnessModules, HybridChatIndex, Message, PocketICore, ShelfPlan


def chat(identifier: str, *texts: str) -> Conversation:
    return Conversation(identifier, "fixture", tuple(Message(f"{identifier}:{index}", "assistant", text) for index, text in enumerate(texts, 1)))


class KeywordEmbedder:
    def __init__(self, vocabulary):
        self.vocabulary = tuple(vocabulary)

    def __call__(self, texts):
        return [[float(word in text.casefold()) for word in self.vocabulary] for text in texts]


class HybridRetrievalTests(unittest.TestCase):
    def test_lexical_and_neural_results_are_fused_into_top_k(self):
        conversations = [
            chat("packaging", "Tauri creates desktop packages for three systems."),
            chat("windows", "An installer for a PC."),
            chat("bees", "A hive can prepare a queen cell."),
        ]
        index = HybridChatIndex(conversations, KeywordEmbedder(("desktop", "installer", "hive")))

        result = index.route("How is the desktop installer packaged?", top_k=2)

        self.assertEqual("packaging", result.conversation_ids[0])
        self.assertEqual(2, len(result.conversation_ids))

    def test_best_message_routes_the_whole_conversation(self):
        conversations = [
            chat("long", "unrelated opening", "The source anchor uses an exact quote.", "unrelated ending"),
            chat("other", "A different subject."),
        ]
        index = HybridChatIndex(conversations, KeywordEmbedder(("anchor", "different")))

        result = index.route("How does the source anchor work?", top_k=1)

        self.assertEqual(("long",), result.conversation_ids)

    def test_route_hit_points_to_the_matching_message_inside_the_chat(self):
        conversations = [
            chat("long", "unrelated opening", "The source anchor uses an exact quote.", "unrelated ending"),
            chat("other", "A different subject."),
        ]
        index = HybridChatIndex(conversations, KeywordEmbedder(("anchor", "different")))

        result, hits = index.route_with_hits("How does the source anchor work?", top_k=2)

        self.assertEqual("long", result.conversation_ids[0])
        self.assertEqual(("long", 1), (hits[0].conversation_id, hits[0].message_position))

    def test_context_keeps_exact_and_semantic_messages_from_the_selected_chat(self):
        conversations = (
            chat(
                "target",
                "DeBERTa checks whether evidence supports a claim.",
                "A cautious semantic verifier helps reject attractive noise.",
                "Why judge evidence in an unrelated courtroom?",
            ),
        )
        def semantic_embed(texts):
            return [
                [0.0, 1.0] if "cautious" in text.casefold() or text.startswith("Why") else [1.0, 0.0]
                for text in texts
            ]

        index = HybridChatIndex(conversations, semantic_embed)

        hits = index.context_hits("Why did DeBERTa judge evidence?", ("target",), per_conversation=2)

        self.assertEqual({0, 1}, {item.message_position for item in hits})

    def test_public_summary_contains_only_rank_not_private_identifiers(self):
        private_id = "PRIVATE-CONVERSATION-ID"
        index = HybridChatIndex([chat(private_id, "Desktop package")], KeywordEmbedder(("desktop",)))
        result = index.route("desktop", top_k=1)

        rendered = json.dumps(result.public_summary((private_id,)))

        self.assertNotIn(private_id, rendered)
        self.assertTrue(result.public_summary((private_id,))["expected_conversation_in_top_k"])
        self.assertEqual(1, result.public_summary((private_id,))["best_expected_rank"])

    def test_empty_library_returns_empty_route(self):
        result = HybridChatIndex([], KeywordEmbedder(("anything",))).route("question", top_k=5)
        self.assertEqual((), result.conversation_ids)

    def test_index_is_the_real_core_router_not_a_parallel_demo(self):
        conversations = [chat("target", "A desktop package uses Tauri."), chat("other", "Bee notes.")]
        index = HybridChatIndex(conversations, KeywordEmbedder(("desktop", "bee")))
        modules = HarnessModules(
            route=index.core_router,
            read=lambda question, conversation: (),
            scan_secrets=lambda evidence: (),
            approve=lambda evidence: True,
            nli=lambda question, evidence: "unavailable",
            build_shelves=lambda question, checked: ShelfPlan((), ()),
            write=lambda question, used: "not called",
        )

        result = PocketICore(modules, top_k=1).run("desktop package", conversations)

        self.assertEqual("target", result.trace[1].detail["conversation_ids"][0])
        self.assertEqual("no_information", result.status)


if __name__ == "__main__":
    unittest.main()
