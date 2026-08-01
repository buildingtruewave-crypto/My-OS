"""HTML / SVG components. The EKG is the signature heartbeat; the client
stepper and chips read the pipeline live, so renaming stages re-skins every
card with no code change. Terminal clients carry an Outcome line.

The *render* helpers at the bottom (log_row, *_log_rows, memory_line, the
upgraded kv / client_card / journal_card / history_html) are what make saved
entries look premium on every refresh - directional glow, receipt-style
reference chips (M-Pesa brand-coded, no '#' artifacts), warm-orange outflows,
bright signed figures - derived from the stored data, so the look is permanent.
"""
from __future__ import annotations

import calendar as _cal
import datetime as _dt
import html
import math

from . import data as D
from . import util as U
from .data import TAG_COLORS

_SVG_OPEN = (
    '<svg viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
)


def _svg(inner):
    return _SVG_OPEN + inner + '</svg>'


ICONS = {
    "star": _svg('<polygon points="M12 3 14.6 8.6 21 9.3 16.2 13.6 '
                 '17.6 20 12 16.7 6.4 20 7.8 13.6 3 9.3 9.4 8.6z"/>'),
    "pulse": _svg('<polyline points="M3 12h3l2 6 4-13 2 7h4"/>'),
    "check": _svg('<polyline points="M20 6 9 17l-5-5"/>'),
    "trend": _svg('<polyline points="M3 17l5-5 4 4 8-9"/>'
                  '<polyline points="M16 7h5v5"/>'),
    "flame": _svg('<path d="M12 2c2 4 6 6 6 10a6 6 0 1 1-12 0'
                  'c0-2 1-3 2-4 1 2 2 2 2 2 0-3-1-5 2-8z"/>'),
    "grid": _svg('<rect x="3" y="3" width="7" height="7" rx="1"/>'
                 '<rect x="14" y="3" width="7" height="7" rx="1"/>'
                 '<rect x="3" y="14" width="7" height="7" rx="1"/>'
                 '<rect x="14" y="14" width="7" height="7" rx="1"/>'),
    "x": _svg('<line x1="6" y1="6" x2="18" y2="18"/>'
              '<line x1="18" y1="6" x2="6" y2="18"/>'),
    "edit": _svg('<path d="M4 20h4l10-10-4-4L4 16z"/>'
                 '<line x1="13" y1="6" x2="17" y2="10"/>'),
    "target": _svg('<circle cx="12" cy="12" r="8"/>'
                   '<circle cx="12" cy="12" r="4"/>'
                   '<circle cx="12" cy="12" r="1"/>'),
    "flag": _svg('<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>'),
    "list": _svg('<path d="M4 6h.01M4 12h.01M4 18h.01'
                 'M8 6h12M8 12h12M8 18h12"/>'),
    "hash": _svg('<path d="M9 3v18M15 3v18M3 9h18M3 15h18"/>'),
    "bolt": _svg('<polygon points="M13 2 4 14h6l-1 8 9-12h-6z"/>'),
    "clock": _svg('<circle cx="12" cy="12" r="9"/>'
                  '<polyline points="M12 7v5l3 2"/>'),
    "phone": _svg('<path d="M22 16.9v3a2 2 0 0 1-2.2 2'
                  ' 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6'
                  'A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3'
                  'a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.9'
                  'a2 2 0 0 1-.4 2.1L8.1 10a16 16 0 0 0 6 6'
                  'l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.9.6 2.9.7'
                  'a2 2 0 0 1 1.6 2z"/>'),
    "cash": _svg('<rect x="2" y="6" width="20" height="12" rx="2"/>'
                 '<circle cx="12" cy="12" r="3"/>'),
    "lock": _svg('<rect x="4" y="11" width="16" height="10" rx="2"/>'
                 '<path d="M8 11V7a4 4 0 0 1 8 0v4"/>'),
    "bot": _svg('<rect x="4" y="9" width="16" height="11" rx="2"/>'
                '<path d="M12 9V5"/><circle cx="12" cy="4" r="1"/>'
                '<path d="M9 14h.01M15 14h.01"/>'),
    "scale": _svg('<circle cx="12" cy="13" r="8"/>'
                  '<path d="M12 13l3.5-3.5"/>'),
    "users": _svg('<circle cx="9" cy="8" r="3"/>'
                  '<path d="M3 20c0-3 3-5 6-5s6 2 6 5"/>'
                  '<circle cx="17" cy="9" r="2.5"/>'
                  '<path d="M16 15.3c2.6.4 5 2 5 4.7"/>'),
    "cal": _svg('<rect x="3" y="5" width="18" height="16" rx="2"/>'
                '<path d="M8 3v4M16 3v4M3 10h18"/>'),
}

WAVE = (
    '<svg width="30" height="30" viewBox="0 0 32 32" fill="none">'
    '<rect width="32" height="32" rx="9" '
    'fill="#0E1422" stroke="#1C2740"/>'
    '<path d="M5 19c3 0 3-4 6-4s3 4 6 4 3-4 6-4" '
    'stroke="#4C8DFF" stroke-width="2.2" stroke-linecap="round"/>'
    '<path d="M5 13c3 0 3-3 6-3s3 3 6 3 3-3 6-3" '
    'stroke="#34D399" stroke-width="1.6" '
    'stroke-linecap="round" opacity=".7"/></svg>'
)

WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
_HEAT = {"Hot": "#F0556B", "Warm": "#F5B544", "Cold": "#7C8AA5"}
MOOD_COLOR = {"drained": "#F0556B", "flat": "#7C8AA5",
              "steady": "#F5B544", "sharp": "#34D399",
              "on fire": "#D946EF"}

# Inline reference marks. The M-Pesa mark is a clean brand-coded monogram
# drawn in SVG (not a hot-linked trademarked asset) so it never breaks; the
# barcode mark makes a generic reference read like a real, scannable code.
MPESA_MARK = (
    '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">'
    '<rect width="16" height="16" rx="4" fill="#4CAF50"/>'
    '<polyline points="4,12 4,5 8,9 12,5 12,12" fill="none" '
    'stroke="#fff" stroke-width="1.7" stroke-linecap="round" '
    'stroke-linejoin="round"/></svg>'
)
BARCODE_MARK = (
    '<svg viewBox="0 0 12 12" aria-hidden="true" focusable="false">'
    '<g fill="currentColor">'
    '<rect x="1" y="2" width="1.4" height="8"/>'
    '<rect x="3.4" y="2" width="2.2" height="8"/>'
    '<rect x="6.6" y="2" width="1.2" height="8"/>'
    '<rect x="8.8" y="2" width="1.6" height="8"/></g></svg>'
)


def _icon(name):
    return ICONS.get(name, name)


def _tag_color(tag):
    return TAG_COLORS.get(tag, "#7C8AA5")


def is_mpesa(pid, name):
    """True when a pocket is the M-Pesa one (by id or name)."""
    p = str(pid or "").lower()
    n = str(name or "").lower()
    return ("mpesa" in p) or ("mpesa" in n) or ("m-pesa" in n)


def ekg_html():
    pts = ("0,30 60,30 80,30 90,14 100,44 110,8 120,30 180,30 "
           "260,30 280,30 290,18 300,38 310,30 400,30 480,30 "
           "500,30 510,12 520,46 530,6 540,30 620,30 700,30")
    return (
        '<svg class="tw-ekg" viewBox="0 0 700 60" '
        'preserveAspectRatio="none">'
        '<polyline class="tw-ekg-line" points="' + pts + '"/>'
        '</svg>'
    )


def brand_html():
    return (
        '<div class="tw-brand">' + WAVE + '<div>'
        '<div class="tw-brand-n">PULSE</div>'
        '<div class="tw-brand-s">LIFE COMMAND CENTER &middot; NBO</div>'
        '</div></div>'
    )


def user_html(name, role="Operator"):
    return (
        '<div class="tw-user">'
        '<div class="tw-avatar">' + html.escape(U.initials(name))
        + '</div><div>'
        '<div class="tw-user-n">' + html.escape(name) + '</div>'
        '<div class="tw-user-r">' + html.escape(role) + '</div>'
        '</div></div>'
    )


def greeting_html(name):
    return (
        '<div class="tw-greet">'
        '<span class="tw-greet-hi">Good to see you,</span>'
        '<span class="tw-greet-name">' + html.escape(name) + '</span>'
        '<span class="tw-live" title="live"></span></div>'
    )


def panel(title, body, right="", delay=0):
    r = ""
    if right:
        r = ('<span class="tw-pill">' + html.escape(right) + '</span>')
    return (
        '<div class="tw-panel" style="animation-delay:' + str(delay)
        + 'ms"><div class="tw-panel-h">'
        '<span class="tw-panel-t">' + html.escape(title) + '</span>'
        + r + '</div><div>' + body + '</div></div>'
    )


def tile(label, value, delta_text="", delta_tone="mute",
         value_tone="ink", icon="", icon_tone="accent", delay=0):
    chip = ""
    if icon:
        chip = ('<span class="tw-chip ' + U.tone_cls(icon_tone) + '">'
                + _icon(icon) + '</span>')
    delta = ""
    if delta_text:
        delta = ('<div class="tw-sub ' + U.tone_cls(delta_tone) + '">'
                 + html.escape(delta_text) + '</div>')
    return (
        '<div class="tw-tile" style="animation-delay:' + str(delay)
        + 'ms"><div class="tw-tile-top">'
        '<span class="tw-lab">' + html.escape(label) + '</span>'
        + chip + '</div>'
        '<div class="tw-val ' + U.tone_cls(value_tone) + '">'
        + html.escape(str(value)) + '</div>' + delta + '</div>'
    )


def tiles_grid(items, cols):
    style = "grid-template-columns:repeat(" + str(cols) + ",1fr)"
    return ('<div class="tw-tiles" style="' + style + '">'
            + "".join(items) + '</div>')


def empty_state(msg="Nothing here yet."):
    return ('<div class="tw-empty">' + html.escape(msg) + '</div>')


def tag_chip(label, color):
    return ('<span class="tw-tagc" style="background:'
            + U.hexa(color, 0.16) + ';color:' + color + '">'
            + html.escape(label) + '</span>')


def badge(text, color):
    return ('<span class="tw-badge" style="background:'
            + U.hexa(color, 0.13) + ';color:' + color
            + ';border-color:' + U.hexa(color, 0.35) + '">'
            + html.escape(str(text)) + '</span>')


def stage_chip(stage):
    return badge(D.stage_label(stage, stage), D.stage_color(stage))


