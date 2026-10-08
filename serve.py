#!/usr/bin/env python3
"""
serve.py
Lightweight local HTTP development server for EBSBank
"""

import http.server
import socketserver
import os
import sys

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Enable CORS and caching headers for local testing
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

def run_server():
    global PORT
    while PORT < 8095:
        try:
            with socketserver.TCPServer(("", PORT), Handler) as httpd:
                print("=" * 60)
                print(f" EBSBank Local Development Server Started")
                print(f" Directory: {DIRECTORY}")
                print(f" Local URL: http://localhost:{PORT}/index.html")
                print(f" 3D Viewer: http://localhost:{PORT}/viewer.html")
                print(f" Explorer:   http://localhost:{PORT}/explorer.html")
                print(f" Importer:   http://localhost:{PORT}/importer.html")
                print("=" * 60)
                print("Press Ctrl+C to stop the server.")
                httpd.serve_forever()
        except OSError as e:
            if e.errno == 48: # Address already in use
                PORT += 1
            else:
                raise e

if __name__ == "__main__":
    run_server()
