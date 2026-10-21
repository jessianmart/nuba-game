"""Static server for the NUBA prototype.

The stock SimpleHTTPRequestHandler server uses the socketserver default backlog
of 5. A stage loads a few hundred textures in parallel, which overflows the
accept queue and surfaces in the browser as ERR_CONNECTION_REFUSED, so the
backlog is raised well above that.

PV-B.5: gzip on the fly for compressible payloads (JSON/JS/CSS/HTML).
The arena map JSON is 8.2 MB raw and compresses ~5x — without it every device
downloads 8 MB of numbers before a single triangle appears. Production hosts
(Vercel) do this automatically; the local dev server now matches.
"""

import gzip
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
PORT = int(os.environ.get("NUBA_PORT", "8080"))

GZIP_TYPES = {
    ".json": "application/json",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".html": "text/html",
    ".htm": "text/html",
    ".webmanifest": "application/manifest+json",
    ".txt": "text/plain",
    ".md": "text/plain",
}
GZIP_MIN_BYTES = 1024


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 256


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        """gzip para tipos comprimeveis (o resto cai no handler padrao)."""
        if "gzip" in (self.headers.get("Accept-Encoding") or ""):
            path = self.translate_path(self.path)
            if os.path.isfile(path):
                ext = os.path.splitext(path)[1].lower()
                ctype = GZIP_TYPES.get(ext)
                if ctype and os.path.getsize(path) >= GZIP_MIN_BYTES:
                    try:
                        with open(path, "rb") as fh:
                            raw = fh.read()
                        packed = gzip.compress(raw, 6)
                        self.send_response(200)
                        self.send_header("Content-Type", ctype)
                        self.send_header("Content-Encoding", "gzip")
                        self.send_header("Content-Length", str(len(packed)))
                        self.send_header("Vary", "Accept-Encoding")
                        self.end_headers()
                        self.wfile.write(packed)
                        return
                    except (BrokenPipeError, ConnectionResetError):
                        return
        super().do_GET()


if __name__ == "__main__":
    os.chdir(PUB)
    httpd = Server(("0.0.0.0", PORT), Handler)
    print(f"NUBA server serving {PUB} on http://localhost:{PORT} "
          f"(backlog {Server.request_queue_size}, gzip on)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
