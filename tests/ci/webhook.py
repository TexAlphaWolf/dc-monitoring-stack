"""Tiny Alertmanager webhook receiver for the CI end-to-end test.

POST /      store the notification (JSON) in memory
GET  /count number of notifications received
GET  /last  last notification, as JSON
GET  /names names of all alerts received so far, as JSON
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

received: list[dict] = []


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        received.append(json.loads(self.rfile.read(length) or b"{}"))
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == "/count":
            body = str(len(received)).encode()
        elif self.path == "/names":
            names = sorted({a["labels"]["alertname"] for n in received for a in n["alerts"]})
            body = json.dumps(names).encode()
        elif self.path == "/last":
            body = json.dumps(received[-1] if received else {}).encode()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
