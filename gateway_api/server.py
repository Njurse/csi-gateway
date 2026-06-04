from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .state import GatewayState

logger = logging.getLogger(__name__)

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "4040"))


class GatewayRequestHandler(BaseHTTPRequestHandler):
    server_version = "CSI-Gateway-API/1.0"

    def _write_json(self, payload: dict, status: int = 200):
        encoded = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        state: GatewayState = getattr(self.server, "gateway_state")

        if parsed.path in {"/", "/api", "/api/state"}:
            self._write_json({"ok": True, "service": "csi-gateway", "state": state.snapshot()})
            return

        if parsed.path == "/api/health":
            self._write_json({"ok": True, "service": "csi-gateway"})
            return

        if parsed.path == "/api/nodes":
            snapshot = state.snapshot()
            self._write_json({"ok": True, "nodes": snapshot["nodes"], "total_nodes": snapshot["total_nodes"]})
            return

        if parsed.path == "/api/recent":
            params = parse_qs(parsed.query)
            limit = int(params.get("limit", [25])[0])
            snapshot = state.snapshot()
            self._write_json({"ok": True, "recent_packets": snapshot["recent_packets"][-limit:]})
            return

        self._write_json({"ok": False, "error": "not_found"}, status=404)

    def log_message(self, format, *args):
        logger.info("API %s - %s", self.address_string(), format % args)


async def start_api_server(state: GatewayState):
    server = ThreadingHTTPServer((API_HOST, API_PORT), GatewayRequestHandler)
    server.gateway_state = state

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    logger.info("HTTP API server listening on http://%s:%s", API_HOST, API_PORT)

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        logger.info("HTTP API server stopped")
        raise
