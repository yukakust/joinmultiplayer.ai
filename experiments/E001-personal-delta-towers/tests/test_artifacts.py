from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from e001.artifacts import write_json, write_jsonl


class ArtifactTests(unittest.TestCase):
    def test_json_and_jsonl_are_written_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "summary.json", {"ok": True})
            write_jsonl(root / "tasks.jsonl", [{"id": 1}, {"id": 2}])

            self.assertEqual(json.loads((root / "summary.json").read_text()), {"ok": True})
            lines = (root / "tasks.jsonl").read_text().splitlines()
            self.assertEqual([json.loads(line)["id"] for line in lines], [1, 2])


if __name__ == "__main__":
    unittest.main()
