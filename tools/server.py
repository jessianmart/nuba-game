"""Static server for the NUBA prototype.

The stock SimpleHTTPRequestHandler server uses the socketserver default backlog
of 5. A stage loads a few hundred textures in parallel, which overflows the
accept queue and surfaces in the browser as ERR_CONNECTION_REFUSED, so the
backlog is raised well above that.
"""

import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
PORT = int(os.environ.get("NUBA_PORT", "8080"))


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


if __name__ == "__main__":
    os.chdir(PUB)
    httpd = Server(("0.0.0.0", PORT), Handler)
    print(f"NUBA server serving {PUB} on http://localhost:{PORT} "
          f"(backlog {Server.request_queue_size})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass