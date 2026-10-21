#!/usr/bin/env python3
"""API mock minimaliste pour le POC de tests de charge (JMeter / Locust).

Objectif : rendre les scénarios du depot executables sans dependance externe,
puisqu'ils ciblent `api.example.com` qui n'existe pas.

    POST /login      -> 200 {"access_token": ..., "token_type": "Bearer"}  (401 si mauvais identifiants)
    GET  /protected  -> 200 si "Authorization: Bearer <token>" valide, sinon 401
    GET  /health     -> 200 {"status": "ok"}

Le login accepte les deux formats utilises par les scenarios du POC :
  - JSON  : {"user": "testuser", "pass": "testpass"}      (locustfile.py)  ou username/password
  - FORM  : user=testuser&pass=testpass                   (plan_de_test.jmx)

Standard library uniquement (aucune installation requise).

Exemples
--------
    python mock_api/mock_server.py
    python mock_api/mock_server.py --port 8080 --latency-ms 120 --jitter-ms 80
"""

from __future__ import annotations

import argparse
import json
import random
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

USERS = {"testuser": "testpass"}

_tokens: dict[str, str] = {}
_lock = threading.Lock()
_started_at = time.time()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "MockAPI/1.0"

    # surcharges par ligne de commande
    latency_ms: float = 0.0
    jitter_ms: float = 0.0

    # --- utilitaires -----------------------------------------------------
    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        if getattr(self.server, "verbose", False):
            sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _simulate_backend_latency(self) -> None:
        delay = self.latency_ms
        if self.jitter_ms:
            delay += random.uniform(0, self.jitter_ms)
        if delay > 0:
            time.sleep(delay / 1000.0)

    def _bearer_token(self) -> str:
        header = self.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            return header[7:].strip()
        return ""

    # --- routes ----------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        if path == "/health":
            self._send_json(200, {"status": "ok", "uptime_s": round(time.time() - _started_at, 1)})
            return

        if path == "/protected":
            self._simulate_backend_latency()
            token = self._bearer_token()
            with _lock:
                user = _tokens.get(token)
            if user:
                self._send_json(200, {"message": "acces autorise", "user": user})
            else:
                self._send_json(401, {"error": "unauthorized"})
            return

        self._send_json(404, {"error": "not_found", "path": path})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/login":
            self._send_json(404, {"error": "not_found", "path": path})
            return

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        ctype = (self.headers.get("Content-Type") or "").lower()

        user = password = None
        if "application/json" in ctype:
            try:
                data = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                self._send_json(400, {"error": "invalid_json"})
                return
            user = data.get("user") or data.get("username")
            password = data.get("pass") or data.get("password")
        else:  # formulaire (defaut JMeter)
            form = parse_qs(raw.decode("utf-8", errors="replace"))
            user = (form.get("user") or form.get("username") or [None])[0]
            password = (form.get("pass") or form.get("password") or [None])[0]

        if not user or not password:
            self._send_json(400, {"error": "missing_credentials"})
            return

        if USERS.get(user) != password:
            self._send_json(401, {"error": "invalid_credentials"})
            return

        token = secrets.token_hex(16)
        with _lock:
            _tokens[token] = user
        self._send_json(200, {"access_token": token, "token_type": "Bearer", "expires_in": 3600})


def main() -> int:
    parser = argparse.ArgumentParser(description="API mock pour tests de charge (stdlib)")
    parser.add_argument("--host", default="127.0.0.1", help="adresse d'ecoute (defaut 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="port d'ecoute (defaut 8080)")
    parser.add_argument("--latency-ms", type=float, default=0.0,
                        help="latence fixe ajoutee a /protected, en ms (defaut 0)")
    parser.add_argument("--jitter-ms", type=float, default=0.0,
                        help="latence aleatoire ajoutee a /protected, en ms (defaut 0)")
    parser.add_argument("--verbose", action="store_true", help="journaliser chaque requete")
    args = parser.parse_args()

    Handler.latency_ms = args.latency_ms
    Handler.jitter_ms = args.jitter_ms

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    server.verbose = args.verbose

    base = f"http://{args.host}:{args.port}"
    print(f"API mock a l'ecoute sur {base}")
    print(f"  POST /login      200 access_token  (user=testuser / pass=testpass)")
    print(f"  GET  /protected  200 avec Bearer, sinon 401")
    print(f"  GET  /health     200")
    if args.latency_ms or args.jitter_ms:
        print(f"  latence simulee sur /protected : {args.latency_ms} ms + jitter {args.jitter_ms} ms")
    print("\nLocust : locust -f locust/locustfile.py --host " + base)
    print("JMeter : jmeter -n -t jmeter/plan_de_test.jmx -Jhost=%s -Jport=%d -Jprotocol=http -l resultats.jtl -e -o rapport_html"
          % (args.host, args.port))
    print("\nCtrl+C pour arreter.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArret du serveur.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
