"""Supabase (PostgreSQL) bridge for PULSE.
Reads credentials from .streamlit/secrets.toml under [supabase]. Tries the
direct connection first, then an optional pooler, across two SSL modes, and
surfaces the REAL error through diagnose() so a failed link is easy to fix.
Every function fails open - a database problem never breaks a page.
"""
from __future__ import annotations

import streamlit as st

try:
    import psycopg2
    _HAS_PSYCOPG = True
except Exception:
    psycopg2 = None
    _HAS_PSYCOPG = False


def _cfg():
    try:
        s = st.secrets["supabase"]
    except Exception:
        return None

    def g(key, default=""):
        try:
            v = s[key]
            return default if v is None else v
        except Exception:
            return default

    def as_int(v, default):
        try:
            return int(v)
        except Exception:
            return default

    return {
        "host": str(g("host", "")).strip(),
        "port": as_int(g("port", 5432), 5432),
        "user": str(g("user", "postgres")).strip() or "postgres",
        "password": str(g("password", "")),
        "dbname": str(g("dbname", "postgres")).strip() or "postgres",
        "pooler_host": str(g("pooler_host", "")).strip(),
        "pooler_port": as_int(g("pooler_port", 5432), 5432),
        "pooler_user": str(g("pooler_user", "")).strip(),
    }


def _candidate_configs(cfg):
    """Connection attempts in order: direct, then pooler (if configured)."""
    out = []
    if cfg["host"] and cfg["password"]:
        out.append({
            "label": "direct",
            "host": cfg["host"],
            "port": cfg["port"],
            "user": cfg["user"],
            "password": cfg["password"],
            "dbname": cfg["dbname"],
        })
    if cfg["pooler_host"] and cfg["password"]:
        out.append({
            "label": "pooler",
            "host": cfg["pooler_host"],
            "port": cfg["pooler_port"],
            "user": cfg["pooler_user"] or cfg["user"],
            "password": cfg["password"],
            "dbname": cfg["dbname"],
        })
    return out


def _try_connect(conf):
    """Try one config across SSL modes. Return (conn, error)."""
    last_err = "unknown error"
    for sslmode in ("require", "prefer"):
        try:
            conn = psycopg2.connect(
                host=conf["host"],
                port=int(conf["port"]),
                user=conf["user"],
                password=conf["password"],
                dbname=conf["dbname"],
                sslmode=sslmode,
                connect_timeout=10,
            )
            return conn, None
        except Exception as e:
            last_err = "%s (%s)" % (str(e), sslmode)
    return None, last_err


def get_connection():
    """Return an open connection or None. Tries direct then pooler."""
    if not _HAS_PSYCOPG:
        return None
    cfg = _cfg()
    if not cfg:
        return None
    for conf in _candidate_configs(cfg):
        conn, _err = _try_connect(conf)
        if conn is not None:
            return conn
    return None


def diagnose():
    """Return (ok, message). On failure the message carries the real error."""
    if not _HAS_PSYCOPG:
        return False, ("psycopg2 is not installed - run "
                       "'pip install psycopg2-binary'")
    cfg = _cfg()
    if not cfg:
        return False, "No [supabase] block in .streamlit/secrets.toml"
    if not cfg["host"] and not cfg["pooler_host"]:
        return False, "No host set - add host (or pooler_host)."
    if not cfg["password"]:
        return False, "Password is empty in secrets.toml."
    errors = []
    for conf in _candidate_configs(cfg):
        conn, err = _try_connect(conf)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            return True, ("Connected via %s (%s:%s)"
                          % (conf["label"], conf["host"],
                             conf["port"]))
        errors.append("%s -> %s" % (conf["label"], err))
    return False, " | ".join(errors)


def test_connection():
    return diagnose()


def fetch_all(sql, params=None):
    conn = get_connection()
    if conn is None:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            cols = [d[0] for d in cur.description] \
                if cur.description else []
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def execute(sql, params=None):
    conn = get_connection()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass
