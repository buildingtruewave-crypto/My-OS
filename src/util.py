"""Formatting + colour helpers (no Streamlit dependency)."""
from __future__ import annotations


def fmt_money(x, sign=False):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "$0.00"
    pre = "-" if x < 0 else ("+" if sign else "")
    return f"{pre}${abs(x):,.2f}"


def fmt_pct(x, sign=True, d=1):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "0.0%"
    pre = "-" if x < 0 else ("+" if sign else "")
    return f"{pre}{abs(x):.{d}f}%"


def fmt_num(x, d=1):
    try:
        return f"{float(x):,.{d}f}"
    except (TypeError, ValueError):
        return "0"


def hexa(color, alpha):
    h = color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        r, g, b = 76, 141, 255
    return f"rgba({r},{g},{b},{alpha})"


def initials(name):
    p = [x for x in name.replace(".", " ").split() if x]
    if not p:
        return "?"
    return (p[0][0] + (p[-1][0] if len(p) > 1 else p[0][1])).upper()


def slug(s):
    out = []
    for ch in str(s).lower():
        out.append(ch if ch.isalnum() else "_")
    return "".join(out).strip("_") or "x"


TONE = {"win": "tw-win", "loss": "tw-loss", "ink": "tw-ink",
        "accent": "tw-accent", "mute": "tw-mute", "jewel": "tw-jewel"}


def tone_cls(t):
    return TONE.get(t, "tw-ink")
