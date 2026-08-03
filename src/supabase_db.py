"""Supabase bridge over the REST API - no psycopg2, no direct Postgres.
Reads credentials from the first source that exists (secrets -> env -> .env
-> data/supabase.json), then talks to https://<project>.supabase.co/rest/v1
over HTTPS with the project keys, exactly like the trading app's client.
Table discovery never assumes column names (probes use select=*). Positive
table hits are cached for 2 minutes; negatives are never cached. Every
function fails open so a database problem never breaks a page.
"""
from __future__ import annotations

import json
import os
import time as _time
from pathlib import Path

import streamlit as st

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_EXIST = {}
_EXIST_TTL = 120.0


def _gather():
    vals = {}

    def put(k, v):
        v = str(v or "").strip()
        if v and not vals.get(k):
            vals[k] = v

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
    for kk in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SECRET_KEY",
               "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_TABLE"):
        put(kk, os.environ.get(kk, ""))
    for f in (_DATA_DIR.parent / ".env", Path.cwd() / ".env"):
        try:
            if f.exists() and f.stat().st_size > 0:
                for line in f.read_text().splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") \
                            or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line[7:].strip()
                    k, _, v = line.partition("=")
                    put(k.strip(), v.strip().strip('"').strip("'"))
        except Exception:
            continue
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
             or "trades").strip() or "trades"
    return url, key, table


def _headers(key):
    return {
        "apikey": key,
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _http(method, url, headers, params=None, body=None):
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


def clear_cache():
    _EXIST.clear()


def table_exists(table):
    now = _time.time()
    hit = _EXIST.get(table)
    if hit and hit[0] and (now - hit[1]) < _EXIST_TTL:
        return True
    url, key, _t = _cfg()
    if not url or not key:
        return False
    status, _text = _http("GET", url.rstrip("/") + "/rest/v1/" + table,
                          _headers(key), {"select": "*", "limit": "1"})
    ok = status == 200
    if ok:
        _EXIST[table] = (True, now)
    else:
        _EXIST.pop(table, None)
    return ok


def first_existing(candidates):
    for t in candidates:
        if table_exists(t):
            return t
    return None


def diagnose():
    url, key, table = _cfg()
    if not url:
        return False, ("No Supabase URL found. Looked in: "
                       ".streamlit/secrets.toml, environment, .env, "
                       "data/supabase.json")
    if not key:
        return False, ("Supabase URL found but no key. Add the full "
                       "sb_secret_... (or sb_publishable_...) key.")
    found = []
    for t in ("trades", "deriv_trade_research", "deriv_venture_advice"):
        if table_exists(t):
            found.append(t)
    if found:
        return True, ("Connected - tables: " + ", ".join(found)
                      + " @ " + url.replace("https://", ""))
    return False, ("Connected to " + url + " but no known tables yet "
                   "- waiting for the trading app to write.")


def test_connection():
    return diagnose()


def fetch_rows(table, limit=1000, order=None):
    """Return (rows, message). rows is a list (caller sorts), [] when the
    table is empty/missing, None on a hard failure."""
    url, key, _t = _cfg()
    if not url or not key:
        _ok, why = diagnose()
        return None, why
    base = url.rstrip("/") + "/rest/v1/" + table
    params = {"select": "*", "limit": str(int(limit))}
    if order:
        params["order"] = order
    status, text = _http("GET", base, _headers(key), params)
    if status == 400 and order:
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
        return [], "table '" + table + "' missing"
    if status in (401, 403):
        return None, "Key rejected (HTTP " + str(status) + ")"
    if status is None:
        return None, "Network error: " + str(text)[:160]
    return None, "HTTP " + str(status) + ": " + str(text)[:160]


def fetch_trades(limit=4000):
    t = first_existing(["trades", "deriv_trades", "bot_trades"])
    if t is None:
        return [], "no trades table yet - waiting for the trading app"
    return fetch_rows(t, limit)
