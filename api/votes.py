import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            params = urllib.parse.urlencode({
                "chamber_type": "house",
                "date_start": "2025-01-01",
                "date_end": "2026-10-01",
                "skip": "0",
                "limit": "50"
            })

            url = "https://api.oireachtas.ie/v1/divisions?" + params

            with urllib.request.urlopen(url, timeout=20) as response:
                data = response.read()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(
                json.dumps({
                    "error": "Could not load Oireachtas vote data",
                    "detail": str(e)
                }).encode()
            )
