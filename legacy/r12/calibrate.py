"""One-time menu calibration in the iPhone's own Safari. Only a tiny greyscale button patch is stored."""
import json
import math
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = Path.home() / ".necro-gold-menu.json"


def configure():
    token = "/" + secrets.token_urlsafe(8)
    # Bind to loopback and serve until one valid calibration is received.
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != token:
                return self.send_error(404)
            data = (ROOT / "setup.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if self.path != token or self.headers.get("Origin") != "http://127.0.0.1:8765":
                return self.send_error(403)
            try:
                size = int(self.headers["Content-Length"])
                if not 0 < size < 32000:
                    raise ValueError()
                steps = json.loads(self.rfile.read(size))
                if not isinstance(steps, list) or not 1 <= len(steps) <= 2:
                    raise ValueError()
                for step in steps:
                    patch, point = step["patch"], step["point"]
                    if len(patch)!=840 or not all(type(v) is int and 0 <= v <= 255 for v in patch):
                        raise ValueError()
                    if len(point)!=2 or not all(isinstance(v,(float,int)) and math.isfinite(v) and .04<v<.96 for v in point):
                        raise ValueError()
                    if max(patch)-min(patch)<45:
                        raise ValueError()
            except (ValueError, KeyError, TypeError):
                return self.send_error(400,"Please select the button text again")
            tmp = CONFIG.with_suffix(".tmp")
            tmp.write_text(json.dumps(steps))
            tmp.replace(CONFIG)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            self.server.done = True

        def log_message(self, *args):
            pass

    with HTTPServer(("127.0.0.1",8765),Handler) as server:
        print("iPhoneのSafariで次のURLを開いて登録してください。\nhttp://127.0.0.1:8765"+token, flush=True)
        server.done = False
        while not server.done:
            server.handle_request()
    print("登録しました。iSHに戻ってください。")
