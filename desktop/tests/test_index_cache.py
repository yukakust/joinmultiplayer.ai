from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from pocket_i_core import Conversation, Message, build_cached_index


class CountingEmbedder:
    def __init__(self):
        self.document_batches = []

    def __call__(self, texts):
        texts = list(texts)
        self.document_batches.append(tuple(texts))
        return [[float(len(text)), float(sum(ord(char) for char in text) % 97)] for text in texts]


def library(second_text="second fact"):
    return (
        Conversation("c1", "fixture", (Message("c1:1", "user", "first fact"),)),
        Conversation("c2", "fixture", (Message("c2:1", "assistant", second_text),)),
    )


class IndexCacheTests(unittest.TestCase):
    def test_second_build_reuses_every_document_vector(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.sqlite3"
            first = CountingEmbedder()
            _, cold = build_cached_index(library(), first, cache_path=path, model_fingerprint="model-v1")
            second = CountingEmbedder()
            index, warm = build_cached_index(library(), second, cache_path=path, model_fingerprint="model-v1")

            self.assertEqual((0, 2), (cold.reused, cold.embedded))
            self.assertEqual((2, 0), (warm.reused, warm.embedded))
            self.assertEqual([], second.document_batches)
            self.assertEqual("c1", index.route("first", top_k=1).conversation_ids[0])

    def test_changed_message_embeds_only_that_message(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.sqlite3"
            build_cached_index(library(), CountingEmbedder(), cache_path=path, model_fingerprint="model-v1")
            embedder = CountingEmbedder()
            _, stats = build_cached_index(library("changed second fact"), embedder, cache_path=path, model_fingerprint="model-v1")

            self.assertEqual((1, 1), (stats.reused, stats.embedded))
            self.assertEqual([("changed second fact",)], embedder.document_batches)

    def test_model_change_rebuilds_all_vectors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.sqlite3"
            build_cached_index(library(), CountingEmbedder(), cache_path=path, model_fingerprint="model-v1")
            _, stats = build_cached_index(library(), CountingEmbedder(), cache_path=path, model_fingerprint="model-v2")

            self.assertTrue(stats.rebuilt_for_model_change)
            self.assertEqual(2, stats.embedded)

    def test_cache_contains_hashes_and_vectors_but_not_private_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.sqlite3"
            private = "PRIVATE SOURCE TEXT"
            data = (Conversation("private-id", "fixture", (Message("private-path:1", "user", private),)),)
            build_cached_index(data, CountingEmbedder(), cache_path=path, model_fingerprint="model-v1")

            rendered = path.read_bytes()
            self.assertNotIn(private.encode(), rendered)
            self.assertNotIn(b"private-path", rendered)
            self.assertEqual(0o600, path.stat().st_mode & 0o777)
            connection = sqlite3.connect(path)
            columns = [row[1] for row in connection.execute("pragma table_info(vectors)")]
            connection.close()
            self.assertNotIn("text", columns)

    def test_commits_each_batch_and_resumes_after_interruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.sqlite3"
            data = tuple(
                Conversation(f"c{index}", "fixture", (Message(f"c{index}:1", "user", f"fact {index}"),))
                for index in range(5)
            )
            calls = 0

            def interrupted(texts):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError("fixture interruption")
                return CountingEmbedder()(texts)

            with self.assertRaises(RuntimeError):
                build_cached_index(
                    data, interrupted, cache_path=path, model_fingerprint="model-v1", batch_size=2
                )
            resumed = CountingEmbedder()
            _, stats = build_cached_index(
                data, resumed, cache_path=path, model_fingerprint="model-v1", batch_size=2
            )

            self.assertEqual(2, stats.reused)
            self.assertEqual(3, stats.embedded)
            self.assertEqual([("fact 2", "fact 3"), ("fact 4",)], resumed.document_batches)

    def test_reports_saved_message_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            progress = []
            build_cached_index(
                library(),
                CountingEmbedder(),
                cache_path=Path(directory) / "index.sqlite3",
                model_fingerprint="model-v1",
                batch_size=1,
                on_progress=lambda completed, total: progress.append((completed, total)),
            )
            self.assertEqual([(0, 2), (1, 2), (2, 2)], progress)


if __name__ == "__main__":
    unittest.main()
