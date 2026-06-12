#!/usr/bin/env python3
"""Gallery server: static files + persistent validation/label state.

GET  /api/state                -> {"npcOk": {...}, "overrides": {...}}
POST /api/state  {"op": {"kind": "npcOk"|"override", "hash": "0x..", "value": ...}}
                 or bulk: {"merge": {"npcOk": {...}, "overrides": {...}}}
State persists to validation.json next to the served files (atomic write).

Usage: python3 serve_gallery.py [port] [serve_dir]
"""
import json
import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5300
ROOT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
STATE_PATH = os.path.join(ROOT, "validation.json")

_lock = threading.Lock()
_state = {"npcOk": {}, "overrides": {}}
if os.path.exists(STATE_PATH):
    with open(STATE_PATH) as f:
        _state.update(json.load(f))


def _save():
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(_state, f)
    os.replace(tmp, STATE_PATH)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/state":
            with _lock:
                return self._json(_state)
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/state":
            return self._json({"error": "not found"}, 404)
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return self._json({"error": "bad json"}, 400)
        with _lock:
            op = payload.get("op")
            if op and op.get("hash"):
                key = "npcOk" if op.get("kind") == "npcOk" else "overrides"
                if op.get("value") in (None, False, ""):
                    _state[key].pop(op["hash"], None)
                else:
                    _state[key][op["hash"]] = op["value"]
            merge = payload.get("merge")
            if merge:
                for key in ("npcOk", "overrides"):
                    _state[key].update(merge.get(key, {}))
            _save()
            return self._json({"ok": True, "npcOk": len(_state["npcOk"]),
                               "overrides": len(_state["overrides"])})


if __name__ == "__main__":
    print(f"serving {ROOT} on :{PORT}, state -> {STATE_PATH}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
