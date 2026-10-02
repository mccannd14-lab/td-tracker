import json
import re
import urllib.parse
import urllib.request
from html import unescape
from http.server import BaseHTTPRequestHandler


API_URL = (
    "https://api.oireachtas.ie/v1/members"
    "?chamber=dail&house_no=34&limit=200"
)


def fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TD-Tracker/1.0"
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def normalise(value):
    value = unescape(str(value or "")).lower().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def find_member(data, wanted_name):
    wanted = normalise(wanted_name)

    items = data.get("results", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return None

    best = None
    for item in items:
        obj = item.get("member", item) if isinstance(item, dict) else {}
        if not isinstance(obj, dict):
            continue

        names = [
            obj.get("fullName"),
            obj.get("name"),
            obj.get("showAs"),
            obj.get("memberName"),
        ]

        first = obj.get("firstName") or obj.get("first_name") or ""
        family = obj.get("familyName") or obj.get("surname") or obj.get("lastName") or ""
        combined = f"{first} {family}".strip()
        if combined:
            names.append(combined)

        for candidate in names:
            if normalise(candidate) == wanted:
                return obj

        # Also allow the requested name to be contained in the official display name.
        for candidate in names:
            c = normalise(candidate)
            if c and (wanted in c or c in wanted):
                best = obj

    return best


def find_uri(obj):
    if not isinstance(obj, dict):
        return ""

    candidates = [
        obj.get("uri"),
        obj.get("memberUri"),
        obj.get("profileUri"),
        obj.get("link"),
        obj.get("href"),
    ]

    for value in candidates:
        if isinstance(value, str) and "/members/member/" in value:
            return urllib.parse.urljoin("https://www.oireachtas.ie", value)

    return ""


def find_member_code(obj):
    if not isinstance(obj, dict):
        return ""
    for key in ("memberCode", "personCode", "id"):
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def first_email(html):
    patterns = [
        r'href=["\']mailto:([^"\']+)["\']',
        r'[\w.+-]+@oireachtas\.ie',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html, flags=re.I)
        if matches:
            value = unescape(matches[0]).strip()
            if "@" in value:
                return value

    return ""


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


def fetch_profile(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TD-Tracker/1.0"
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", "replace")


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            query = urllib.parse.parse_qs(
                urllib.parse.urlsplit(self.path).query
            )

            wanted_name = query.get("name", [""])[0].strip()

            if not wanted_name:
                raise ValueError("Missing member name")

            data = fetch_json(API_URL)
            member = find_member(data, wanted_name)

            if not member:
                raise ValueError("Member not found")

            profile_url = find_uri(member)

            if not profile_url:
                raise ValueError("Official member profile URL not found")

            html = fetch_profile(profile_url)

            result = {
                "ok": True,
                "profileUrl": profile_url,
                "email": first_email(html),
                "photo": first_image(html),
            }

            body = json.dumps(
                result,
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
