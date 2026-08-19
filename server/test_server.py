import tempfile
import unittest
from pathlib import Path

from server import init_db, validate_submission


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


if __name__ == "__main__":
    unittest.main()
