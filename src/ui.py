"""HTML / SVG components.  f-strings interpolate bare names only; every dict
lookup / strftime / .get is pulled into a local first, so no quote ever lives
inside a {..} (the construct that broke on Python 3.14)."""
from __future__ import annotations

import calendar as _cal
import datetime as _dt
import html
import math

from . import util as U
from .data import TAG_COLORS

WAVE = ('<svg width="30" height="30" viewBox="0 0 32 32" fill="none">'
        '<rect width="32" height="32" rx="9" fill="#0E1422" stroke="#1C2740"/>'
        '<circle cx="16" cy="16" r="3.4" fill="#4C8DFF"/>'
        '<circle cx="16" cy="16" r="7" stroke="#4C8DFF" stroke-width="1.4" opacity=".55"/>'
        '<circle cx="16" cy="16" r="11" stroke="#34D399" stroke-width="1.2" opacity=".3"/></svg>')


def _tag_color(tag):
    return TAG_COLORS.get(tag, "#7C8AA5")


def brand_html():
    return ('<div class="tw-brand">' + WAVE +
            '<div><div class="tw-brand-n">PULSE</div>'
            '<div class="tw-brand-s">LIFE COMMAND CENTER</div></div></div>')


def user_html(name, role="Operator"):
    av = html.escape(U.initials(name))
    nm = html.escape(name)
    ro = html.escape(role)
    return ('<div class="tw-user"><div class="tw-avatar">' + av + '</div>'
            '<div><div class="tw-user-n">' + nm + '</div>'
            '<div class="tw-user-r">' + ro + '</div></div></div>')


def greeting_html(name):
    nm = html.escape(name)
    return ('<div class="tw-greet"><span class="tw-greet-hi">Good to see you,</span>'
            '<span class="tw-greet-name">' + nm + '</span>'
            '<span class="tw-live" title="live"></span></div>')


def panel(title, body, right="", delay=0):
    r = '<span class="tw-pill">' + html.escape(right) + '</span>' if right else ""
    t = html.escape(title)
    return ('<div class="tw-panel" style="animation-delay:' + str(delay) + 'ms">'
            '<div class="tw-panel-h"><span class="tw-panel-t">' + t + '</span>' + r + '</div>'
            '<div>' + body + '</div></div>')


def tile(label, value, delta_text="", delta_tone="mute", value_tone="ink",
         icon="", icon_tone="accent", delay=0):
    chip = '<span class="tw-chip ' + U.tone_cls(icon_tone) + '">' + icon + '</span>' if icon else ""
    delta = ('<div class="tw-sub ' + U.tone_cls(delta_tone) + '">' +
             html.escape(delta_text) + '</div>') if delta_text else ""
    lab = html.escape(label)
    val = html.escape(value)
    return ('<div class="tw-tile" style="animation-delay:' + str(delay) + 'ms">'
            '<div class="tw-tile-top"><span class="tw-lab">' + lab + '</span>' + chip + '</div>'
            '<div class="tw-val ' + U.tone_cls(value_tone) + '">' + val + '</div>' + delta + '</div>')


def tiles_grid(items, cols):
    inner = "".join(items)
    return ('<div class="tw-tiles" style="grid-template-columns:repeat(' +
            str(cols) + ',1fr)">' + inner + '</div>')


def empty_state(msg="Nothing here yet."):
    return panel("Notice", '<div class="tw-empty">' + html.escape(msg) + '</div>')


def tag_chip(label, color):
    bg = U.hexa(color, 0.16)
    lab = html.escape(label)
    return ('<span class="tw-tagc" style="background:' + bg +
            ';color:' + color + '">' + lab + '</span>')


def now_card(now_str, block, tag, tag_color, progress, next_time, next_label):
    nt = html.escape(next_time)
    nl = html.escape(next_label)
    if block:
        lab = html.escape(block["label"])
        chip = tag_chip(tag, tag_color)
        pct = int(progress * 100)
        left = ('<div class="tw-now-lab">RIGHT NOW</div>'
                '<div class="tw-now-block">' + lab + '</div>'
                '<div class="tw-now-meta">' + chip + '</div>'
                '<div class="tw-now-bar"><div class="tw-now-fill" style="width:' +
                str(pct) + '%"></div></div>'
                '<div class="tw-now-next">next - ' + nt + ' ' + nl + '</div>')
    else:
        left = ('<div class="tw-now-lab">RIGHT NOW</div>'
                '<div class="tw-now-block">Off schedule</div>'
                '<div class="tw-now-next">first block - ' + nt + ' ' + nl + '</div>')
    right = ('<div style="text-align:right"><div class="tw-lab">local time</div>'
             '<div class="tw-now-time">' + html.escape(now_str) + '</div></div>')
    return '<div class="tw-now">' + left + right + '</div>'


