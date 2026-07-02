#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ticket_processor.infrastructure.config.container import get_container  # noqa: E402

container = get_container()


class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "healthy"})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/webhook":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_payload = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_payload.decode("utf-8"))
            result = container.process_webhook_use_case.execute(payload)
        except Exception as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"success": False, "error": str(exc)})
            return

        self._send_json(
            HTTPStatus.OK,
            {
                "success": result.success,
                "message_id": result.message_id,
                "processed_purchases": list(result.processed_purchases),
                "reason": result.reason,
            },
        )

    def log_message(self, format: str, *args: object) -> None:
        container.logger.info("webhook_http", message=format % args)

    def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 8080), WebhookHandler)
    container.logger.info("webhook_server_started", port=8080)
    server.serve_forever()


if __name__ == "__main__":
    main()
