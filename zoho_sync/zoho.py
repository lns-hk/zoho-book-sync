"""Zoho OAuth + Books API client (stdlib only, so it packages cleanly on macOS and Windows)."""
from __future__ import annotations

import http.server
import json
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from .i18n import tr

DATA_CENTERS = {  # accounts host suffix -> api domain
    "com": "https://www.zohoapis.com",
    "eu": "https://www.zohoapis.eu",
    "in": "https://www.zohoapis.in",
    "com.au": "https://www.zohoapis.com.au",
    "jp": "https://www.zohoapis.jp",
    "ca": "https://www.zohoapis.ca",
    "sa": "https://www.zohoapis.sa",
    "com.cn": "https://www.zohoapis.com.cn",
}

SCOPES = ",".join([
    "ZohoBooks.estimates.READ", "ZohoBooks.invoices.READ", "ZohoBooks.creditnotes.READ",
    "ZohoBooks.salesorders.READ", "ZohoBooks.customerpayments.READ",
    "ZohoBooks.contacts.READ", "ZohoBooks.settings.READ",
])

# Daily Books API calls per organization, by plan (Zoho KB "per-day API limit").
# Only a fallback: the live X-Rate-Limit-* headers on each response are authoritative.
PLAN_DAILY_LIMITS = {"FREE": 1000, "STANDARD": 2000, "PROFESSIONAL": 5000,
                     "PREMIUM": 10000, "ELITE": 10000, "ULTIMATE": 10000}


def plan_daily_limit(plan_name: str) -> int | None:
    plan = (plan_name or "").upper()
    return next((v for k, v in PLAN_DAILY_LIMITS.items() if k in plan), None)


def parse_rate_headers(headers) -> dict:
    """X-Rate-Limit-* headers -> {limit, remaining, reset_in, per_minute}; missing keys omitted."""
    out = {}
    for key, name in (("limit", "X-Rate-Limit-Limit"), ("remaining", "X-Rate-Limit-Remaining"),
                      ("reset_in", "X-Rate-Limit-Reset"), ("per_minute", "X-User-Access-Limit")):
        try:
            v = headers.get(name) if headers is not None else None
            if v is not None:
                out[key] = int(v)
        except (TypeError, ValueError):
            pass
    return out


REDIRECT_PORT = 53682
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/callback"


class ZohoError(Exception):
    pass


def _post(url: str, params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(url, data, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:
            raise ZohoError(f"HTTP {e.code}") from e


def exchange_code(dc: str, client_id: str, client_secret: str, code: str,
                  redirect_uri: str | None = None, accounts_server: str | None = None) -> dict:
    """Swap a one-time grant code for tokens. Returns dict with refresh_token, api_domain, dc."""
    server = accounts_server or f"https://accounts.zoho.{dc}"
    params = {"code": code.strip(), "client_id": client_id.strip(),
              "client_secret": client_secret.strip(), "grant_type": "authorization_code"}
    if redirect_uri:
        params["redirect_uri"] = redirect_uri
    d = _post(f"{server}/oauth/v2/token", params)
    if "refresh_token" not in d:
        msg = d.get("error", "unknown error")
        if msg == "invalid_code":
            msg = tr("zerr.invalid_code")
        raise ZohoError(tr("zerr.auth_failed", error=msg))
    if accounts_server:  # browser flow tells us which DC the user lives in
        dc = accounts_server.split("accounts.zoho.", 1)[-1].rstrip("/")
    return {"refresh_token": d["refresh_token"], "access_token": d.get("access_token"),
            "api_domain": d.get("api_domain") or DATA_CENTERS.get(dc, DATA_CENTERS["com"]), "dc": dc}


def browser_login(dc: str, client_id: str, client_secret: str, timeout: int = 300) -> dict:
    """OAuth via the system browser with a one-shot localhost callback.

    Needs a Zoho *Server-based* client whose redirect URI is REDIRECT_URI.
    """
    state = secrets.token_urlsafe(16)
    result: dict = {}
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if not self.path.startswith("/callback"):
                self.send_response(404); self.end_headers(); return
            if q.get("state", [""])[0] != state:
                result["error"] = "state mismatch"
            elif "error" in q:
                result["error"] = q["error"][0]
            else:
                result["code"] = q.get("code", [""])[0]
                result["accounts_server"] = q.get("accounts-server", [None])[0]
            body = f"<h2>{tr('zerr.callback_ok', app=tr('app.name'))}</h2>" if "code" in result \
                else f"<h2>{tr('zerr.auth_failed', error=result.get('error'))}</h2>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())
            done.set()

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", REDIRECT_PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f"https://accounts.zoho.{dc}/oauth/v2/auth?" + urllib.parse.urlencode({
            "scope": SCOPES, "client_id": client_id, "response_type": "code",
            "access_type": "offline", "prompt": "consent",
            "redirect_uri": REDIRECT_URI, "state": state})
        webbrowser.open(url)
        if not done.wait(timeout):
            raise ZohoError(tr("zerr.login_timeout"))
    finally:
        srv.shutdown()
        srv.server_close()
    if "error" in result:
        raise ZohoError(tr("zerr.auth_failed", error=result["error"]))
    return exchange_code(dc, client_id, client_secret, result["code"],
                         redirect_uri=REDIRECT_URI, accounts_server=result.get("accounts_server"))


