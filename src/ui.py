"""HTML / SVG components.

Every physical line in this file is kept short on purpose.  Long markup is
built with parenthesised implicit string concatenation (one fragment per
line) or explicit loops, so a copy tool that wraps long lines can never cut
a bracket off the end of a statement.  No f-strings are used.
"""
from __future__ import annotations

import calendar as _cal
import datetime as _dt
import html
import math

from . import util as U
from .data import TAG_COLORS

WAVE = (
    '<svg width="30" height="30" '
    'viewBox="0 0 32 32" fill="none">'
    '<rect width="32" height="32" rx="9" '
    'fill="#0E1422" stroke="#1C2740"/>'
    '<circle cx="16" cy="16" r="3.4" '
    'fill="#4C8DFF"/>'
    '<circle cx="16" cy="16" r="7" '
    'stroke="#4C8DFF" stroke-width="1.4" '
    'opacity=".55"/>'
    '<circle cx="16" cy="16" r="11" '
    'stroke="#34D399" stroke-width="1.2" '
    'opacity=".3"/></svg>'
)

WEEKDAYS = (
    "MON",
    "TUE",
    "WED",
    "THU",
    "FRI",
    "SAT",
    "SUN",
)


def _tag_color(tag):
    return TAG_COLORS.get(tag, "#7C8AA5")


def brand_html():
    return (
        '<div class="tw-brand">'
        + WAVE
        + '<div>'
        + '<div class="tw-brand-n">PULSE</div>'
        + '<div class="tw-brand-s">'
        + 'LIFE COMMAND CENTER</div>'
        + '</div></div>'
    )


def user_html(name, role="Operator"):
    av = html.escape(U.initials(name))
    nm = html.escape(name)
    ro = html.escape(role)
    return (
        '<div class="tw-user">'
        + '<div class="tw-avatar">' + av + '</div>'
        + '<div>'
        + '<div class="tw-user-n">' + nm + '</div>'
        + '<div class="tw-user-r">' + ro + '</div>'
        + '</div></div>'
    )


def greeting_html(name):
    nm = html.escape(name)
    return (
        '<div class="tw-greet">'
        + '<span class="tw-greet-hi">Good to see you,</span>'
        + '<span class="tw-greet-name">' + nm + '</span>'
        + '<span class="tw-live" title="live"></span>'
        + '</div>'
    )


def panel(title, body, right="", delay=0):
    t = html.escape(title)
    r = ""
    if right:
        r = (
            '<span class="tw-pill">'
            + html.escape(right) + '</span>'
        )
    d = str(delay)
    return (
        '<div class="tw-panel" '
        + 'style="animation-delay:' + d + 'ms">'
        + '<div class="tw-panel-h">'
        + '<span class="tw-panel-t">' + t + '</span>'
        + r + '</div>'
        + '<div>' + body + '</div>'
        + '</div>'
    )


def tile(label, value, delta_text="",
         delta_tone="mute", value_tone="ink",
         icon="", icon_tone="accent", delay=0):
    chip = ""
    if icon:
        chip = (
            '<span class="tw-chip '
            + U.tone_cls(icon_tone) + '">'
            + icon + '</span>'
        )
    delta = ""
    if delta_text:
        delta = (
            '<div class="tw-sub '
            + U.tone_cls(delta_tone) + '">'
            + html.escape(delta_text) + '</div>'
        )
    lab = html.escape(label)
    val = html.escape(value)
    d = str(delay)
    return (
        '<div class="tw-tile" '
        + 'style="animation-delay:' + d + 'ms">'
        + '<div class="tw-tile-top">'
        + '<span class="tw-lab">' + lab + '</span>'
        + chip + '</div>'
        + '<div class="tw-val '
        + U.tone_cls(value_tone) + '">'
        + val + '</div>'
        + delta + '</div>'
    )


def tiles_grid(items, cols):
    inner = "".join(items)
    style = "grid-template-columns:repeat(" + str(cols) + ",1fr)"
    open_div = '<div class="tw-tiles" style="'
    return open_div + style + '">' + inner + '</div>'


def empty_state(msg="Nothing here yet."):
    body = (
        '<div class="tw-empty">'
        + html.escape(msg) + '</div>'
    )
    return panel("Notice", body)


