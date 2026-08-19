import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from server import ApplicationHandler, init_db, record_publication_event, validate_submission


class SubmissionTests(unittest.TestCase):
    def test_d04_minimum(self):
        door, payload, author = validate_submission(
            {
                "door": "d04",
                "question": "Why?",
                "responses": [{"model": "Example AI", "raw": "Because."}],
                "author_mode": "anonymous",
                "consent": True,
            }
        )
        self.assertEqual(door, "d04")
        self.assertEqual(author, "anonymous")
        self.assertEqual(len(payload["responses"]), 1)

    def test_d06_requires_expert_observation(self):
        with self.assertRaises(ValueError):
            validate_submission(
                {
                    "door": "d06",
                    "question": "Is this correct?",
                    "responses": [{"model": "Example AI", "raw": "Yes."}],
                    "consent": True,
                }
            )

    def test_consent_is_required(self):
        with self.assertRaises(ValueError):
            validate_submission(
                {
                    "door": "d04",
                    "question": "Why?",
                    "responses": [{"model": "Example AI", "raw": "Because."}],
                }
            )

    def test_database_initializes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            self.assertTrue(path.exists())
            with sqlite3.connect(path) as db:
                columns = {row[1] for row in db.execute("PRAGMA table_info(contributions)")}
                self.assertIn("parent_public_id", columns)
                self.assertIsNotNone(db.execute("SELECT name FROM sqlite_master WHERE name = 'events'").fetchone())

    def test_public_corpus_excludes_pending_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            payload = json.dumps(
                {"question": "What changed?", "responses": [{"model": "Example AI", "raw": "This."}]}
            )
            with sqlite3.connect(path) as db:
                values = ("hash", "d04", payload, "anonymous", "2026-08-19T00:00:00+00:00", "2026-08-19T00:00:00+00:00")
                cursor = db.execute(
                    "INSERT INTO contributions (token_hash, door, payload, author, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    values,
                )
                db.execute("UPDATE contributions SET public_id = 'T0001' WHERE row_id = ?", (cursor.lastrowid,))
                cursor = db.execute(
                    "INSERT INTO contributions (token_hash, door, payload, author, status, created_at, updated_at) VALUES (?, ?, ?, ?, 'public', ?, ?)",
                    ("hash2", "d04", payload, "Yuka", values[-2], values[-1]),
                )
                db.execute("UPDATE contributions SET public_id = 'T0002' WHERE row_id = ?", (cursor.lastrowid,))
            handler = object.__new__(ApplicationHandler)
            handler.db_path = path
            records = handler.public_records()
            self.assertEqual([record["public_id"] for record in records], ["T0002"])
            self.assertEqual(records[0]["payload"]["question"], "What changed?")

    def test_continuation_creates_a_linked_global_event(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            payload = json.dumps(
                {"question": "Who notices the gap?", "responses": [{"model": "Example AI", "raw": "A person."}]}
            )
            with sqlite3.connect(path) as db:
                db.execute(
                    "INSERT INTO contributions "
                    "(public_id, token_hash, door, payload, author, status, parent_public_id, relation, created_at, updated_at) "
                    "VALUES ('T0002', 'child', 'd04', ?, 'Yuka', 'public', 'T0001', 'continues', ?, ?)",
                    (payload, "2026-08-19T00:00:00+00:00", "2026-08-19T00:00:00+00:00"),
                )
                record_publication_event(db, "T0002")
            handler = object.__new__(ApplicationHandler)
            handler.db_path = path
            events = handler.public_events()
            self.assertEqual(events[0]["event_id"], "E000001")
            self.assertEqual(events[0]["event_type"], "trace_continued")
            self.assertEqual(events[0]["links"][0]["target_id"], "T0001")


if __name__ == "__main__":
    unittest.main()
