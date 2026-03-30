#!/usr/bin/env python3
"""Multi-threaded HTTP server for QA testing. Handles concurrent requests without crashing."""
import http.server, socketserver, os, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9091
_here = os.path.dirname(os.path.abspath(__file__))
# When run as submodule under teamzlab-tools, serve the parent repo (static site root).
_parent = os.path.abspath(os.path.join(_here, ".."))
if os.environ.get("TEAMZ_QA_SITE_ROOT"):
    ROOT = os.path.abspath(os.environ["TEAMZ_QA_SITE_ROOT"])
elif os.path.isfile(os.path.join(_parent, "index.html")):
    ROOT = _parent
else:
    ROOT = _here
os.chdir(ROOT)

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Silent

class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

ThreadedServer(("", PORT), QuietHandler).serve_forever()
