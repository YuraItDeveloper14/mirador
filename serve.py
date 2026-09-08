"""Static server for previewing index.html over HTTP.

Python's built-in `http.server` does not answer HTTP Range requests, and without
those the browser refuses to seek inside the video — the page loads but the film
stays frozen on its first frame. This adds range support, which is all the
scroll-scrubbing needs.

    python serve.py            ->  http://127.0.0.1:8125

Opening index.html straight from disk (file://) works too, and needs none of this.
"""

import functools
import http.server
import os
import re
import socketserver

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 8125
HOST = "0.0.0.0"          # listen on the LAN too, so a phone can reach it


class RangeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        header = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not header or not os.path.isfile(path):
            return super().do_GET()

        size = os.path.getsize(path)
        match = re.match(r"bytes=(\d*)-(\d*)", header)
        if not match:
            return super().do_GET()

        start = int(match.group(1)) if match.group(1) else 0
        end = int(match.group(2)) if match.group(2) else size - 1
        end = min(end, size - 1)
        if start > end:
            self.send_error(416, "Requested range not satisfiable")
            return

        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            self.wfile.write(f.read(end - start + 1))


socketserver.TCPServer.allow_reuse_address = True
handler = functools.partial(RangeHandler, directory=ROOT)

def lan_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


with socketserver.ThreadingTCPServer((HOST, PORT), handler) as server:
    print("this machine   ->  http://127.0.0.1:%d" % PORT)
    ip = lan_ip()
    if ip:
        print("phone / LAN    ->  http://%s:%d" % (ip, PORT))
    print("ctrl-c to stop")
    server.serve_forever()
