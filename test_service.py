"""Minimal HTTP server for Render deploy test"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')
    def log_message(self, format, *args):
        pass

port = int(os.environ.get('PORT', 10000))
server = HTTPServer(('0.0.0.0', port), Handler)
print(f'Test server on port {port}')
server.serve_forever()