def progress(pct, color):
    w = max(0.0, min(100.0, float(pct)))
    return ('<div class="tw-prog"><div class="tw-prog-fill" '
            'style="width:' + format(w, ".1f") + '%;background:'
            + color + '"></div></div>')


def kv(pairs):
    """Premium key/value list - left accent tick, bright tabular values."""
    out = []
    for k, v in pairs:
        out.append(
            '<div class="tw-kv"><span class="tw-kv-k">'
            + html.escape(str(k)) + '</span><span class="tw-kv-v">'
            + str(v) + '</span></div>'
        )
    return '<div class="tw-kvlist">' + "".join(out) + '</div>'


def now_card(now_str, block, tag, tag_color, prog,
             next_time, next_label):
    nt = html.escape(str(next_time))
    nl = html.escape(str(next_label))
    if block:
        pct = str(int(prog * 100))
        left = (
            '<div class="tw-now-lab">RIGHT NOW</div>'
            '<div class="tw-now-block">'
            + html.escape(block["label"]) + '</div>'
            '<div class="tw-now-meta">' + tag_chip(tag, tag_color)
            + '</div>'
            '<div class="tw-now-bar"><div class="tw-now-fill" '
            'style="width:' + pct + '%"></div></div>'
            '<div class="tw-now-next">next &middot; ' + nt + ' '
            + nl + '</div>'
        )
    else:
        left = (
            '<div class="tw-now-lab">RIGHT NOW</div>'
            '<div class="tw-now-block">Between blocks</div>'
            '<div class="tw-now-next">up next &middot; ' + nt + ' '
            + nl + '</div>'
        )
    right = (
        '<div style="text-align:right">'
        '<div class="tw-lab">nairobi &middot; eat</div>'
        '<div class="tw-now-time">' + html.escape(now_str)
        + '</div></div>'
    )
    return '<div class="tw-now">' + left + right + '</div>'


def timeline_html(blocks, active_idx):
    if not blocks:
        return ('<div class="tw-empty">'
                'No blocks scheduled for today.</div>')
    out = []
    for i, b in enumerate(blocks):
        if i == active_idx:
            state = "active"
        elif i < active_idx:
            state = "done"
        else:
            state = ""
        tg = b.get("tag", "Life")
        out.append(
            '<div class="tw-tl-item ' + state + '">'
            '<div class="tw-tl-time">' + html.escape(b["time"])
            + '</div>'
            '<div class="tw-tl-rail"><span class="tw-tl-dot">'
            + '</span></div>'
            '<div><div class="tw-tl-label">'
            + html.escape(b["label"]) + '</div>'
            '<div class="tw-tl-meta">' + tag_chip(tg, _tag_color(tg))
            + '</div></div></div>'
        )
    return '<div class="tw-tl">' + "".join(out) + '</div>'


def habit_grid(habits, log, dates, today):
    if not habits:
        return ('<div class="tw-empty">No habits defined yet.</div>')
    n = len(dates)
    head_cells = []
    for i, d in enumerate(dates):
        txt = str(d.day) if (i % 5 == 0 or i == n - 1) else ""
        head_cells.append("<span>" + txt + "</span>")
    cols = "grid-template-columns:repeat(" + str(n) + ",1fr)"
    head = (
        '<div class="tw-hhead"><div></div>'
        '<div class="tw-hhead-days" style="' + cols + '">'
        + "".join(head_cells) + '</div><div></div></div>'
    )
    rows = []
    for h in habits:
        s = log.get(h["id"], {})
        cells = []
        done = total = 0
        for d in dates:
            ds = d.isoformat()
            if d > today:
                cls = "tw-hcell future"
            elif s.get(ds):
                cls = "tw-hcell done"
                done += 1
                total += 1
            elif ds in s:
                cls = "tw-hcell miss"
                total += 1
            else:
                cls = "tw-hcell"
            if d == today:
                cls += " today"
            cells.append('<div class="' + cls + '" title="'
                         + d.strftime("%b %d") + '"></div>')
        pct = (done / total * 100) if total else 0.0
        pcls = ("tw-win" if pct >= 70 else
                ("tw-loss" if pct < 40 and total else "tw-mute"))
        rows.append(
            '<div class="tw-hrow-name"><span class="tw-hrow-ico">'
            + html.escape(h["icon"]) + '</span>'
            + html.escape(h["name"]) + '</div>'
            '<div class="tw-hcells" style="' + cols + '">'
            + "".join(cells) + '</div>'
            '<div class="tw-hpct ' + pcls + '">'
            + format(pct, ".0f") + '%</div>'
        )
    return head + '<div class="tw-hgrid">' + "".join(rows) + '</div>'


def goal_html(g, pct, color):
    pc = format(pct, ".0f")
    return (
        '<div class="tw-goal">'
        '<div class="tw-goal-t">' + html.escape(g["title"]) + '</div>'
        '<div class="tw-goal-m">' + html.escape(g["metric"])
        + ' &middot; ' + html.escape(str(g.get("quarter", "")))
        + '</div>'
        '<div class="tw-goal-bar"><div class="tw-goal-fill" '
        'style="width:' + pc + '%;background:' + color
        + '"></div></div>'
        '<div class="tw-goal-foot"><span>'
        + U.fmt_num(g["current"], 1) + ' / '
        + U.fmt_num(g["target"], 1) + '</span>'
        '<span style="color:' + color + '">' + pc + '%</span>'
        '</div></div>'
    )


