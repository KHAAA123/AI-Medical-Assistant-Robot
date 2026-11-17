from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    from .pharmacity_service import answer_product_question, search_products
except ImportError:
    from pharmacity_service import answer_product_question, search_products


ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data: https:; "
    "connect-src 'self'"
)


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


load_env_file(ROOT_DIR.parent / ".env")


class PharmacityChatbotHandler(SimpleHTTPRequestHandler):
    server_version = "PharmacityChatbot/0.1"

    def log_message(self, format: str, *args: object) -> None:
        print(f"[pharmacity-chatbot] {format % args}")

    def end_headers(self) -> None:
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path in {"/", "/index.html"}:
            self._send_file(WEB_DIR / "index.html")
            return
        if path.startswith("/"):
            candidate = (WEB_DIR / path.lstrip("/")).resolve()
            if WEB_DIR.resolve() in candidate.parents and candidate.is_file():
                self._send_file(candidate)
                return
        self._send_json({"detail": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/api/pharmacity/search", "/robot/api/pharmacity/search"}:
            self._handle_search()
            return
        if parsed.path in {"/api/pharmacity/answer", "/robot/api/pharmacity/answer"}:
            self._handle_answer()
            return
        self._send_json({"detail": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def _handle_search(self) -> None:
        try:
            payload = self._read_json()
            query = str(payload.get("query") or "").strip()
            if not query:
                self._send_json({"detail": "Missing query"}, status=HTTPStatus.BAD_REQUEST)
                return
            result = search_products(
                query,
                original_query=str(payload.get("original_query") or query),
                target_intent=str(payload.get("target_intent") or "") or None,
            )
            self._send_json(result)
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_GATEWAY)

    def _handle_answer(self) -> None:
        try:
            payload = self._read_json()
            product = payload.get("product")
            if not isinstance(product, dict):
                self._send_json({"detail": "Missing product"}, status=HTTPStatus.BAD_REQUEST)
                return
            original_query = str(payload.get("original_query") or product.get("name") or "").strip()
            target_intent = str(payload.get("target_intent") or "").strip()
            result = answer_product_question(original_query, target_intent, product)
            self._send_json(result)
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_GATEWAY)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON body") from exc

    def _send_json(self, payload: dict, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self._send_json({"detail": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run() -> None:
    host = os.environ.get("PHARMACITY_CHATBOT_HOST", "127.0.0.1")
    port = int(os.environ.get("PHARMACITY_CHATBOT_PORT", "8010"))
    httpd = ThreadingHTTPServer((host, port), PharmacityChatbotHandler)
    print(f"Serving Pharmacity chatbot at http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
