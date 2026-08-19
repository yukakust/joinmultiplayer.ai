import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from server import ApplicationHandler, init_db, validate_submission


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


if __name__ == "__main__":
    unittest.main()
