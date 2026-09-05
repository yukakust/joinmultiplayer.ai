import importlib.util
import gzip
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
GATEWAY_PATH = ROOT / "ops" / "pocket-i" / "production" / "pocket-i-brain-gateway.py"


class Backend(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        body = b'{"status":"ok"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request_body = self.rfile.read(length)
        body = json.dumps({"received": json.loads(request_body)}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class BrainGatewayTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        token_path = Path(self.directory.name) / "token"
        token_path.write_text("t" * 64, encoding="utf-8")
        old_token_path = os.environ.get("POCKET_I_GATEWAY_TOKEN_FILE")
        os.environ["POCKET_I_GATEWAY_TOKEN_FILE"] = str(token_path)
        try:
            spec = importlib.util.spec_from_file_location("brain_gateway", GATEWAY_PATH)
            self.gateway = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.gateway)
        finally:
            if old_token_path is None:
                os.environ.pop("POCKET_I_GATEWAY_TOKEN_FILE", None)
            else:
                os.environ["POCKET_I_GATEWAY_TOKEN_FILE"] = old_token_path

        self.backend = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
        self.gateway.BACKENDS["reader"] = ("127.0.0.1", self.backend.server_port)
        self.gateway.AUDIT_DIR = str(Path(self.directory.name) / "audit")
        self.proxy = ThreadingHTTPServer(("127.0.0.1", 0), self.gateway.Gateway)
        self.threads = [
            threading.Thread(target=self.backend.serve_forever, daemon=True),
            threading.Thread(target=self.proxy.serve_forever, daemon=True),
        ]
        for thread in self.threads:
            thread.start()

    def tearDown(self):
        self.proxy.shutdown()
        self.backend.shutdown()
        self.proxy.server_close()
        self.backend.server_close()
        self.directory.cleanup()

    def request(self, path, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return urlopen(Request(f"http://127.0.0.1:{self.proxy.server_port}{path}", headers=headers), timeout=3)

    def test_requires_token_and_proxies_only_the_reader_health_route(self):
        with self.assertRaises(HTTPError) as missing:
            self.request("/reader/health")
        self.assertEqual(missing.exception.code, 401)

        with self.request("/reader/health", "t" * 64) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response), {"status": "ok"})

        with self.assertRaises(HTTPError) as forbidden:
            self.request("/reader/unknown", "t" * 64)
        self.assertEqual(forbidden.exception.code, 404)

    def test_opted_in_post_is_written_privately_without_authorization(self):
        payload = {"messages": [{"role": "user", "content": "private alpha question"}]}
        request = Request(
            f"http://127.0.0.1:{self.proxy.server_port}/reader/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {'t' * 64}",
                "Content-Type": "application/json",
                "X-Pocket-I-Alpha-Audit": "full",
            },
            method="POST",
        )
        with urlopen(request, timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertTrue(response.headers.get("X-Pocket-I-Audit-Id"))

        files = list(Path(self.gateway.AUDIT_DIR).glob("*.json.gz"))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].stat().st_mode & 0o777, 0o600)
        with gzip.open(files[0], "rt", encoding="utf-8") as handle:
            record = json.load(handle)
        self.assertEqual(record["route"], "reader/v1/chat/completions")
        self.assertEqual(record["request"], payload)
        self.assertEqual(record["response_status"], 200)
        self.assertNotIn("Authorization", json.dumps(record))


if __name__ == "__main__":
    unittest.main()