def tag_chip(label, color):
    bg = U.hexa(color, 0.16)
    lab = html.escape(label)
    return (
        '<span class="tw-tagc" style="background:'
        + bg + ';color:' + color + '">'
        + lab + '</span>'
    )


def now_card(now_str, block, tag, tag_color,
             progress, next_time, next_label):
    nt = html.escape(next_time)
    nl = html.escape(next_label)
    if block:
        lab = html.escape(block["label"])
        chip = tag_chip(tag, tag_color)
        pct = str(int(progress * 100))
        left = (
            '<div class="tw-now-lab">RIGHT NOW</div>'
            + '<div class="tw-now-block">' + lab + '</div>'
            + '<div class="tw-now-meta">' + chip + '</div>'
            + '<div class="tw-now-bar">'
            + '<div class="tw-now-fill" style="width:'
            + pct + '%"></div></div>'
            + '<div class="tw-now-next">next - '
            + nt + ' ' + nl + '</div>'
        )
    else:
        left = (
            '<div class="tw-now-lab">RIGHT NOW</div>'
            + '<div class="tw-now-block">Off schedule</div>'
            + '<div class="tw-now-next">first block - '
            + nt + ' ' + nl + '</div>'
        )
    right = (
        '<div style="text-align:right">'
        + '<div class="tw-lab">local time</div>'
        + '<div class="tw-now-time">'
        + html.escape(now_str) + '</div></div>'
    )
    return '<div class="tw-now">' + left + right + '</div>'


def timeline_html(blocks, active_idx):
    if not blocks:
        return (
            '<div class="tw-empty">'
            + 'No blocks scheduled for today.</div>'
        )
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
        item = (
            '<div class="tw-tl-item ' + state + '">'
            + '<div class="tw-tl-time">' + t + '</div>'
            + '<div class="tw-tl-rail">'
            + '<span class="tw-tl-dot"></span></div>'
            + '<div>'
            + '<div class="tw-tl-label">' + lab + '</div>'
            + '<div class="tw-tl-meta">' + meta + '</div>'
            + '</div></div>'
        )
        out.append(item)
    return '<div class="tw-tl">' + "".join(out) + '</div>'


def habit_grid(habits, log, dates, today):
    if not habits:
        return (
            '<div class="tw-empty">'
            + 'No habits defined yet.</div>'
        )
    n = len(dates)
    head_cells = []
    for i, d in enumerate(dates):
        show = (i % 5 == 0) or (i == n - 1)
        txt = str(d.day) if show else ""
        head_cells.append("<span>" + txt + "</span>")
    cols = "grid-template-columns:repeat(" + str(n) + ",1fr)"
    head = (
        '<div class="tw-hhead"><div></div>'
        + '<div class="tw-hhead-days" style="'
        + cols + '">' + "".join(head_cells)
        + '</div><div></div></div>'
    )
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
            cells.append(
                '<div class="' + cls
                + '" title="' + tip + '"></div>'
            )
        done = 0
        total = 0
        for d in dates:
            if d <= today:
                total += 1
                if s.get(d.isoformat()):
                    done += 1
        pct = (done / total * 100) if total else 0
        if pct >= 70:
            pcls = "tw-win"
        elif pct < 40:
            pcls = "tw-loss"
        else:
            pcls = "tw-mute"
        ico = h["icon"]
        nm = html.escape(h["name"])
        row = (
            '<div class="tw-hrow-name">'
            + '<span class="tw-hrow-ico">' + ico + '</span>'
            + nm + '</div>'
            + '<div class="tw-hcells" style="'
            + cols + '">' + "".join(cells) + '</div>'
            + '<div class="tw-hpct ' + pcls + '">'
            + format(pct, ".0f") + '%</div>'
        )
        rows.append(row)
    return head + '<div class="tw-hgrid">' + "".join(rows) + '</div>'


