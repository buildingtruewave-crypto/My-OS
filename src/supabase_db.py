"""Supabase bridge over the REST API - no psycopg2, no direct Postgres.
Talks to https://<project>.supabase.co/rest/v1 over HTTPS with the project
keys, exactly like the trading app's supabase-js client, so both apps always
agree. Credentials are read from the first source that exists:
  1. Streamlit secrets  -> .streamlit/secrets.toml [supabase] url + key
  2. Environment vars   -> SUPABASE_URL + SUPABASE_KEY / _SECRET_KEY
  3. Plain JSON file    -> data/supabase.json {"url","key","table"}
Every function fails open and diagnose() returns the exact HTTP reason so a
broken link is trivial to fix.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _cfg():
    url = ""
    key = ""
    table = "deriv_trades"
    try:
        s = st.secrets["supabase"]
        url = str(s.get("url", "") or "").strip()
        key = (str(s.get("key", "") or "").strip()
               or str(s.get("secret_key", "") or "").strip()
               or str(s.get("publishable_key", "") or "").strip())
        table = str(s.get("table", "deriv_trades")
                    or "deriv_trades").strip()
    except Exception:
        pass
    if not url:
        import os
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = (os.environ.get("SUPABASE_KEY", "").strip()
               or os.environ.get("SUPABASE_SECRET_KEY", "").strip()
               or os.environ.get("SUPABASE_PUBLISHABLE_KEY", "").strip())
        table = os.environ.get("SUPABASE_TABLE",
                               "deriv_trades").strip()
    if not url:
        try:
            f = _DATA_DIR / "supabase.json"
            if f.exists() and f.stat().st_size > 0:
                j = json.loads(f.read_text())
                url = str(j.get("url", "") or "").strip()
                key = (str(j.get("key", "") or "").strip()
                       or str(j.get("secret_key", "") or "").strip())
                table = str(j.get("table", "deriv_trades")
                            or "deriv_trades").strip()
        except Exception:
            pass
    return url, key, table


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
            url = url + ("&" if "?" in url else "?") \
                + urlencode(params)
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


def diagnose():
    url, key, table = _cfg()
    if not url:
        return False, ("No Supabase URL found - add [supabase] url to "
                       ".streamlit/secrets.toml (or data/supabase.json)")
    if not key:
        return False, ("No Supabase key found - paste the secret key "
                       "as 'key' under [supabase]")
    base = url.rstrip("/") + "/rest/v1/" + table
    status, text = _http("GET", base, _headers(key),
                         {"select": "id", "limit": "1"})
    if status == 200:
        return True, "Connected - " + table + " reachable"
    if status == 404:
        return False, ("Supabase reached but table '" + table
                       + "' is missing - run the one-time SQL once in "
                       "the Supabase SQL editor")
    if status in (401, 403):
        return False, ("Key rejected (HTTP " + str(status)
                       + ") - check the key in secrets")
    if status is None:
        return False, "Network error: " + str(text)[:160]
    return False, "HTTP " + str(status) + ": " + str(text)[:160]


def test_connection():
    return diagnose()


def fetch_trades(limit=1000):
    """Return (rows, message). rows is a list of dicts (newest handled by
    the caller's sort), [] when the table is empty or missing, None on a
    hard failure."""
    url, key, table = _cfg()
    if not url or not key:
        _ok, why = diagnose()
        return None, why
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
        return [], ("table '" + table + "' missing - run the one-time "
                    "SQL once in the Supabase SQL editor")
    if status in (401, 403):
        return None, "Key rejected (HTTP " + str(status) + ")"
    if status is None:
        return None, "Network error: " + str(text)[:160]
    return None, "HTTP " + str(status) + ": " + str(text)[:160]
