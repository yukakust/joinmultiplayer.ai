import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task_world", ROOT / "src" / "task_world.py")
task_world = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(task_world)


class TaskWorldTests(unittest.TestCase):
    def test_answer_space_is_not_a_binary_guess(self):
        sample = task_world.build_sample()
        self.assertEqual(sample["complete_answer_space"], 32_768)
        self.assertEqual(sample["blind_guess_probability"], 1 / 32_768)
        self.assertEqual(sample["pair_missing_segment_guess_probability"], 1 / 32)

    def test_every_segment_matches_the_public_derivation(self):
        for task in task_world.build_sample()["tasks"]:
            for domain, derivation in task["derivation"].items():
                value = task_world.evaluate(domain, derivation["inputs"])
                self.assertEqual(value, derivation["value"])
                self.assertEqual(task_world.format_segment(domain, value), derivation["segment"])
            expected = " / ".join(task["derivation"][domain]["segment"] for domain in task["order"])
            self.assertEqual(task["answer"], expected)

    def test_generator_is_deterministic_and_marks_samples_unlocked(self):
        first = task_world.build_sample()
        second = task_world.build_sample()
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "illustrative_not_locked")
        self.assertEqual(len(first["tasks"]), 12)

    def test_cli_artifact_matches_in_memory_generator(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sample.json"
            output.write_text(json.dumps(task_world.build_sample(), ensure_ascii=False, indent=2) + "\n")
            self.assertEqual(json.loads(output.read_text()), task_world.build_sample())


if __name__ == "__main__":
    unittest.main()