def goal_html(g, pct, color):
    t = html.escape(g["title"])
    m = html.escape(g["metric"])
    q = html.escape(str(g.get("quarter", "")))
    cur = U.fmt_num(g["current"], 1)
    tgt = U.fmt_num(g["target"], 1)
    pc = format(pct, ".0f")
    return (
        '<div class="tw-goal">'
        + '<div class="tw-goal-t">' + t + '</div>'
        + '<div class="tw-goal-m">' + m + ' - ' + q + '</div>'
        + '<div class="tw-goal-bar">'
        + '<div class="tw-goal-fill" style="width:'
        + pc + '%;background:' + color + '"></div></div>'
        + '<div class="tw-goal-foot"><span>'
        + cur + ' / ' + tgt + '</span>'
        + '<span style="color:' + color + '">'
        + pc + '%</span></div></div>'
    )


def _k(v):
    a = abs(v)
    if a >= 1000:
        s = format(a / 1000, ".1f") + "k"
    else:
        s = format(a, ".0f")
    sign = "-" if v < 0 else ""
    return sign + "$" + s


def equity_svg(points, gid="eq", h=280):
    W = 1000
    pl = 46
    pr = 14
    pt = 18
    pb = 26
    vals = [v for _, v in points] or [0.0]
    vmin = min(vals)
    vmax = max(vals)
    if vmax - vmin < 1e-9:
        vmax = vmin + 1
    n = max(len(points), 1)
    span_x = W - pl - pr
    span_y = h - pt - pb

    def X(i):
        if n > 1:
            return pl + (i / (n - 1)) * span_x
        return W / 2

    def Y(v):
        frac = (v - vmin) / (vmax - vmin)
        return pt + (1 - frac) * span_y

    grid = []
    ytxt = []
    for k in range(4):
        v = vmin + (vmax - vmin) * k / 3
        y = Y(v)
        ys = format(y, ".1f")
        grid.append(
            '<line class="tw-eq-grid" x1="' + str(pl)
            + '" y1="' + ys + '" x2="' + str(W - pr)
            + '" y2="' + ys + '"/>'
        )
        ytxt.append(
            '<text class="tw-eq-txt" x="6" y="'
            + format(y + 3, ".1f") + '">'
            + _k(v) + '</text>'
        )
    coords = []
    for i, pair in enumerate(points):
        cx = format(X(i), ".1f")
        cy = format(pair[1], ".1f")
        coords.append(cx + "," + cy)
    if coords:
        line = " ".join(coords)
    else:
        line = str(pl) + "," + format(Y(vals[0]), ".1f")
    x0 = format(pl, ".1f")
    xr = format(W - pr, ".1f")
    yb = str(h - pb)
    area = x0 + "," + yb + " " + line + " " + xr + "," + yb
    xtxt = []
    if n > 1:
        step = max(1, n // 6)
        for i in range(0, n, step):
            d = points[i][0]
            lab = d.strftime("%b %y")
            xtxt.append(
                '<text class="tw-eq-txt" x="'
                + format(X(i), ".1f") + '" y="'
                + str(h - 8) + '" text-anchor="middle">'
                + lab + '</text>'
            )
    if points:
        lx = X(n - 1)
        ly = Y(vals[-1])
    else:
        lx = W / 2
        ly = h / 2
    lxs = format(lx, ".1f")
    lys = format(ly, ".1f")
    return (
        '<svg class="tw-eq" viewBox="0 0 ' + str(W)
        + ' ' + str(h) + '" '
        + 'preserveAspectRatio="xMidYMid meet">'
        + '<defs><linearGradient id="' + gid
        + '" x1="0" y1="0" x2="0" y2="1">'
        + '<stop offset="0" stop-color="#4C8DFF" '
        + 'stop-opacity=".34"/>'
        + '<stop offset="1" stop-color="#4C8DFF" '
        + 'stop-opacity="0"/></linearGradient></defs>'
        + "".join(grid) + "".join(ytxt)
        + '<polygon class="tw-eq-area" points="'
        + area + '" fill="url(#' + gid + ')"/>'
        + '<polyline class="tw-eq-line" points="'
        + line + '"/>'
        + '<circle class="tw-eq-ring" cx="' + lxs
        + '" cy="' + lys + '" r="6"/>'
        + '<circle class="tw-eq-dot" cx="' + lxs
        + '" cy="' + lys + '" r="3.4"/>'
        + "".join(xtxt) + '</svg>'
    )


def monthly_bars(rows):
    if not rows:
        return '<div class="tw-empty">No data.</div>'
    mx = 1
    for _lab, v in rows:
        if abs(v) > mx:
            mx = abs(v)
    cells = []
    for i, pair in enumerate(rows):
        lab = pair[0]
        v = pair[1]
        pct = min(abs(v) / mx * 48, 48)
        cls = "tw-bar-up" if v >= 0 else "tw-bar-down"
        short = html.escape(lab[-3:])
        tip = html.escape(lab) + ": " + format(v, "+,.0f")
        cell = (
            '<div class="tw-bar-col">'
            + '<div class="tw-bar-track">'
            + '<div class="tw-bar-zero"></div>'
            + '<div class="tw-bar-fill ' + cls
            + '" style="height:' + format(pct, ".0f")
            + '%;animation-delay:' + str(i * 40)
            + 'ms" title="' + tip + '"></div>'
            + '<span class="tw-bar-lab">' + short
            + '</span></div></div>'
        )
        cells.append(cell)
    return '<div class="tw-bars">' + "".join(cells) + '</div>'


def donut(segments, center_top, center_sub, total):
    r = 52
    sw = 14
    cx = 70
    cy = 70
    C = 2 * math.pi * r
    rings = []
    acc = 0.0
    for seg in segments:
        val = seg[1]
        color = seg[2]
        if val <= 0:
            continue
        frac = val / total if total > 0 else 0.0
        length = frac * C
        ring = (
            '<circle cx="' + str(cx) + '" cy="' + str(cy)
            + '" r="' + str(r) + '" fill="none" stroke="'
            + color + '" stroke-width="' + str(sw)
            + '" stroke-dasharray="' + format(length, ".2f")
            + " " + format(C - length, ".2f")
            + '" stroke-dashoffset="' + format(-acc, ".2f")
            + '" transform="rotate(-90 ' + str(cx)
            + " " + str(cy) + ')"/>'
        )
        rings.append(ring)
        acc += length
    if not rings:
        rings.append(
            '<circle cx="' + str(cx) + '" cy="' + str(cy)
            + '" r="' + str(r) + '" fill="none" '
            + 'stroke="#1C2740" stroke-width="' + str(sw) + '"/>'
        )
    c1 = html.escape(center_sub)
    c2 = html.escape(center_top)
    svg = (
        '<svg class="tw-donut" width="140" height="140" '
        + 'viewBox="0 0 140 140">' + "".join(rings)
        + '<text class="tw-donut-c1" x="' + str(cx)
        + '" y="' + str(cy - 8) + '" text-anchor="middle">'
        + c1 + '</text>'
        + '<text class="tw-donut-c2" x="' + str(cx)
        + '" y="' + str(cy + 12) + '" text-anchor="middle">'
        + c2 + '</text></svg>'
    )
    leg = []
    for seg in segments:
        name = seg[0]
        val = seg[1]
        color = seg[2]
        if total > 0 and val > 0:
            pct = val / total * 100
        else:
            pct = 0.0
        if val > 0:
            tone = "tw-win"
        elif val < 0:
            tone = "tw-loss"
        else:
            tone = "tw-mute"
        row = (
            '<div class="tw-leg-row">'
            + '<span class="tw-leg-dot" style="background:'
            + color + '"></span>'
            + '<span class="tw-leg-name">'
            + html.escape(name) + '</span>'
            + '<span class="tw-leg-val ' + tone + '">'
            + format(val, "+,.0f") + '</span>'
            + '<span class="tw-leg-pct">'
            + format(pct, ".0f") + '%</span></div>'
        )
        leg.append(row)
    return (
        '<div class="tw-donut-wrap">' + svg
        + '<div class="tw-legend">' + "".join(leg)
        + '</div></div>'
    )


def calendar_html(year, month, day_pnl, today=None):
    head = []
    for d in WEEKDAYS:
        head.append("<span>" + d + "</span>")
    first_wd, ndays = _cal.monthrange(year, month)
    cells = []
    for _ in range(first_wd % 7):
        cells.append('<div class="tw-day empty"></div>')
    for d in range(1, ndays + 1):
        date = _dt.date(year, month, d)
        pnl = day_pnl.get(date)
        cls = ["tw-day"]
        if pnl is not None and pnl > 0:
            cls.append("up")
        elif pnl is not None and pnl < 0:
            cls.append("down")
        if today == date:
            cls.append("today")
        if today and date > today:
            cls.append("future")
        inner = '<div class="tw-day-num">' + str(d) + '</div>'
        if pnl is not None:
            arrow = "+" if pnl >= 0 else "-"
            tone = "tw-win" if pnl >= 0 else "tw-loss"
            inner = inner + (
                '<div class="tw-day-pnl ' + tone + '">'
                + arrow + format(abs(pnl), ",.0f") + '</div>'
            )
        clsstr = " ".join(cls)
        cells.append(
            '<div class="' + clsstr + '">' + inner + '</div>'
        )
    return (
        '<div class="tw-cal-head">' + "".join(head) + '</div>'
        + '<div class="tw-cal">' + "".join(cells) + '</div>'
    )


def streaks_html(items):
    out = []
    for val, lab, tone in items:
        out.append(
            '<div class="tw-streak">'
            + '<div class="tw-streak-n '
            + U.tone_cls(tone) + '">'
            + str(val) + '</div>'
            + '<div class="tw-streak-l">'
            + html.escape(lab) + '</div></div>'
        )
    grid = "grid-template-columns:repeat(" + str(len(items)) + ",1fr)"
    body = "".join(out)
    open_div = '<div class="tw-streaks" style="'
    return open_div + grid + '">' + body + '</div>'


def table(headers, rows):
    th = []
    for h in headers:
        th.append("<th>" + html.escape(h) + "</th>")
    body = []
    for row in rows:
        tds = []
        for text, c in row:
            tds.append('<td class="' + c + '">' + text + '</td>')
        body.append("<tr>" + "".join(tds) + "</tr>")
    if not body:
        empty = (
            '<tr><td colspan="' + str(len(headers))
            + '" class="tw-empty">No rows.</td></tr>'
        )
        body.append(empty)
    return (
        '<div class="tw-scroll"><table class="tw-table">'
        + '<thead><tr>' + "".join(th) + '</tr></thead>'
        + '<tbody>' + "".join(body) + '</tbody>'
        + '</table></div>'
    )


def hbars(items):
    if not items:
        return '<div class="tw-empty">No data.</div>'
    mx = 1
    for _n, v, _c in items:
        if abs(v) > mx:
            mx = abs(v)
    rows = []
    for i, triple in enumerate(items):
        name = triple[0]
        v = triple[1]
        color = triple[2]
        w = min(abs(v) / mx * 100, 100)
        row = (
            '<div style="margin-bottom:11px;'
            + 'animation:tw-rise .5s ease both;'
            + 'animation-delay:' + str(i * 45) + 'ms">'
            + '<div style="display:flex;'
            + 'justify-content:space-between;'
            + 'font:600 12px var(--body);'
            + 'margin-bottom:5px">'
            + '<span style="color:var(--ink-2)">'
            + html.escape(name) + '</span>'
            + '<span style="font-family:var(--mono);color:'
            + color + '">' + format(v, "+,.0f")
            + '</span></div>'
            + '<div style="height:7px;'
            + 'background:rgba(255,255,255,.04);'
            + 'border-radius:4px;overflow:hidden">'
            + '<div style="height:100%;width:'
            + format(w, ".1f") + '%;background:' + color
            + ';border-radius:4px;transform-origin:left;'
            + 'animation:tw-grow .7s ease both">'
            + '</div></div></div>'
        )
        rows.append(row)
    return "".join(rows)


def journal_card(date_str, entry):
    g = html.escape(entry.get("gratitude", ""))
    w = html.escape(entry.get("win", ""))
    les = entry.get("lesson", "")
    m = html.escape(entry.get("mood", ""))
    rows = '<div class="row"><b>grateful -</b> ' + g + '</div>'
    rows = rows + '<div class="row"><b>win -</b> ' + w + '</div>'
    if les:
        rows = rows + (
            '<div class="row"><b>lesson -</b> '
            + html.escape(les) + '</div>'
        )
    rows = rows + (
        '<div class="row" style="margin-top:5px">'
        + m + '</div>'
    )
    return (
        '<div class="tw-jcard"><div class="d">'
        + html.escape(date_str) + '</div>'
        + rows + '</div>'
    )