def timeline_html(blocks, active_idx):
    if not blocks:
        return '<div class="tw-empty">No blocks scheduled for today.</div>'
    out = []
    for i, b in enumerate(blocks):
        if i == active_idx:
            state = "active"
        elif i < active_idx:
            state = "done"
        else:
            state = ""
        tg = b.get("tag", "Life")
        meta = tag_chip(tg, _tag_color(tg))
        t = html.escape(b["time"])
        lab = html.escape(b["label"])
        out.append('<div class="tw-tl-item ' + state + '">'
                   '<div class="tw-tl-time">' + t + '</div>'
                   '<div class="tw-tl-rail"><span class="tw-tl-dot"></span></div>'
                   '<div><div class="tw-tl-label">' + lab + '</div>'
                   '<div class="tw-tl-meta">' + meta + '</div></div></div>')
    return '<div class="tw-tl">' + "".join(out) + '</div>'


def habit_grid(habits, log, dates, today):
    if not habits:
        return '<div class="tw-empty">No habits defined yet.</div>'
    n = len(dates)
    head_cells = []
    for i, d in enumerate(dates):
        txt = str(d.day) if (i % 5 == 0 or i == n - 1) else ""
        head_cells.append('<span>' + txt + '</span>')
    head = ('<div class="tw-hhead"><div></div><div class="tw-hhead-days" '
            'style="grid-template-columns:repeat(' + str(n) + ',1fr)">' +
            "".join(head_cells) + '</div><div></div></div>')
    rows = []
    for h in habits:
        s = log.get(h["id"], {})
        cells = []
        for d in dates:
            ds = d.isoformat()
            if d > today:
                cls = "tw-hcell future"
            elif s.get(ds):
                cls = "tw-hcell done"
            elif ds in s:
                cls = "tw-hcell miss"
            else:
                cls = "tw-hcell"
            if d == today:
                cls = cls + " today"
            tip = d.strftime("%b %d")
            cells.append('<div class="' + cls + '" title="' + tip + '"></div>')
        done = sum(1 for d in dates if d <= today and s.get(d.isoformat()))
        total = sum(1 for d in dates if d <= today)
        pct = (done / total * 100) if total else 0
        if pct >= 70:
            pcls = "tw-win"
        elif pct < 40:
            pcls = "tw-loss"
        else:
            pcls = "tw-mute"
        ico = h["icon"]
        nm = html.escape(h["name"])
        rows.append('<div class="tw-hrow-name"><span class="tw-hrow-ico">' + ico + '</span>' +
                    nm + '</div>'
                    '<div class="tw-hcells" style="grid-template-columns:repeat(' +
                    str(n) + ',1fr)">' + "".join(cells) + '</div>'
                    '<div class="tw-hpct ' + pcls + '">' + format(pct, ".0f") + '%</div>')
    return head + '<div class="tw-hgrid">' + "".join(rows) + '</div>'


def goal_html(g, pct, color):
    t = html.escape(g["title"])
    m = html.escape(g["metric"])
    q = html.escape(str(g.get("quarter", "")))
    cur = U.fmt_num(g["current"], 1)
    tgt = U.fmt_num(g["target"], 1)
    return ('<div class="tw-goal"><div class="tw-goal-t">' + t + '</div>'
            '<div class="tw-goal-m">' + m + ' - ' + q + '</div>'
            '<div class="tw-goal-bar"><div class="tw-goal-fill" style="width:' +
            format(pct, ".0f") + '%;background:' + color + '"></div></div>'
            '<div class="tw-goal-foot"><span>' + cur + ' / ' + tgt + '</span>'
            '<span style="color:' + color + '">' + format(pct, ".0f") + '%</span></div></div>')


def _k(v):
    a = abs(v)
    if a >= 1000:
        s = format(a / 1000, ".1f") + "k"
    else:
        s = format(a, ".0f")
    return ("-" if v < 0 else "") + "$" + s


