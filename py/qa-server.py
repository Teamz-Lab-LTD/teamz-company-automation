#!/usr/bin/env python3
"""Multi-threaded HTTP server for QA testing. Handles concurrent requests without crashing."""
import http.server, socketserver, os, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9091
_here = os.path.dirname(os.path.abspath(__file__))
# py/ → automation → parent = teamzlab-tools (submodule layout)
_automation = os.path.abspath(os.path.join(_here, ".."))
_site = os.path.abspath(os.path.join(_automation, ".."))
if os.environ.get("TEAMZ_QA_SITE_ROOT"):
    ROOT = os.path.abspath(os.environ["TEAMZ_QA_SITE_ROOT"])
elif os.path.isfile(os.path.join(_site, "index.html")):
    ROOT = _site
else:
    ROOT = _automation
os.chdir(ROOT)

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Silent

class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

ThreadedServer(("", PORT), QuietHandler).serve_forever()