class BooksClient:
    def __init__(self, *, dc: str, client_id: str, client_secret: str, refresh_token: str,
                 api_domain: str | None = None, org_id: str | None = None, observer=None):
        self.dc, self.client_id, self.client_secret = dc, client_id, client_secret
        self.refresh_token = refresh_token
        self.base = (api_domain or DATA_CENTERS.get(dc, DATA_CENTERS["com"])) + "/books/v3"
        self.org_id = org_id
        self._token: str | None = None
        self._token_exp = 0.0
        self.calls = 0  # API calls made by this client (for the usage counter)
        self.observer = observer  # called with parse_rate_headers(...) after every Books API call

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        d = _post(f"https://accounts.zoho.{self.dc}/oauth/v2/token", {
            "refresh_token": self.refresh_token, "client_id": self.client_id,
            "client_secret": self.client_secret, "grant_type": "refresh_token"})
        if "access_token" not in d:
            raise ZohoError(tr("zerr.session_expired", error=d.get("error", "unknown")))
        self._token, self._token_exp = d["access_token"], time.time() + int(d.get("expires_in", 3600))
        return self._token

    def get(self, path: str, *, raw: bool = False, with_org: bool = True, **params):
        if with_org and self.org_id:
            params.setdefault("organization_id", self.org_id)
        url = f"{self.base}/{path}?{urllib.parse.urlencode(params)}"
        for attempt in range(4):
            req = urllib.request.Request(url, headers={"Authorization": "Zoho-oauthtoken " + self._access_token()})
            try:
                self.calls += 1
                with urllib.request.urlopen(req, timeout=60) as r:
                    self._observe(r.headers)
                    return r.read() if raw else json.load(r)
            except urllib.error.HTTPError as e:
                self._observe(e.headers)
                if e.code == 429 and attempt < 3:  # rate limited: back off and retry
                    time.sleep(5 * (attempt + 1)); continue
                if e.code == 401 and attempt == 0:
                    self._token = None; continue
                try:
                    msg = json.load(e).get("message", "")
                except Exception:
                    msg = ""
                if e.code == 429:
                    raise ZohoError(tr("zerr.rate_limited")) from e
                if e.code in (401, 403) and "not authorized" in msg.lower():
                    raise ZohoError(tr("zerr.forbidden")) from e
                raise ZohoError(tr("zerr.api", code=e.code, message=msg)) from e
            except urllib.error.URLError as e:
                if attempt < 2:
                    time.sleep(3); continue
                raise ZohoError(tr("zerr.unreachable", error=e.reason)) from e
        raise ZohoError(tr("zerr.retry_failed"))

    def _observe(self, headers):
        if self.observer:
            try:
                self.observer(parse_rate_headers(headers))
            except Exception:
                pass  # usage display must never break a sync

    def quota_probe(self) -> None:
        """One cheap call whose response carries the org's X-Rate-Limit-* headers (seen by the observer)."""
        self.get(f"organizations/{self.org_id}", with_org=False, organization_id=self.org_id)

    def organizations(self) -> list[dict]:
        return self.get("organizations", with_org=False).get("organizations", [])

    def list_page(self, plural: str, page: int = 1, per_page: int = 200, **filters) -> tuple[list[dict], bool]:
        d = self.get(plural, page=page, per_page=per_page,
                     sort_column="last_modified_time", sort_order="D", **filters)
        return d.get(plural, []), bool(d.get("page_context", {}).get("has_more_page"))

    def pdf(self, plural: str, doc_id: str) -> bytes:
        data = self.get(f"{plural}/{doc_id}", raw=True, accept="pdf")
        if not data.startswith(b"%PDF"):
            raise ZohoError(tr("zerr.no_pdf"))
        return data