def client_card(c, today):
    """Premium client card - stage-coloured top accent, glowing link,
    premium kv rows. Terminal clients show where the journey ended."""
    heat = c.get("heat", "Warm")
    hcolor = _HEAT.get(heat, "#7C8AA5")
    days = 0
    try:
        days = (today - _dt.date.fromisoformat(c["created"])).days
    except Exception:
        days = 0
    term = D.terminal_ids()
    stg = c.get("stage", "new")
    accent = D.stage_color(stg)
    rows = []
    phone = str(c.get("phone", "") or "")
    if phone:
        p = html.escape(phone)
        rows.append(("Phone", '<a href="tel:' + p
                     + '" style="color:var(--accent);text-decoration:'
                     'none;border-bottom:1px dashed rgba(76,141,255,.45)">'
                     + p + '</a>'))
    if stg in term:
        odate = (c.get("paid_date") or c.get("returned_date")
                 or c.get("created", ""))
        rows.append(("Outcome", D.stage_label(stg, stg)
                     + (" &middot; " + html.escape(str(odate))
                        if odate else "")))
    if c.get("next_action"):
        na = html.escape(c["next_action"])
        if c.get("next_date"):
            na += " &middot; " + html.escape(c["next_date"])
        rows.append(("Next action", na))
    if c.get("plan"):
        rows.append(("Plan", html.escape(c["plan"])))
    if c.get("remark"):
        rows.append(("Remark", html.escape(c["remark"])))
    if c.get("why_not"):
        rows.append(("Why not today", html.escape(c["why_not"])))
    rows.append(("Source", html.escape(str(c.get("source", "")))))
    budget = str(c.get("budget", "") or "")
    meta = html.escape(str(c.get("want", "") or ""))
    if budget:
        meta += " &middot; budget " + html.escape(budget)
    meta += " &middot; " + str(max(days, 0)) + "d in pipeline"
    return (
        '<div class="tw-card-premium" style="--card-accent:' + accent
        + '">'
        '<div class="tw-cp-top"><span class="tw-cp-name">'
        + html.escape(str(c.get("name", "?"))) + '</span>'
        '<span class="tw-cp-chips">' + stage_chip(stg) + " "
        + badge(heat, hcolor) + '</span></div>'
        '<div class="tw-cp-meta">' + meta + '</div>'
        + kv(rows) + '</div>'
    )


def stepper_html(c):
    cur = c.get("stage", "new")
    journey = D.journey_ids()
    idx = journey.index(cur) if cur in journey else -1
    parts = []
    for i, sid in enumerate(journey):
        if idx >= 0 and i < idx:
            cls = "done"
        elif i == idx:
            cls = "cur"
        else:
            cls = ""
        parts.append('<span class="tw-step ' + cls
                     + '"><span class="dot"></span>'
                     + html.escape(D.stage_label(sid, sid))
                     + '</span>')
        if i < len(journey) - 1:
            parts.append('<span class="tw-step-bar"></span>')
    branch = ""
    if cur not in journey:
        branch = ('<div style="margin:0 0 10px">' + stage_chip(cur)
                  + '</div>')
    return ('<div class="tw-steps">' + "".join(parts) + '</div>'
            + branch)


def memory_line(ts, note, stage=""):
    """One premium touch in the client memory timeline."""
    chip = (" " + stage_chip(stage)) if stage else ""
    return (
        '<div class="tw-mem"><span class="tw-mem-dot"></span>'
        '<div class="tw-mem-body"><div class="tw-mem-ts">'
        + html.escape(str(ts or "")) + chip + '</div>'
        '<div class="tw-mem-nt">' + html.escape(str(note or ""))
        + '</div></div></div>'
    )


def history_html(hist, limit=15):
    items = list(hist)[-limit:][::-1]
    if not items:
        return ('<div class="tw-empty">No touches logged yet - '
                'every call and text lands here.</div>')
    return "".join(memory_line(h.get("ts", ""), h.get("note", ""),
                               h.get("stage", "")) for h in items)


def journal_card(date_str, entry):
    """Premium journal card - top accent in the entry's mood colour."""
    mood = entry.get("mood", "")
    accent = MOOD_COLOR.get(mood, "#4C8DFF")
    h = entry.get("happened") or entry.get("gratitude") or ""
    rows = []
    if h:
        rows.append(("day", html.escape(h)))
    if entry.get("win"):
        rows.append(("win", html.escape(entry["win"])))
    if entry.get("lesson"):
        rows.append(("lesson", html.escape(entry["lesson"])))
    body = kv(rows) if rows else '<div class="tw-sub">—</div>'
    moodpill = ('<span class="tw-moodpill" style="color:' + accent
                + ';border-color:' + U.hexa(accent, 0.4) + '">'
                + html.escape(mood or "—") + '</span>')
    return (
        '<div class="tw-card-premium" style="--card-accent:' + accent
        + '"><div class="tw-cp-top"><span class="tw-cp-date">'
        + html.escape(date_str) + '</span>' + moodpill + '</div>'
        + body + '</div>'
    )


