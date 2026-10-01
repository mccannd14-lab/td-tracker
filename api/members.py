import json
import urllib.request
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            url = "https://api.oireachtas.ie/v1/members?chamber=dail&house_no=34&limit=200"

            with urllib.request.urlopen(url, timeout=15) as response:
                data = response.read()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({
                    "error": "Could not load Oireachtas member data",
                    "detail": str(e)
                }).encode()
            )
