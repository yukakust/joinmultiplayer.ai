"""Hybrid whole-conversation routing for the desktop Pocket i core."""

from __future__ import annotations

import collections
import math
import re
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from .pipeline import Conversation


TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
EmbedBatch = Callable[[Sequence[str]], Iterable[Sequence[float]]]


def words(text: str) -> list[str]:
    return [item.casefold() for item in TOKEN.findall(text)]


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(item) ** 2 for item in left))
    right_norm = math.sqrt(sum(float(item) ** 2 for item in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


@dataclass(frozen=True)
class RouteResult:
    conversation_ids: tuple[str, ...]
    lexical_ranks: tuple[str, ...]
    neural_ranks: tuple[str, ...]

    def public_summary(self, expected_ids: Sequence[str] = ()) -> dict[str, object]:
        """Expose ranks and hit counts without conversation IDs or text."""
        expected = set(expected_ids)
        best_rank = next((rank for rank, item in enumerate(self.conversation_ids, 1) if item in expected), None)
        return {
            "returned": len(self.conversation_ids),
            "expected_conversation_in_top_k": best_rank is not None,
            "best_expected_rank": best_rank,
            "privacy": "no text, conversation IDs, message coordinates or vectors",
        }


@dataclass(frozen=True)
class RouteHit:
    conversation_id: str
    message_position: int


class HybridChatIndex:
    """Rank whole chats by their best lexical and neural message matches."""

    def __init__(
        self,
        conversations: Sequence[Conversation],
        embed: EmbedBatch,
        *,
        document_vectors: Sequence[Sequence[float]] | None = None,
    ) -> None:
        self._conversation_ids = tuple(item.conversation_id for item in conversations)
        if len(self._conversation_ids) != len(set(self._conversation_ids)):
            raise ValueError("conversation IDs must be unique")
        self._message_conversations = tuple(
            conversation.conversation_id
            for conversation in conversations
            for _message in conversation.messages
        )
        self._message_positions = tuple(
            position
            for conversation in conversations
            for position, _message in enumerate(conversation.messages)
        )
        self._texts = tuple(message.text for conversation in conversations for message in conversation.messages)
        self._tokenized = tuple(words(text) for text in self._texts)
        self._frequencies = tuple(collections.Counter(tokens) for tokens in self._tokenized)
        self._lengths = tuple(len(tokens) for tokens in self._tokenized)
        self._average_length = sum(self._lengths) / len(self._lengths) if self._lengths else 1.0
        document_frequency: collections.Counter[str] = collections.Counter()
        for frequency in self._frequencies:
            document_frequency.update(frequency.keys())
        self._document_frequency = document_frequency
        self._embed = embed
        source_vectors = document_vectors if document_vectors is not None else (embed(self._texts) if self._texts else ())
        vectors = tuple(tuple(float(value) for value in vector) for vector in source_vectors)
        if len(vectors) != len(self._texts):
            raise ValueError("embedder returned the wrong number of document vectors")
        widths = {len(item) for item in vectors}
        if len(widths) > 1 or vectors and not next(iter(widths)):
            raise ValueError("document vectors must have one non-zero width")
        self._vectors = vectors

    @property
    def conversations(self) -> int:
        return len(self._conversation_ids)

    @property
    def messages(self) -> int:
        return len(self._texts)

    def route(self, question: str, top_k: int = 5) -> RouteResult:
        result, _hits = self.route_with_hits(question, top_k=top_k)
        return result

    def route_with_hits(self, question: str, top_k: int = 5) -> tuple[RouteResult, tuple[RouteHit, ...]]:
        question = question.strip()
        if not question:
            raise ValueError("question must not be empty")
        if top_k < 1:
            raise ValueError("top_k must be positive")
        if not self._conversation_ids:
            return RouteResult((), (), ()), ()

        lexical_message_scores = self._bm25(question)
        lexical = self._rank_chats(lexical_message_scores)

        query_vectors = tuple(tuple(float(value) for value in vector) for vector in self._embed((question,)))
        if len(query_vectors) != 1:
            raise ValueError("embedder must return exactly one query vector")
        if self._vectors and len(query_vectors[0]) != len(self._vectors[0]):
            raise ValueError("query and document vectors have different widths")
        neural_message_scores = [_cosine(query_vectors[0], vector) for vector in self._vectors]
        neural = self._rank_chats(neural_message_scores)

        fused = self._reciprocal_rank_fusion(lexical, neural)[: min(top_k, len(self._conversation_ids))]
        lexical_message_ranks = self._message_ranks(lexical_message_scores)
        neural_message_ranks = self._message_ranks(neural_message_scores)
        message_scores = [
            1 / (60 + lexical_message_ranks[index]) + 1 / (60 + neural_message_ranks[index])
            for index in range(len(self._texts))
        ]
        hits = []
        for conversation_id in fused:
            candidates = [
                index for index, item in enumerate(self._message_conversations) if item == conversation_id
            ]
            if not candidates:
                continue
            best = min(candidates, key=lambda index: (-message_scores[index], index))
            hits.append(RouteHit(conversation_id, self._message_positions[best]))
        return RouteResult(tuple(fused), tuple(lexical), tuple(neural)), tuple(hits)

    def core_router(self, question: str, conversations: Sequence[Conversation], top_k: int) -> tuple[str, ...]:
        """Use this index directly as the `HarnessModules.route` callback."""
        supplied = tuple(item.conversation_id for item in conversations)
        if supplied != self._conversation_ids:
            raise ValueError("core conversations do not match the indexed library snapshot")
        return self.route(question, top_k).conversation_ids

    def _bm25(self, question: str, k1: float = 1.5, b: float = 0.75) -> list[float]:
        count = len(self._texts)
        query = collections.Counter(words(question))
        scores = []
        for length, frequency in zip(self._lengths, self._frequencies):
            score = 0.0
            for term, query_frequency in query.items():
                occurrences = frequency.get(term, 0)
                if not occurrences:
                    continue
                present = self._document_frequency[term]
                inverse = math.log(1 + (count - present + 0.5) / (present + 0.5))
                denominator = occurrences + k1 * (1 - b + b * length / self._average_length)
                score += query_frequency * inverse * occurrences * (k1 + 1) / denominator
            scores.append(score)
        return scores

    def _rank_chats(self, message_scores: Sequence[float]) -> list[str]:
        best = {conversation_id: float("-inf") for conversation_id in self._conversation_ids}
        for conversation_id, score in zip(self._message_conversations, message_scores):
            best[conversation_id] = max(best[conversation_id], float(score))
        return sorted(best, key=lambda item: (-best[item], item))

    @staticmethod
    def _message_ranks(message_scores: Sequence[float]) -> dict[int, int]:
        ordered = sorted(range(len(message_scores)), key=lambda index: (-float(message_scores[index]), index))
        return {index: rank for rank, index in enumerate(ordered, 1)}

    @staticmethod
    def _reciprocal_rank_fusion(first: Sequence[str], second: Sequence[str], offset: int = 60) -> list[str]:
        first_rank = {item: rank for rank, item in enumerate(first, 1)}
        second_rank = {item: rank for rank, item in enumerate(second, 1)}
        return sorted(
            set(first_rank) | set(second_rank),
            key=lambda item: (
                -(1 / (offset + first_rank[item]) if item in first_rank else 0)
                -(1 / (offset + second_rank[item]) if item in second_rank else 0),
                item,
            ),
        )
