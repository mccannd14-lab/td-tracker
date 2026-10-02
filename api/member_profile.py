import json
import re
import urllib.parse
import urllib.request
from html import unescape
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler


DIRECTORY_URL = "https://www.oireachtas.ie/en/members/tds/"


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_href = ""
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            attrs = dict(attrs)
            href = attrs.get("href", "")
            self.current_href = href
            self.current_text = []

    def handle_data(self, data):
        if self.current_href:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current_href:
            text = " ".join(self.current_text)
            self.links.append((text, self.current_href))
            self.current_href = ""
            self.current_text = []


def fetch(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TD-Tracker/1.0"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", "replace")


def normalise(value):
    value = unescape(str(value or "")).lower().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def find_profile_url(name):
    html = fetch(DIRECTORY_URL)
    parser = LinkParser()
    parser.feed(html)

    wanted = normalise(name)

    # Exact match first.
    for text, href in parser.links:
        if "/en/members/member/" in href and normalise(text) == wanted:
            return urllib.parse.urljoin(
                "https://www.oireachtas.ie", href
            )

    # Then allow "Ciarán Ahern" to appear in a longer link label.
    for text, href in parser.links:
        if "/en/members/member/" in href:
            label = normalise(text)
            if wanted and wanted in label:
                return urllib.parse.urljoin(
                    "https://www.oireachtas.ie", href
                )

    raise ValueError("Official member profile not found")


def first_email(html):
    matches = re.findall(
        r'href=["\']mailto:([^"\']+)["\']',
        html,
        flags=re.I
    )
    if matches:
        return unescape(matches[0]).strip()

    matches = re.findall(
        r'[\w.+-]+@oireachtas\.ie',
        html,
        flags=re.I
    )
    return matches[0] if matches else ""


def first_image(html):
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, flags=re.I)
        if match:
            return urllib.parse.urljoin(
                "https://www.oireachtas.ie",
                unescape(match.group(1)).strip()
            )

    return ""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            query = urllib.parse.parse_qs(
                urllib.parse.urlsplit(self.path).query
            )
            name = query.get("name", [""])[0].strip()

            if not name:
                raise ValueError("Missing member name")

            profile_url = find_profile_url(name)
            profile_html = fetch(profile_url)

            result = {
                "ok": True,
                "profileUrl": profile_url,
                "email": first_email(profile_html),
                "photo": first_image(profile_html),
            }

            body = json.dumps(
                result,
                ensure_ascii=False
            ).encode("utf-8")

        except Exception as exc:
            body = json.dumps(
                {
                    "ok": False,
                    "email": "",
                    "photo": "",
                    "profileUrl": "",
                    "error": str(exc),
                },
                ensure_ascii=False
            ).encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )
        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )
        self.end_headers()
        self.wfile.write(body)
