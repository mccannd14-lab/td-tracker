import json
import re
import urllib.parse
import urllib.request
from html import unescape
from http.server import BaseHTTPRequestHandler


def first_email(html):
    matches = re.findall(r'href=["\']mailto:([^"\']+)["\']', html, flags=re.I)
    return unescape(matches[0]).strip() if matches else ""


def first_image(html):
    # Oireachtas pages expose the member photo as og:image.
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.I)
        if match:
            url = unescape(match.group(1)).strip()
            return urllib.parse.urljoin("https://www.oireachtas.ie", url)
    return ""


def clean_name(name):
    # Oireachtas member URLs use the display name with spaces changed to hyphens.
    name = unescape(name).strip()
    name = re.sub(r"[^0-9A-Za-zÀ-ÖØ-öø-ÿ' -]", "", name)
    name = name.replace("'", "")
    name = re.sub(r"\s+", "-", name)
    return name


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            qs = urllib.parse.parse_qs(
                urllib.parse.urlsplit(self.path).query
            )
            name = qs.get("name", [""])[0]
            member_code = qs.get("memberCode", [""])[0]

            if not name:
                raise ValueError("Missing member name")

            slug = clean_name(name)

            if member_code:
                profile_path = f"/en/members/member/{slug}.{member_code}/"
            else:
                profile_path = f"/en/members/member/{slug}/"

            profile_url = "https://www.oireachtas.ie" + profile_path

            request = urllib.request.Request(
                profile_url,
                headers={
                    "User-Agent": "TD-Tracker/1.0 (+https://td-tracker-alpha.vercel.app)"
                },
            )

            with urllib.request.urlopen(request, timeout=15) as response:
                html = response.read().decode("utf-8", "replace")

            result = {
                "ok": True,
                "profileUrl": profile_url,
                "email": first_email(html),
                "photo": first_image(html),
            }

            body = json.dumps(result, ensure_ascii=False).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        except Exception as exc:
            body = json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                },
                ensure_ascii=False,
            ).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
