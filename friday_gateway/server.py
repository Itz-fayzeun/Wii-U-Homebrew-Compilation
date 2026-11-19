#!/usr/bin/env python3
"""Optional FRIDAY HTTPS gateway backend. Keep API keys off the Switch."""
from __future__ import annotations

from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
import threading
import time

# Requires: pip install openai
from openai import OpenAI

HOST = os.environ.get("FRIDAY_HOST", "127.0.0.1")
PORT = int(os.environ.get("FRIDAY_PORT", "8765"))
ACCESS_TOKEN = os.environ.get("FRIDAY_SHARED_TOKEN", "")
API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = os.environ.get("FRIDAY_MODEL", "gpt-4.1-mini")

if len(ACCESS_TOKEN) < 16:
    raise SystemExit("Set FRIDAY_SHARED_TOKEN to a random value of at least 16 characters.")
if not API_KEY:
    raise SystemExit("Set OPENAI_API_KEY on the gateway server only.")

client = OpenAI(api_key=API_KEY, timeout=17.0, max_retries=0)
recent_calls: deque[float] = deque()
rate_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = "FRIDAY/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        # Avoid printing questions, tokens or account identifiers.
        pass

    def respond(self, status: int, payload: dict[str, str]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        if self.path != "/ask":
            return self.respond(404, {"error": "not found"})
        actual = self.headers.get("X-Friday-Token", "")
        if not hmac.compare_digest(actual, ACCESS_TOKEN):
            return self.respond(401, {"error": "unauthorized"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.respond(400, {"error": "invalid length"})
        if not 0 < length <= 2048:
            return self.respond(413, {"error": "invalid length"})

        try:
            body = json.loads(self.rfile.read(length))
            message = body["message"]
        except (ValueError, KeyError, TypeError):
            return self.respond(400, {"error": "invalid JSON"})
        if not isinstance(message, str) or not message.strip() or len(message) > 280:
            return self.respond(400, {"error": "question length must be 1-280"})

        with rate_lock:
            now = time.monotonic()
            while recent_calls and now - recent_calls[0] > 60:
                recent_calls.popleft()
            if len(recent_calls) >= 10:
                return self.respond(429, {"error": "rate limit"})
            recent_calls.append(now)

        try:
            response = client.responses.create(
                model=MODEL,
                instructions=(
                    "Tu es FRIDAY, assistante de jeu et de diagnostic de LunarNX FR+ "
                    "sur Nintendo Switch Lite, reliée à une PS5 par Remote Play. "
                    "Réponds en français, en 2 à 5 phrases claires. "
                    "Tu peux conseiller mais n'as AUCUN accès direct à la console "
                    "et ne dois pas prétendre avoir réparé ou contrôlé le matériel. "
                    "Ne demande pas d'identifiants PSN, de mots de passe ou de clés API. "
                    "Si des données de réseau ne sont pas fournies, ne les invente pas."
                ),
                input=message,
                max_output_tokens=260,
                store=False,
            )
            answer = (response.output_text or "").strip()
            if not answer:
                return self.respond(502, {"error": "empty model response"})
            self.respond(200, {"reply": answer[:1400]})
        except Exception:
            # Do not reveal provider errors, credentials or request internals.
            self.respond(502, {"error": "model provider unavailable"})


if __name__ == "__main__":
    if HOST not in ("127.0.0.1", "::1", "localhost"):
        raise SystemExit(
            "For security, bind FRIDAY_HOST to localhost and put an HTTPS "
            "reverse proxy in front of it."
        )
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"FRIDAY backend active on {HOST}:{PORT}; use an HTTPS reverse proxy for Switch.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