def equity_svg(points, gid="eq", h=280):
    W, pl, pr, pt, pb = 1000, 46, 14, 18, 26
    vals = [v for _, v in points] or [0.0]
    vmin, vmax = min(vals), max(vals)
    if vmax - vmin < 1e-9:
        vmax = vmin + 1
    n = max(len(points), 1)
    span_x = (W - pl - pr)
    span_y = (h - pt - pb)

    def X(i):
        return pl + (i / (n - 1)) * span_x if n > 1 else W / 2

    def Y(v):
        return pt + (1 - (v - vmin) / (vmax - vmin)) * span_y

    grid = []
    ytxt = []
    for k in range(4):
        v = vmin + (vmax - vmin) * k / 3
        y = Y(v)
        grid.append('<line class="tw-eq-grid" x1="' + str(pl) + '" y1="' +
                    format(y, ".1f") + '" x2="' + str(W - pr) + '" y2="' + format(y, ".1f") + '"/>')
        ytxt.append('<text class="tw-eq-txt" x="6" y="' + format(y + 3, ".1f") +
                    '">' + _k(v) + '</text>')
    coords = []
    for i, (_, v) in enumerate(points):
        coords.append(format(X(i), ".1f") + "," + format(Y(v), ".1f"))
    line = " ".join(coords) or (str(pl) + "," + format(Y(vals[0]), ".1f"))
    area = (format(pl, ".1f") + "," + str(h - pb) + " " + line + " " +
            format(W - pr, ".1f") + "," + str(h - pb))
    xtxt = []
    if n > 1:
        step = max(1, n // 6)
        for i in range(0, n, step):
            d = points[i][0]
            lab = d.strftime("%b %y")
            xtxt.append('<text class="tw-eq-txt" x="' + format(X(i), ".1f") +
                        '" y="' + str(h - 8) + '" text-anchor="middle">' + lab + '</text>')
    lx = X(n - 1) if points else W / 2
    ly = Y(vals[-1]) if points else h / 2
    lxs = format(lx, ".1f")
    lys = format(ly, ".1f")
    return ('<svg class="tw-eq" viewBox="0 0 ' + str(W) + ' ' + str(h) +
            '" preserveAspectRatio="xMidYMid meet">'
            '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#4C8DFF" stop-opacity=".34"/>'
            '<stop offset="1" stop-color="#4C8DFF" stop-opacity="0"/></linearGradient></defs>'
            + "".join(grid) + "".join(ytxt) +
            '<polygon class="tw-eq-area" points="' + area + '" fill="url(#' + gid + ')"/>'
            '<polyline class="tw-eq-line" points="' + line + '"/>'
            '<circle class="tw-eq-ring" cx="' + lxs + '" cy="' + lys + '" r="6"/>'
            '<circle class="tw-eq-dot" cx="' + lxs + '" cy="' + lys + '" r="3.4"/>'
            + "".join(xtxt) + '</svg>')


def monthly_bars(rows):
    if not rows:
        return '<div class="tw-empty">No data.</div>'
    mx = max((abs(v) for _, v in rows), default=1) or 1
    cells = []
    for i, (lab, v) in enumerate(rows):
        pct = min(abs(v) / mx * 48, 48)
        cls = "tw-bar-up" if v >= 0 else "tw-bar-down"
        short = html.escape(lab[-3:])
        tip = html.escape(lab) + ": " + format(v, "+,.0f")
        cells.append('<div class="tw-bar-col"><div class="tw-bar-track"><div class="tw-bar-zero"></div>'
                     '<div class="tw-bar-fill ' + cls + '" style="height:' +
                     format(pct, ".0f") + '%;animation-delay:' + str(i * 40) +
                     'ms" title="' + tip + '"></div>'
                     '<span class="tw-bar-lab">' + short + '</span></div></div>')
    return '<div class="tw-bars">' + "".join(cells) + '</div>'


def donut(segments, center_top, center_sub, total):
    r, sw, cx, cy = 52, 14, 70, 70
    C = 2 * math.pi * r
    rings = []
    acc = 0.0
    for _name, val, color in segments:
        if val <= 0:
            continue
        frac = val / total if total > 0 else 0.0
        length = frac * C
        rings.append('<circle cx="' + str(cx) + '" cy="' + str(cy) + '" r="' + str(r) +
                     '" fill="none" stroke="' + color + '" stroke-width="' + str(sw) +
                     '" stroke-dasharray="' + format(length, ".2f") + " " +
                     format(C - length, ".2f") + '" stroke-dashoffset="' +
                     format(-acc, ".2f") + '" transform="rotate(-90 ' + str(cx) +
                     " " + str(cy) + ')"/>')
        acc += length
    if not rings:
        rings = ['<circle cx="' + str(cx) + '" cy="' + str(cy) + '" r="' + str(r) +
                 '" fill="none" stroke="#1C2740" stroke-width="' + str(sw) + '"/>']
    c1 = html.escape(center_sub)
    c2 = html.escape(center_top)
    svg = ('<svg class="tw-donut" width="140" height="140" viewBox="0 0 140 140">' +
           "".join(rings) +
           '<text class="tw-donut-c1" x="' + str(cx) + '" y="' + str(cy - 8) +
           '" text-anchor="middle">' + c1 + '</text>'
           '<text class="tw-donut-c2" x="' + str(cx) + '" y="' + str(cy + 12) +
           '" text-anchor="middle">' + c2 + '</text></svg>')
    leg = []
    for name, val, color in segments:
        pct = (val / total * 100) if (total > 0 and val > 0) else 0.0
        if val > 0:
            tone = "tw-win"
        elif val < 0:
            tone = "tw-loss"
        else:
            tone = "tw-mute"
        leg.append('<div class="tw-leg-row"><span class="tw-leg-dot" style="background:' +
                   color + '"></span>'
                   '<span class="tw-leg-name">' + html.escape(name) + '</span>'
                   '<span class="tw-leg-val ' + tone + '">' + format(val, "+,.0f") + '</span>'
                   '<span class="tw-leg-pct">' + format(pct, ".0f") + '%</span></div>')
    return ('<div class="tw-donut-wrap">' + svg +
            '<div class="tw-legend">' + "".join(leg) + '</div></div>')


def calendar_html(year, month, day_pnl, today=None):
    head = "".join('<span>' + d + '</span>'
                   for d in ["MON", "TUE", "WED", "THU", "FRI",