def equity_svg(points, gid="eq", h=260, kind="num", xfmt=None):
    W = 1000
    pl, pr, pt, pb = 46, 14, 18, 26
    vals = [v for _, v in points] or [0.0]
    vmin, vmax = min(vals), max(vals)
    if kind == "pct":
        vmin, vmax = 0.0, 100.0
    if vmax - vmin < 1e-9:
        vmax = vmin + 1
    n = max(len(points), 1)
    span_x = W - pl - pr
    span_y = h - pt - pb

    def X(i):
        return pl + (i / (n - 1)) * span_x if n > 1 else W / 2

    def Y(v):
        return pt + (1 - (v - vmin) / (vmax - vmin)) * span_y

    def ylab(v):
        return str(int(round(v))) + "%" if kind == "pct" \
            else U.fmt_k(v)

    def xlab(d):
        return xfmt(d) if xfmt else d.strftime("%b %y")

    grid, ytxt = [], []
    steps = 5 if kind == "pct" else 4
    for k in range(steps):
        v = vmin + (vmax - vmin) * k / (steps - 1)
        y = format(Y(v), ".1f")
        grid.append('<line class="tw-eq-grid" x1="' + str(pl)
                    + '" y1="' + y + '" x2="' + str(W - pr)
                    + '" y2="' + y + '"/>')
        ytxt.append('<text class="tw-eq-txt" x="6" y="'
                    + format(Y(v) + 3, ".1f") + '">' + ylab(v)
                    + '</text>')
    coords = [format(X(i), ".1f") + "," + format(p[1], ".1f")
              for i, p in enumerate(points)]
    line = (" ".join(coords) if coords else
            str(pl) + "," + format(Y(vals[0]), ".1f"))
    x0, xr, yb = format(pl, ".1f"), format(W - pr, ".1f"), str(h - pb)
    area = x0 + "," + yb + " " + line + " " + xr + "," + yb
    xtxt = []
    if n > 1:
        step = max(1, n // 6)
        for i in range(0, n, step):
            xtxt.append('<text class="tw-eq-txt" x="'
                        + format(X(i), ".1f") + '" y="' + str(h - 8)
                        + '" text-anchor="middle">'
                        + xlab(points[i][0]) + '</text>')
    if points:
        lx, ly = X(n - 1), Y(vals[-1])
    else:
        lx, ly = W / 2, h / 2
    return (
        '<svg class="tw-eq" viewBox="0 0 ' + str(W) + ' ' + str(h)
        + '" preserveAspectRatio="xMidYMid meet">'
        '<defs><linearGradient id="' + gid + '" x1="0" y1="0" '
        'x2="0" y2="1">'
        '<stop offset="0" stop-color="#4C8DFF" stop-opacity=".34"/>'
        '<stop offset="1" stop-color="#4C8DFF" stop-opacity="0"/>'
        '</linearGradient></defs>'
        + "".join(grid) + "".join(ytxt)
        + '<polygon class="tw-eq-area" points="' + area
        + '" fill="url(#' + gid + ')"/>'
        + '<polyline class="tw-eq-line" points="' + line + '"/>'
        + '<circle class="tw-eq-ring" cx="' + format(lx, ".1f")
        + '" cy="' + format(ly, ".1f") + '" r="6"/>'
        + '<circle class="tw-eq-dot" cx="' + format(lx, ".1f")
        + '" cy="' + format(ly, ".1f") + '" r="3.4"/>'
        + "".join(xtxt) + '</svg>'
    )


def bars(rows):
    if not rows:
        return '<div class="tw-empty">No data.</div>'
    mx = max([abs(v) for _l, v in rows] + [1])
    cells = []
    for i, (lab, v) in enumerate(rows):
        pct = min(abs(v) / mx * 48, 48)
        cls = "tw-bar-up" if v >= 0 else "tw-bar-down"
        cells.append(
            '<div class="tw-bar-col"><div class="tw-bar-track">'
            '<div class="tw-bar-zero"></div>'
            '<div class="tw-bar-fill ' + cls + '" style="height:'
            + format(pct, ".0f") + '%;animation-delay:' + str(i * 40)
            + 'ms" title="' + html.escape(str(lab)) + ": "
            + format(v, "+,.0f") + '"></div>'
            '<span class="tw-bar-lab">'
            + html.escape(str(lab)[-3:]) + '</span>'
            '</div></div>'
        )
    return '<div class="tw-bars">' + "".join(cells) + '</div>'


def hbars(items):
    if not items:
        return '<div class="tw-empty">No data yet.</div>'
    mx = max([abs(v) for _n, v, _c in items] + [1])
    rows = []
    for i, (name, v, color) in enumerate(items):
        w = min(abs(v) / mx * 100, 100)
        rows.append(
            '<div style="margin-bottom:11px;'
            'animation:tw-rise .5s ease both;animation-delay:'
            + str(i * 45) + 'ms">'
            '<div style="display:flex;justify-content:space-between;'
            'font:600 12px var(--body);margin-bottom:5px">'
            '<span style="color:var(--ink-2)">' + html.escape(name)
            + '</span><span style="font-family:var(--mono);color:'
            + color + '">' + format(v, "+,.0f") + '</span></div>'
            '<div style="height:7px;background:rgba(255,255,255,.04);'
            'border-radius:4px;overflow:hidden">'
            '<div style="height:100%;width:' + format(w, ".1f")
            + '%;background:' + color + ';border-radius:4px;'
            'transform-origin:left;animation:tw-grow .7s ease both">'
            '</div></div></div>'
        )
    return "".join(rows)


def donut(segments, center_top, center_sub, total):
    r, sw, cx, cy = 52, 14, 70, 70
    C = 2 * math.pi * r
    rings, acc = [], 0.0
    for _n, val, color in segments:
        if val <= 0:
            continue
        length = (val / total * C) if total > 0 else 0.0
        rings.append(
            '<circle cx="' + str(cx) + '" cy="' + str(cy) + '" r="'
            + str(r) + '" fill="none" stroke="' + color
            + '" stroke-width="' + str(sw) + '" stroke-dasharray="'
            + format(length, ".2f") + " " + format(C - length, ".2f")
            + '" stroke-dashoffset="' + format(-acc, ".2f")
            + '" transform="rotate(-90 ' + str(cx) + " " + str(cy)
            + ')"/>')
        acc += length
    if not rings:
        rings.append('<circle cx="' + str(cx) + '" cy="' + str(cy)
                     + '" r="' + str(r) + '" fill="none" '
                     + 'stroke="#1C2740" stroke-width="' + str(sw)
                     + '"/>')
    svg = (
        '<svg width="140" height="140" viewBox="0 0 140 140">'
        + "".join(rings)
        + '<text class="tw-donut-c1" x="' + str(cx) + '" y="'
        + str(cy - 8) + '" text-anchor="middle">'
        + html.escape(str(center_sub)) + '</text>'
        + '<text class="tw-donut-c2" x="' + str(cx) + '" y="'
        + str(cy + 12) + '" text-anchor="middle">'
        + html.escape(str(center_top)) + '</text></svg>'
    )
    leg = []
    for name, val, color in segments:
        pct = (val / total * 100) if total > 0 and val > 0 else 0.0
        leg.append(
            '<div class="tw-leg-row">'
            '<span class="tw-leg-dot" style="background:' + color
            + '"></span><span class="tw-leg-name">'
            + html.escape(str(name)) + '</span>'
            '<span class="tw-leg-val">' + format(val, "+,.0f")
            + '</span><span class="tw-leg-pct">'
            + format(pct, ".0f") + '%</span></div>'
        )
    return ('<div class="tw-donut-wrap">' + svg
            + '<div class="tw-legend">' + "".join(leg)
            + '</div></div>')


def calendar_html(year, month, day_map, today=None, pct=False):
    head = "".join("<span>" + d + "</span>" for d in WEEKDAYS)
    first_wd, ndays = _cal.monthrange(year, month)
    cells = ['<div class="tw-day empty"></div>'] * (first_wd % 7)
    for d in range(1, ndays + 1):
        date = _dt.date(year, month, d)
        v = day_map.get(date)
        cls = ["tw-day"]
        inner = '<div class="tw-day-num">' + str(d) + '</div>'
        if v is not None:
            if pct:
                if v >= 70:
                    cls.append("up")
                    tone = "tw-win"
                elif v < 40:
                    cls.append("down")
                    tone = "tw-loss"
                else:
                    tone = "tw-mute"
                inner += ('<div class="tw-day-pnl ' + tone + '">'
                          + str(int(round(v))) + '%</div>')
            else:
                tone = "tw-win" if v >= 0 else "tw-loss"
                cls.append("up" if v >= 0 else "down")
                inner += ('<div class="tw-day-pnl ' + tone + '">'
                          + format(v, "+,.0f") + '</div>')
        if today == date:
            cls.append("today")
        if today and date > today:
            cls.append("future")
        cells.append('<div class="' + " ".join(cls) + '">' + inner
                     + '</div>')
    return ('<div class="tw-cal-head">' + head + '</div>'
            '<div class="tw-cal">' + "".join(cells) + '</div>')


def streaks_html(items):
    out = []
    for val, lab, tone in items:
        out.append(
            '<div class="tw-streak"><div class="tw-streak-n '
            + U.tone_cls(tone) + '">' + str(val) + '</div>'
            '<div class="tw-streak-l">' + html.escape(lab)
            + '</div></div>'
        )
    grid = "grid-template-columns:repeat(" + str(len(items)) + ",1fr)"
    return ('<div class="tw-streaks" style="' + grid + '">'
            + "".join(out) + '</div>')


def table(headers, rows):
    th = "".join("<th>" + html.escape(h) + "</th>" for h in headers)
    body = []
    for row in rows:
        tds = "".join('<td class="' + c + '">' + str(text) + '</td>'
                      for text, c in row)
        body.append("<tr>" + tds + "</tr>")
    if not body:
        body.append('<tr><td colspan="' + str(len(headers))
                    + '" class="tw-empty">No rows.</td></tr>')
    return ('<div class="tw-scroll"><table class="tw-table">'
            '<thead><tr>' + th + '</tr></thead><tbody>'
            + "".join(body) + '</tbody></table></div>')


# ---------------------------------------------------------------------------
# PREMIUM LOG RENDERERS - the heart of the "saved data looks alive" upgrade.
# References render as clean receipt chips (no '#'); M-Pesa references carry
# the brand mark + green; outflows read warm orange, inflows mint.
# ---------------------------------------------------------------------------

def _flow_eff(rec):
    """Signed effect of a stored money record (in +, out -, else as-is)."""
    k = rec.get("kind")
    a = float(rec.get("amount", 0))
    if k == "in":
        return abs(a)
    if k == "out":
        return -abs(a)
    return a


def kind_chip(kind):
    k = (kind or "").lower()
    if k == "in":
        lab, cls = "IN", "kc-in"
    elif k == "add":
        lab, cls = "ADD", "kc-in"
    elif k == "out":
        lab, cls = "OUT", "kc-out"
    elif k == "spend":
        lab, cls = "SPEND", "kc-out"
    elif k == "adjust":
        lab, cls = "ADJ", "kc-adj"
    else:
        lab, cls = (kind or "—").upper(), "kc-neutral"
    return '<span class="tw-kind ' + cls + '">' + lab + '</span>'


def txid_pill(txid, mpesa=False):
    """A reference as a clean chip. Empty -> nothing (no placeholder noise).
    M-Pesa -> brand mark + green; otherwise a barcode mark + neutral ink."""
    t = (txid or "").strip()
    if not t:
        return ""
    code = html.escape(t)
    if mpesa:
        return ('<span class="tw-txid tw-txid-mpesa">'
                + MPESA_MARK + code + '</span>')
    return ('<span class="tw-txid">' + BARCODE_MARK + code + '</span>')


def amt_span(amount, signed=True, tone="auto"):
    try:
        v = float(amount)
    except (TypeError, ValueError):
        v = 0.0
    if tone == "flat":
        cls = "tw-amt-flat"
    elif tone == "pos":
        cls = "tw-amt-pos"
    elif tone == "neg":
        cls = "tw-amt-neg"
    else:
        cls = "tw-amt-pos" if v >= 0 else "tw-amt-neg"
    return ('<span class="tw-amt ' + cls + '">'
            + U.fmt_kes(v, signed) + '</span>')


def time_pill(date, time=""):
    d = html.escape(str(date or ""))
    t = (time or "").strip()
    if t:
        return ('<span class="tw-time"><span class="tw-time-d">'
                + d + '</span><span class="tw-time-t">'
                + html.escape(t) + '</span></span>')
    return ('<span class="tw-time"><span class="tw-time-d">'
            + d + '</span></span>')


def log_row(date, time, kind, amount, main_html, meta_html="",
            txid="", mpesa=False, tone=None, delay=0):
    """One premium log row: glowing rail + time + chip + reference + main
    text + glowing signed amount. Tone drives the rail/wash colour."""
    if tone is None:
        k = (kind or "").lower()
        if k in ("in", "add"):
            tone = "win"
        elif k in ("out", "spend"):
            tone = "loss"
        elif k == "adjust":
            tone = "jewel"
        else:
            try:
                tone = "win" if float(amount) >= 0 else "loss"
            except (TypeError, ValueError):
                tone = "neutral"
    rcls = {"win": "r-in", "loss": "r-out", "jewel": "r-adj",
            "done": "r-done"}.get(tone, "r-neutral")
    chip = kind_chip(kind) if kind else ""
    tp = txid_pill(txid, mpesa)
    amt = amt_span(amount, signed=(tone != "flat"))
    tm = time_pill(date, time)
    meta = ('<div class="tw-log-meta">' + meta_html + '</div>') \
        if meta_html else ""
    return (
        '<div class="tw-log ' + rcls + '" style="animation-delay:'
        + str(delay) + 'ms"><div class="tw-log-rail"></div>'
        '<div class="tw-log-body"><div class="tw-log-top">' + tm
        + chip + tp + '</div><div class="tw-log-main">'
        + str(main_html) + meta + '</div></div>'
        '<div class="tw-log-amt">' + amt + '</div></div>'
    )


def flow_log_rows(flow, pmap, limit=40):
    if not flow:
        return empty_state("No money logged yet - your first entry "
                           "starts the climb.")
    out = []
    for i, f in enumerate(flow[:limit]):
        eff = _flow_eff(f)
        pid = f.get("pocket", "")
        pname = pmap.get(pid, pid or "") or "—"
        mp = is_mpesa(pid, pname)
        main = html.escape(str(f.get("note", "") or "—"))
        meta = ('<span class="tw-pocket">' + html.escape(pname)
                + '</span>')
        out.append(log_row(f.get("date", ""), f.get("time", ""),
                           f.get("kind", ""), eff, main,
                           meta_html=meta, txid=f.get("txid", ""),
                           mpesa=mp, delay=min(i * 30, 300)))
    return '<div class="tw-loglist">' + "".join(out) + '</div>'


def tx_log_rows(tx_list, limit=4, mpesa=False):
    if not tx_list:
        return ('<div class="tw-sub" style="margin-top:6px">'
                'No moves yet.</div>')
    out = []
    for i, t in enumerate(tx_list[:limit]):
        eff = _flow_eff(t)
        main = html.escape(str(t.get("note", "") or t.get("kind", "")))
        out.append(log_row(t.get("date", ""), t.get("time", ""),
                           t.get("kind", ""), eff, main,
                           txid=t.get("txid", ""), mpesa=mpesa,
                           delay=i * 25))
    return ('<div class="tw-loglist tw-loglist-mini">'
            + "".join(out) + '</div>')


def income_log_rows(income, limit=12):
    if not income:
        return empty_state("No income logged yet.")
    out = []
    for i, x in enumerate(income[:limit]):
        main = html.escape(str(x.get("type", "")))
        meta = html.escape(str(x.get("note", "") or ""))
        out.append(log_row(x.get("date", ""), "", "in",
                           x.get("amount", 0), main, meta_html=meta,
                           tone="win", delay=min(i * 25, 300)))
    return '<div class="tw-loglist">' + "".join(out) + '</div>'


def client_line(client, phone):
    c = html.escape(str(client or "?"))
    p = str(phone or "").strip()
    if p:
        pe = html.escape(p)
        link = '<a href="tel:' + pe + '">' + pe + '</a>'
    else:
        link = '<span class="tw-mute">—</span>'
    return '<div class="tw-cl">' + c + ' &middot; ' + link + '</div>'


def task_done_row(t, delay=0):
    pri = {"High": "pr-h", "Normal": "pr-n", "Low": "pr-l"}.get(
        t.get("priority", "Normal"), "pr-n")
    dd = ('<span class="tw-time-d">'
          + html.escape(str(t.get("done_date", ""))) + '</span>') \
        if t.get("done_date") else ""
    return (
        '<div class="tw-log r-done" style="animation-delay:'
        + str(delay) + 'ms"><div class="tw-log-rail"></div>'
        '<div class="tw-log-body"><div class="tw-log-top">'
        '<span class="tw-kind kc-done">DONE</span>'
        '<span class="tw-pri ' + pri + '">'
        + html.escape(str(t.get("priority", ""))) + '</span>' + dd
        + '</div><div class="tw-log-main">'
        + html.escape(str(t.get("text", ""))) + '</div></div>'
        '<div class="tw-log-amt"><span class="tw-check-glyph">'
        + '✓</span></div></div>'
    )

# ---------------------------------------------------------------------------
# PANTRY premium rows  (display only - the edit widgets live in vault.py)
# ---------------------------------------------------------------------------

CAT_COLOR = {"staple": "#4C8DFF", "protein": "#34D399",
             "drink": "#2DD4BF", "treat": "#D946EF",
             "other": "#7C8AA5"}


def _days_tone(aged):
    if aged is None:
        return ("mute", "—", False)
    if aged >= 14:
        return ("win", format(aged, ".0f"), False)
    if aged >= 7:
        return ("accent", format(aged, ".0f"), False)
    if aged >= 3:
        return ("out", format(aged, ".0f"), False)
    return ("loss", format(aged, ".0f"), True)


def pantry_row(it, raw, aged):
    """One premium shelf card. raw/aged come from metrics so ui stays free of
    date math. Low stock (<3 days) pulses so the eye is pulled to it."""
    name = html.escape(str(it.get("name", "?")))
    unit = html.escape(str(it.get("unit", "u")))
    cat = it.get("category", "other")
    ccol = CAT_COLOR.get(cat, "#7C8AA5")
    tone, num, low = _days_tone(aged)
    stock = it.get("stock", 0)
    daily = it.get("daily", 0)
    chk = it.get("checked", "")
    if tone == "out":
        numcolor = "var(--out)"
        glow = "0 0 12px rgba(251,146,60,.35)"
    elif tone == "win":
        numcolor = "var(--win)"
        glow = "0 0 12px rgba(52,211,153,.35)"
    elif tone == "accent":
        numcolor = "var(--accent)"
        glow = "0 0 12px rgba(76,141,255,.35)"
    elif tone == "loss":
        numcolor = "var(--loss)"
        glow = "0 0 12px rgba(240,85,107,.4)"
    else:
        numcolor = "var(--mute)"
        glow = "none"
    lowcls = " tw-low" if low else ""
    barw = "0"
    if aged is not None:
        barw = format(min(aged / 30.0 * 100.0, 100.0), ".1f")
    if aged is None:
        shelf_note = "not consumed / set a daily burn"
    else:
        shelf_note = (format(aged, ".1f") + "d now")
        if raw is not None and abs(raw - aged) > 0.05:
            shelf_note += (" (was " + format(raw, ".1f")
                           + "d at check)")
    opt = ('<span class="tw-opt">optional</span>') \
        if it.get("hidden") else ""
    catc = ('<span class="tw-cat" style="background:'
            + hexa(ccol, 0.16) + ";color:" + ccol + '">'
            + html.escape(cat) + '</span>')
    checked = ('<span class="tw-aged">checked ' + html.escape(chk)
               + '</span>') if chk else \
        '<span class="tw-aged">not checked yet</span>'
    return (
        '<div class="tw-pantry">'
        '<div class="tw-pantry-top">'
        '<span class="tw-pantry-name">' + name + '</span>'
        '<span class="tw-pantry-chips">' + catc + opt + '</span>'
        '</div>'
        '<div class="tw-pantry-mid">'
        '<div class="tw-pantry-days' + lowcls + '" style="color:'
        + numcolor + ';text-shadow:' + glow + '">' + num
        + '<span class="tw-pantry-days-u">days</span></div>'
        '<div class="tw-shelf"><div class="tw-shelf-fill" style="width:'
        + barw + '%;background:' + numcolor + '"></div></div>'
        '</div>'
        '<div class="tw-pantry-meta">'
        '<span>' + U.fmt_num(stock, 0) + ' ' + unit + ' on shelf</span>'
        '<span>' + U.fmt_num(daily, 0) + ' ' + unit + '/day</span>'
        + checked + '</div>'
        '<div class="tw-pantry-note">' + shelf_note + '</div>'
        '</div>'
    )
