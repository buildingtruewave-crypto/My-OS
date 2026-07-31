"""Formatting, colour and Nairobi-time helpers (no Streamlit dep)."""
from __future__ import annotations

import datetime as dt


def now_local():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("Africa/Nairobi"))
    except Exception:
        return dt.datetime.utcnow() + dt.timedelta(hours=3)


def today_local():
    return now_local().date()


def fmt_kes(x, sign=False):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "KSh 0"
    pre = "-" if x < 0 else ("+" if sign else "")
    return pre + "KSh " + format(abs(x), ",.0f")


def fmt_k(x, sign=False):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "0"
    pre = "-" if x < 0 else ("+" if sign else "")
    a = abs(x)
    if a >= 1000000:
        return pre + format(a / 1000000, ".1f") + "m"
    if a >= 1000:
        return pre + format(a / 1000, ".1f") + "k"
    return pre + format(a, ".0f")


def fmt_pct(x, sign=True, d=1):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "0.0%"
    pre = "-" if x < 0 else ("+" if sign else "")
    return pre + format(abs(x), ",." + str(d) + "f") + "%"


def fmt_num(x, d=1):
    try:
        return format(float(x), ",." + str(d) + "f")
    except (TypeError, ValueError):
        return "0"


def hexa(color, alpha):
    h = str(color).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
    except ValueError:
        r, g, b = 76, 141, 255
    return "rgba(%d,%d,%d,%s)" % (r, g, b, alpha)


def initials(name):
    p = [x for x in str(name).replace(".", " ").split() if x]
    if not p:
        return "?"
    if len(p) == 1:
        return p[0][:2].upper()
    return (p[0][0] + p[-1][0]).upper()


def slug(s):
    out = [ch for ch in str(s).lower() if ch.isalnum()]
    return "".join(out) or "x"


TONE = {"win": "tw-win", "loss": "tw-loss", "ink": "tw-ink",
        "accent": "tw-accent", "mute": "tw-mute",
        "jewel": "tw-jewel"}


def tone_cls(t):
    return TONE.get(t, "tw-ink")
