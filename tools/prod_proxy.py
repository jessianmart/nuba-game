#!/usr/bin/env python3
"""prod_proxy.py — reverse proxy: localhost:8080 -> Vercel production deploy.

Lets the deterministic battery (verify_browser_runtime.py, test_e2e_suite.py)
run UNCHANGED against the production artifacts: every byte fetched by the
browser comes from the public CDN. Any 404/regression in the deployed files
fails the suite.

Usage: python tools/prod_proxy.py [port]   (default 8080)
"""
import sys
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "https://goofy-mendeleev.vercel.app"
HOP = {"connection", "keep-alive", "transfer-encoding", "content-encoding",
       "content-length", "accept-encoding"}


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        url = UPSTREAM + self.path
        req = urllib.request.Request(url, headers={"User-Agent": "nuba-prod-proxy/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:  # follows 308 -> /
                body, status, hdrs = r.read(), r.status, r.headers
        except urllib.error.HTTPError as e:
            body, status, hdrs = e.read(), e.code, e.headers
        except Exception as e:  # network/TLS problem upstream
            self.send_error(502, f"upstream error: {e}")
            return
        self.send_response(status)
        for k, v in hdrs.items():
            if k.lower() not in HOP:
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write("[proxy] %s %s\n" % (self.command if hasattr(self, 'command') else '?', self.path))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"prod_proxy: http://localhost:{port} -> {UPSTREAM}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Proxy).serve_forever()
