import importlib.util
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


if __name__ == "__main__":
    unittest.main()
