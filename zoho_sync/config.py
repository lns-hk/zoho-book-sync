"""Settings and secrets, both stored only in the app's own per-user folder (no OS keychain, by design)."""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir, user_log_dir

APP_NAME = "ZohoBookSync"
CONFIG_DIR = Path(user_config_dir(APP_NAME, appauthor=False))
DATA_DIR = Path(user_data_dir(APP_NAME, appauthor=False))
LOG_DIR = Path(user_log_dir(APP_NAME, appauthor=False))
SETTINGS_FILE = CONFIG_DIR / "settings.json"
STATE_FILE = DATA_DIR / "state.json"
COMPANIES_FILE = DATA_DIR / "companies.json"  # cached Zoho customer company names
COMPANIES_MAX_AGE = 24 * 3600
QUOTA_FILE = DATA_DIR / "quota.json"  # last Zoho X-Rate-Limit-* values + this computer's call count today


def default_output_root() -> str:
    home = Path.home()
    for cand in sorted((home / "Library" / "CloudStorage").glob("OneDrive*")) + \
            [Path(os.environ.get("OneDrive", "")), home / "OneDrive"]:
        if str(cand) not in ("", ".") and cand.is_dir():
            return str(cand / "Zoho Books")
    return str(home / "Documents" / "Zoho Books")


@dataclass
class Partner:
    name: str                       # folder name, e.g. "ABC Partner"
    companies: list[str] = field(default_factory=list)  # Zoho company names routed to this folder


@dataclass
class Settings:
    # connection
    dc: str = "com"
    client_id: str = ""
    api_domain: str = ""
    org_id: str = ""
    org_name: str = ""
    plan_name: str = ""             # Zoho Books plan, e.g. FREE (read on connect)
    auth_mode: str = "browser"      # browser | manual
    # what to sync
    doc_types: list[str] = field(default_factory=lambda: ["estimates", "invoices"])
    skip_statuses: list[str] = field(default_factory=lambda: ["draft", "void"])
    since_date: str = ""            # YYYY-MM-DD; never-seen docs dated before this are ignored by routine sync
    partner_only: bool = False      # True: only companies listed under a partner are synced
    partners: list[Partner] = field(default_factory=list)
    # where / how
    output_root: str = field(default_factory=default_output_root)
    path_template: str = "{partner}/{type}/{number}.pdf"
    conflict: str = "version"       # version | overwrite | skip
    # automation
    auto_sync: bool = False
    interval_min: int = 10
    start_at_login: bool = False
    notify: bool = True
    # interface
    language: str = ""              # "" = follow the system; else en | zh-Hans | zh-Hant | ja

    @property
    def connected(self) -> bool:
        return bool(self.client_id and self.org_id and get_secret("refresh_token"))

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        tmp = SETTINGS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, SETTINGS_FILE)

    @classmethod
    def load(cls) -> "Settings":
        if not SETTINGS_FILE.exists():
            return cls()
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        known = {k: v for k, v in raw.items() if k in cls.__dataclass_fields__}
        known["partners"] = [Partner(**p) for p in known.get("partners", [])]
        return cls(**known)


SECRETS_FILE = CONFIG_DIR / "secrets.json"  # client secret + refresh token; user-only permissions


def _read_secrets() -> dict:
    try:
        return json.loads(SECRETS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def get_secret(name: str) -> str:
    return _read_secrets().get(name, "")


def set_secret(name: str, value: str) -> None:
    data = _read_secrets()
    if value:
        data[name] = value
    else:
        data.pop(name, None)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not data:
        SECRETS_FILE.unlink(missing_ok=True)
        return
    tmp = SECRETS_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)  # never world-readable, even briefly
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.chmod(tmp, 0o600)
    os.replace(tmp, SECRETS_FILE)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"docs": {}}


def save_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def load_companies(org_id: str) -> list[str] | None:
    """Cached company names for this org, or None if missing / other org / older than 24h."""
    try:
        d = json.loads(COMPANIES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if d.get("org_id") != org_id or time.time() - d.get("fetched_at", 0) > COMPANIES_MAX_AGE:
        return None
    return d.get("companies")


def save_companies(org_id: str, companies: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = COMPANIES_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"org_id": org_id, "fetched_at": time.time(), "companies": companies},
                              ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, COMPANIES_FILE)


def load_quota() -> dict:
    try:
        return json.loads(QUOTA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_quota(q: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = QUOTA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(q), encoding="utf-8")
    os.replace(tmp, QUOTA_FILE)


def apply_api_call(q: dict, rate: dict, now: float | None = None) -> dict:
    """Count one Books API call made by this computer and merge Zoho's reported limits.

    local_used resets at local midnight; limit/remaining come from Zoho and are org-wide.
    """
    now = time.time() if now is None else now
    today = time.strftime("%Y-%m-%d", time.localtime(now))
    if q.get("date") != today:
        q = {**q, "date": today, "local_used": 0}
    q["local_used"] = q.get("local_used", 0) + 1
    if "limit" in rate:
        q["limit"] = rate["limit"]
    if "remaining" in rate:
        q["remaining"] = rate["remaining"]
        q["updated_at"] = now
    if "reset_in" in rate:
        q["reset_at"] = now + rate["reset_in"]
    if "per_minute" in rate:
        q["per_minute"] = rate["per_minute"]
    return q
