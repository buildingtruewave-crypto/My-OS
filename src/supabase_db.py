"""Supabase bridge over the REST API - no psycopg2, no direct Postgres.
Reads credentials from EVERY place they might live, in this order:
  1. Streamlit secrets  - [supabase] table OR top-level keys
  2. Process environment variables
  3. .env file          - the same one your other app uses
  4. data/supabase.json - plain fallback
Then talks to https://<project>.supabase.co/rest/v1 over HTTPS with the
project keys, exactly like the trading app's supabase-js client, so both
apps always agree. If the configured trades table doesn't exist, it probes
common table names so it finds wherever the other app writes. Every function
fails open and diagnose() returns the exact HTTP reason.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_TABLE_CACHE = [None]


# ---------------------------------------------------------------------------
# credential discovery
# ---------------------------------------------------------------------------
def _read_dotenv():
    """Parse .env files manually (no dependency). First occurrence wins."""
    out = {}
    candidates = []
    try:
        root = Path(__file__).resolve().parent.parent
        candidates.append(root / ".env")
        candidates.append(root / "src" / ".env")
        candidates.append(Path.cwd() / ".env")
    except Exception:
        pass
    for f in candidates:
        try:
            if not (f.exists() and f.stat().st_size > 0):
                continue
            for line in f.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.startswith("export "):
                    line = line[7:].strip()
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                # strip trailing inline comment for unquoted values
                if v and not v.startswith('"') and " #" in v:
                    v = v.split(" #", 1)[0].strip()
                if k and k not in out:
                    out[k] = v
        except Exception:
            continue
    return out


def _gather():
    vals = {}

    def put(k, v):
        v = str(v or "").strip()
        if v and not vals.get(k):
            vals[k] = v

    # 1) Streamlit secrets: [supabase] table, then top-level keys
    try:
        s = st.secrets
        try:
            sb = s["supabase"]
            for kk in ("url", "key", "secret_key", "publishable_key",
                       "table"):
                put(kk, sb.get(kk, ""))
        except Exception:
            pass
        for kk in ("SUPABASE_URL", "SUPABASE_KEY",
                   "SUPABASE_SECRET_KEY", "SUPABASE_PUBLISHABLE_KEY",
                   "SUPABASE_TABLE"):
            try:
                put(kk, s[kk])
            except Exception:
                pass
    except Exception:
        pass
    # 2) process environment
    for kk in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SECRET_KEY",
               "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_TABLE"):
        put(kk, os.environ.get(kk, ""))
    # 3) .env file (the one your other app uses)
    for k, v in _read_dotenv().items():
        put(k, v)
    # 4) data/supabase.json
    try:
        f = _DATA_DIR / "supabase.json"
        if f.exists() and f.stat().st_size > 0:
            j = json.loads(f.read_text())
            for kk in ("url", "key", "secret_key", "publishable_key",
                       "table"):
                put(kk, j.get(kk, ""))
    except Exception:
        pass
    return vals


def _cfg():
    v = _gather()
    url = (v.get("url") or v.get("SUPABASE_URL") or "").strip()
    key = (v.get("key") or v.get("secret_key")
           or v.get("SUPABASE_KEY") or v.get("SUPABASE_SECRET_KEY")
           or v.get("publishable_key")
           or v.get("SUPABASE_PUBLISHABLE_KEY") or "").strip()
    table = (v.get("table") or v.get("SUPABASE_TABLE")
             or "deriv_trades").strip() or "deriv_trades"
    return url, key, table


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def _headers(key):
    return {
        "apikey": key,
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _http(method, url, headers, params=None, body=None):
    """Return (status:int|None, text:str). Tries httpx then stdlib urllib."""
    if params:
        try:
            from urllib.parse import urlencode
            url = url + ("&" if "?" in url else "?") + urlencode(params)
        except Exception:
            pass
    data = body.encode("utf-8") if body else None
    try:
        import httpx
        with httpx.Client(timeout=30.0) as client:
            r = client.request(method, url, headers=headers, data=data)
            return r.status_code, r.text
    except Exception:
        pass
    try:
        from urllib import request as _req
        from urllib.error import HTTPError
        req = _req.Request(url, data=data, headers=headers,
                           method=method)
        try:
            with _req.urlopen(req, timeout=30.0) as resp:
                return resp.status, resp.read().decode("utf-8")
        except HTTPError as he:
            return he.code, he.read().decode("utf-8")
    except Exception as e:
        return None, str(e)


def _resolve_table(url, key, preferred):
    """Find the real trades table, even if the other app named it else."""
    if _TABLE_CACHE[0]:
        return _TABLE_CACHE[0]
    cands = [preferred] + [t for t in
                           ("deriv_trades", "trades", "bot_trades",
                            "deriv_bot_trades", "pulse_trades")
                           if t != preferred]
    base = url.rstrip("/") + "/rest/v1/"
    for t in cands:
        status, _text = _http("GET", base + t, _headers(key),
                              {"select": "id", "limit": "1"})
        if status == 200:
            _TABLE_CACHE[0] = t
            return t
    _TABLE_CACHE[0] = preferred
    return preferred


# ---------------------------------------------------------------------------
# public API (same signatures trade_intel / bots expect)
# ---------------------------------------------------------------------------
def diagnose():
    url, key, table = _cfg()
    if not url:
        return False, ("No Supabase URL found. Looked in: "
                       ".streamlit/secrets.toml, environment, .env, "
                       "data/supabase.json")
    if not key:
        return False, ("Supabase URL found but no key. Add the full "
                       "sb_secret_... (or sb_publishable_...) key.")
    table = _resolve_table(url, key, table)
    base = url.rstrip("/") + "/rest/v1/" + table
    status, text = _http("GET", base, _headers(key),
                         {"select": "id", "limit": "1"})
    if status == 200:
        return True, "Connected - " + table + " reachable"
    if status == 404:
        return False, ("Connected to Supabase but no trades table yet "
                       "(tried " + table + ")")
    if status in (401, 403):
        return False, ("Key rejected (HTTP " + str(status) + ") - use "
                       "the full unmasked key, not the •••• one")
    if status is None:
        return False, "Network error: " + str(text)[:160]
    return False, "HTTP " + str(status) + ": " + str(text)[:160]


def test_connection():
    return diagnose()


def fetch_trades(limit=1000):
    """Return (rows, message). rows is a list (newest handled by caller's
    sort), [] when the table is empty/missing, None on a hard failure."""
    url, key, table = _cfg()
    if not url or not key:
        _ok, why = diagnose()
        return None, why
    table = _resolve_table(url, key, table)
    base = url.rstrip("/") + "/rest/v1/" + table
    status, text = _http("GET", base, _headers(key),
                         {"select": "*", "limit": str(int(limit))})
    if status == 200:
        try:
            rows = json.loads(text)
            if isinstance(rows, list):
                return rows, "ok"
            return None, "Unexpected response shape"
        except Exception:
            return None, "Bad JSON from Supabase"
    if status == 404:
        return [], ("table '" + table + "' missing - waiting for the "
                    "trading app to write, or run the one-time SQL")
    if status in (401, 403):
        return None, ("Key rejected (HTTP " + str(status) + ") - use "
                      "the full unmasked key")
    if status is None:
        return None, "Network error: " + str(text)[:160]
    return None, "HTTP " + str(status) + ": " + str(text)[:160]
