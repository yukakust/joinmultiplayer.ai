import importlib.util
import os
import unittest
from pathlib import Path


CONNECTOR_PATH = Path(__file__).resolve().parents[1] / "site" / "connector" / "codex_lab_connector.py"
SPEC = importlib.util.spec_from_file_location("codex_lab_connector", CONNECTOR_PATH)
connector = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(connector)


class ConnectorTests(unittest.TestCase):
    def test_redaction_removes_secrets_and_local_paths(self):
        value = connector.redact_text(
            "Read /home/alice/repo/file.txt with api_key=super-secret-value"
        )
        self.assertEqual(value, "Read <local-path> with <redacted-secret>")

    def test_safe_environment_drops_provider_and_git_secrets(self):
        previous = dict(os.environ)
        try:
            os.environ["OPENAI_API_KEY"] = "secret"
            os.environ["GITHUB_TOKEN"] = "secret"
            os.environ["PATH"] = "/usr/bin"
            safe = connector.safe_environment()
        finally:
            os.environ.clear()
            os.environ.update(previous)
        self.assertEqual(safe["PATH"], "/usr/bin")
        self.assertNotIn("OPENAI_API_KEY", safe)
        self.assertNotIn("GITHUB_TOKEN", safe)

    def test_normalizer_omits_reasoning_and_command_output(self):
        workspace = Path("/tmp/public-repo")
        self.assertIsNone(
            connector.normalize_codex_event(
                {
                    "type": "item.completed",
                    "item": {"type": "reasoning", "text": "private chain of thought"},
                },
                workspace,
            )
        )
        event_type, payload = connector.normalize_codex_event(
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "python3 script.py --password secret",
                    "aggregated_output": "sk-should-never-leave",
                    "status": "completed",
                    "exit_code": 0,
                },
            },
            workspace,
        )
        self.assertEqual(event_type, "command_status")
        self.assertEqual(payload["command"], "python3")
        self.assertNotIn("aggregated_output", payload)

    def test_normalizer_only_exposes_relative_changed_files(self):
        workspace = Path("/tmp/public-repo")
        event_type, payload = connector.normalize_codex_event(
            {
                "type": "item.completed",
                "item": {
                    "type": "file_change",
                    "changes": [
                        {"path": "/tmp/public-repo/experiment.py"},
                        {"path": "/tmp/private.txt"},
                    ],
                    "status": "completed",
                },
            },
            workspace,
        )
        self.assertEqual(event_type, "file_change")
        self.assertEqual(payload["files"], ["experiment.py"])


if __name__ == "__main__":
    unittest.main()

