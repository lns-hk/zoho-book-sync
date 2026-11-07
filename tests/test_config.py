import os
import stat
import sys

import pytest

from zoho_sync import config


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "SECRETS_FILE", tmp_path / "secrets.json")
    return tmp_path


def test_secrets_roundtrip_and_cleanup(cfg):
    assert config.get_secret("refresh_token") == ""
    config.set_secret("refresh_token", "r1")
    config.set_secret("client_secret", "s1")
    assert config.get_secret("refresh_token") == "r1" and config.get_secret("client_secret") == "s1"
    config.set_secret("refresh_token", "")
    assert config.get_secret("refresh_token") == "" and config.get_secret("client_secret") == "s1"
    config.set_secret("client_secret", "")
    assert not (cfg / "secrets.json").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
def test_secrets_file_is_user_only(cfg):
    config.set_secret("refresh_token", "r1")
    mode = stat.S_IMODE(os.stat(cfg / "secrets.json").st_mode)
    assert mode == 0o600


def test_corrupt_secrets_file_is_ignored(cfg):
    (cfg / "secrets.json").write_text("{not json")
    assert config.get_secret("refresh_token") == ""
    config.set_secret("refresh_token", "r2")
    assert config.get_secret("refresh_token") == "r2"


def test_company_cache_expiry_and_org(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "COMPANIES_FILE", tmp_path / "companies.json")
    assert config.load_companies("org1") is None
    config.save_companies("org1", ["A Ltd", "B Ltd"])
    assert config.load_companies("org1") == ["A Ltd", "B Ltd"]
    assert config.load_companies("org2") is None            # different Zoho org
    now = config.time.time()
    monkeypatch.setattr(config.time, "time", lambda: now + 25 * 3600)
    assert config.load_companies("org1") is None            # older than 24h


def test_apply_api_call_counts_and_resets_daily():
    t = config.time.mktime((2026, 11, 7, 23, 0, 0, 0, 0, -1))
    q = config.apply_api_call({}, {"limit": 1000, "remaining": 790, "reset_in": 600, "per_minute": 150}, now=t)
    assert (q["local_used"], q["limit"], q["remaining"], q["per_minute"]) == (1, 1000, 790, 150)
    assert q["reset_at"] == t + 600
    q = config.apply_api_call(q, {}, now=t + 60)            # call without headers still counts
    assert q["local_used"] == 2 and q["remaining"] == 790
    q = config.apply_api_call(q, {"remaining": 999}, now=t + 3600)  # next local day
    assert q["local_used"] == 1 and q["remaining"] == 999 and q["limit"] == 1000


def test_quota_file_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "QUOTA_FILE", tmp_path / "quota.json")
    assert config.load_quota() == {}
    config.save_quota({"local_used": 3})
    assert config.load_quota() == {"local_used": 3}
