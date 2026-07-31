"""HTML / SVG components.  f-strings carry markup only (attribute styling);
all class styling lives in theme.CSS so brace-collisions cannot happen."""
from __future__ import annotations

import calendar as _cal
import html
import math

from . import util as U

WAVE = ('<svg width="30" height="30" viewBox="0 0 32 32" fill="none">'
        '<rect width="32" height="32" rx="9" fill="#0E1422" stroke="#1C2740"/>'
        '<circle cx="16" cy="16" r="3.4" fill="#4C8DFF"/>'
        '<circle cx="16" cy="16" r="7" stroke="#4C8DFF" stroke-width="1.4" opacity=".55"/>'
        '<circle cx="16" cy="16" r="11" stroke="#34D399" stroke-width="1.2" opacity=".3"/></svg>')


def brand_html():
    return ('<div class="tw-brand">' + WAVE +
            '<div><div class="tw-brand-n">PULSE</div>'
            '<div class="tw-brand-s">LIFE COMMAND CENTER</div></div></div>')


def user_html(name, role="Operator"):
    return (f'<div class="tw-user"><div class="tw-avatar">{html.escape(U.initials(name))}</div>'
            f'<div><div class="tw-user-n">{html.escape(name)}</div>'
            f'<div class="tw-user-r">{html.escape(role)}</div></div></div>')


def greeting_html(name):
    return (f'<div class="tw-greet"><span class="tw-greet-hi">Good to see you,</span>'
            f'<span class="tw-greet-name">{html.escape(name)}</span>'
            f'<span class="tw-live" title="live"></span></div>')


def panel(title, body, right="", delay=0):
    r = f'<span class="tw-pill">{html.escape(right)}</span>' if right else ""
    return (f'<div class="tw-panel" style="animation-delay:{delay}ms">'
            f'<div class="tw-panel-h"><span class="tw-panel-t">{html.escape(title)}</span>{r}</div>'
            f'<div>{body}</div></div>')


def tile(label, value, delta_text="", delta_tone="mute", value_tone="ink",
         icon="", icon_tone="accent", delay=0):
    chip = f'<span class="tw-chip {U.tone_cls(icon_tone)}">{icon}</span>' if icon else ""
    delta = f'<div class="tw-sub {U.tone_cls(delta_tone)}">{html.escape(delta_text)}</div>' if delta_text else ""
    return (f'<div class="tw-tile" style="animation-delay:{delay}ms">'
            f'<div class="tw-tile-top"><span class="tw-lab">{html.escape(label)}</span>{chip}</div>'
            f'<div class="tw-val {U.tone_cls(value_tone)}">{html.escape(value)}</div>{delta}</div>')


def tiles_grid(items, cols):
    return f'<div class="tw-tiles" style="grid-template-columns:repeat({cols},1fr)">{"".join(items)}</div>'


def empty_state(msg="Nothing here yet."):
    return panel("Notice", f'<div class="tw-empty">{html.escape(msg)}</div>')


def tag_chip(label, color):
    return (f'<span class="tw-tagc" style="background:{U.hexa(color, 0.16)};'
            f'color:{color}">{html.escape(label)}</span>')


# ---------------------------------------------------------------- now card
def now_card(now_str, block, tag, tag_color, progress, next_time, next_label):
    if block:
        left = (f'<div class="tw-now-lab">RIGHT NOW</div>'
                f'<div class="tw-now-block">{html.escape(block["label"])}</div>'
                f'<div class="tw-now-meta">{tag_chip(tag, tag_color)}</div>'
                f'<div class="tw-now-bar"><div class="tw-now-fill" style="width:{progress * 100:.0f}%"></div></div>'
                f'<div class="tw-now-next">next · {html.escape(next_time)} {html.escape(next_label)}</div>')
    else:
        left = ('<div class="tw-now-lab">RIGHT NOW</div>'
                '<div class="tw-now-block">Off schedule</div>'
                f'<div class="tw-now-next">first block · {html.escape(next_time)} {html.escape(next_label)}</div>')
    right = (f'<div style="text-align:right"><div class="tw-lab">local time</div>'
             f'<div class="tw-now-time">{html.escape(now_str)}</div></div>')
    return f'<div class="tw-now">{left}{right}</div>'


# ---------------------------------------------------------------- timeline
def timeline_html(blocks, active_idx):
    if not blocks:
        return '<div class="tw-empty">No blocks scheduled for today.</div>'
    out = ""
    for i, b in enumerate(blocks):
        state = "active" if i == active_idx else ("done" if i < active_idx else "")
        col = U.hexa(__import__("src.data", fromlist=["TAG_COLORS"]).TAG_COLORS.get(b.get("tag", "Life"), "#7C8AA5"), 1) if False else ""
        meta = tag_chip(b.get("tag", "Life"), _tag_color(b.get("tag", "Life")))
        out += (f'<div class="tw-tl-item {state}">'
                f'<div class="tw-tl-time">{html.escape(b["time"])}</div>'
                f'<div class="tw-tl-rail"><span class="tw-tl-dot"></span></div>'
                f'<div><div class="tw-tl-label">{html.escape(b["label"])}</div>'
                f'<div class="tw-tl-meta">{meta}</div></div></div>')
    return f'<div class="tw-tl">{out}</div>'


def _tag_color(tag):
    from .data import TAG_COLORS
    return TAG_COLORS.get(tag, "#7C8AA5")


# ---------------------------------------------------------------- habit grid
def habit_grid(habits, log, dates, today):
    if not habits:
        return '<div class="tw-empty">No habits defined yet.</div>'
    n = len(dates)
    head_days = "".join(
        f'<span>{d.day if (i % 5 == 0 or i == n - 1) else ""}</span>' for i, d in enumerate(dates))
    head = (f'<div class="tw-hhead"><div></div><div class="tw-hhead-days" '
            f'style="grid-template-columns:repeat({n},1fr)">{head_days}</div><div></div></div>')
    rows = ""
    for h in habits:
        s = log.get(h["id"], {})
        cells = ""
        for i, d in enumerate(dates):
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
                cls += " today"
            cells += f'<div class="{cls}" title="{d.strftime("%b %d")}"></div>'
        done = sum(1 for d in dates if d <= today and s.get(d.isoformat()))
        total = sum(1 for d in dates if d <= today)
        pct = done / total * 100 if total else 0
        rows += (f'<div class="tw-hrow-name"><span class="tw-hrow-ico">{h["icon"]}</span>'
                 f'{html.escape(h["name"])}</div>'
                 f'<div class="tw-hcells" style="grid-template-columns:repeat({n},1fr)">{cells}</div>'
                 f'<div class="tw-hpct {"tw-win" if pct >= 70 else ("tw-loss" if pct < 40 else "tw-mute")}">{pct:.0f}%</div>')
    return head + f'<div class="tw-hgrid">{rows}</div>'


# ---------------------------------------------------------------- goals
def goal_html(g, pct, color):
    return (f'<div class="tw-goal"><div class="tw-goal-t">{html.escape(g["title"])}</div>'
            f'<div class="tw-goal-m">{html.escape(g["metric"])} · {html.escape(str(g.get("quarter", "")))}</div>'
            f'<div class="tw-goal-bar"><div class="tw-goal-fill" style="width:{pct:.0f}%;background:{color}"></div></div>'
            f'<div class="tw-goal-foot"><span>{U.fmt_num(g["current"], 1)} / {U.fmt_num(g["target"], 1)}</span>'
            f'<span style="color:{color}">{pct:.0f}%</span></div></div>')


# ---------------------------------------------------------------- equity svg
def equity_svg(points, gid="eq", h=280):
    W, pl, pr, pt, pb = 1000, 46, 14, 18, 26
    vals = [v for _, v in points] or [0.0]
    vmin, vmax = min(vals), max(vals)
    if vmax - vmin < 1e-9:
        vmax = vmin + 1
    n = max(len(points), 1)
    X = lambda i: pl + (i / (n - 1)) * (W - pl - pr) if n > 1 else W / 2
    Y = lambda v: pt + (1 - (v - vmin) / (vmax - vmin)) * (h - pt - pb)
    grid = ytxt = ""
    for k in range(4):
        v = vmin + (vmax - vmin) * k / 3; y = Y(v)
        grid += f'<line class="tw-eq-grid" x1="{pl}" y1="{y:.1f}" x2="{W - pr}" y2="{y:.1f}"/>'
        ytxt += f'<text class="tw-eq-txt" x="6" y="{y + 3:.1f}">{_k(v)}</text>'
    line = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, (_, v) in enumerate(points)) or f"{pl},{Y(vals[0]):.1f}"
    area = f"{pl:.1f},{h - pb:.1f} " + line + f" {W - pr:.1f},{h - pb:.1f}"
    xtxt = ""
    if n > 1:
        step = max(1, n // 6)
        for i in range(0, n, step):
            d = points[i][0]
            xtxt += f'<text class="tw-eq-txt" x="{X(i):.1f}" y="{h - 8}" text-anchor="middle">{d.strftime("%b %y")}</text>'
    lx, ly = (X(n - 1), Y(vals[-1])) if points else (W / 2, h / 2)
    return (f'<svg class="tw-eq" viewBox="0 0 {W} {h}" preserveAspectRatio="xMidYMid meet">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="#4C8DFF" stop-opacity=".34"/>'
            f'<stop offset="1" stop-color="#4C8DFF" stop-opacity="0"/></linearGradient></defs>'
            f'{grid}{ytxt}<polygon class="tw-eq-area" points="{area}" fill="url(#{gid})"/>'
            f'<polyline class="tw-eq-line" points="{line}"/>'
            f'<circle class="tw-eq-ring" cx="{lx:.1f}" cy="{ly:.1f}" r="6"/>'
            f'<circle class="tw-eq-dot" cx="{lx:.1f}" cy="{ly:.1f}" r="3.4"/>{xtxt}</svg>')


def _k(v):
    a = abs(v)
    s = f"{a / 1000:.1f}k" if a >= 1000 else f"{a:.0f}"
    return ("-" if v < 0 else "") + "$" + s


# ---------------------------------------------------------------- monthly bars
def monthly_bars(rows):
    if not rows:
        return '<div class="tw-empty">No data.</div>'
    mx = max((abs(v) for _, v in rows), default=1) or 1
    cells = ""
    for i, (lab, v) in enumerate(rows):
        pct = min(abs(v) / mx * 48, 48)
        cls = "tw-bar-up" if v >= 0 else "tw-bar-down"
        cells += (f'<div class="tw-bar-col"><div class="tw-bar-track"><div class="tw-bar-zero"></div>'
                  f'<div class="tw-bar-fill {cls}" style="height:{pct}%;animation-delay:{i * 40}ms" '
                  f'title="{lab}: {v:+,.0f}"></div>'
                  f'<span class="tw-bar-lab">{html.escape(lab[-3:])}</span></div></div>')
    return f'<div class="tw-bars">{cells}</div>'


# ---------------------------------------------------------------- donut
def donut(segments, center_top, center_sub, total):
    r, sw, cx, cy = 52, 14, 70, 70
    C = 2 * math.pi * r
    rings = ""; acc = 0.0
    for _name, val, color in segments:
        if val <= 0:
            continue
        frac = val / total if total > 0 else 0.0
        length = frac * C
        rings += (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{sw}" '
                  f'stroke-dasharray="{length:.2f} {C - length:.2f}" stroke-dashoffset="{-acc:.2f}" '
                  f'transform="rotate(-90 {cx} {cy})"/>')
        acc += length
    if not rings:
        rings = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#1C2740" stroke-width="{sw}"/>'
    svg = (f'<svg class="tw-donut" width="140" height="140" viewBox="0 0 140 140">{rings}'
           f'<text class="tw-donut-c1" x="{cx}" y="{cy - 8}" text-anchor="middle">{html.escape(center_sub)}</text>'
           f'<text class="tw-donut-c2" x="{cx}" y="{cy + 12}" text-anchor="middle">{html.escape(center_top)}</text></svg>')
    leg = ""
    for i, (name, val, color) in enumerate(segments):
        pct = (val / total * 100) if (total > 0 and val > 0) else 0.0
        tone = "tw-win" if val > 0 else ("tw-loss" if val < 0 else "tw-mute")
        leg += (f'<div class="tw-leg-row"><span class="tw-leg-dot" style="background:{color}"></span>'
                f'<span class="tw-leg-name">{html.escape(name)}</span>'
                f'<span class="tw-leg-val {tone}">{val:+,.0f}</span>'
                f'<span class="tw-leg-pct">{pct:.0f}%</span></div>')
    return f'<div class="tw-donut-wrap">{svg}<div class="tw-legend">{leg}</div></div>'


# ---------------------------------------------------------------- calendar
def calendar_html(year, month, day_pnl, today=None):
    head = "".join(f"<span>{d}</span>" for d in ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"])
    first_wd, ndays = _cal.monthrange(year, month)
    cells = "".join('<div class="tw-day empty"></div>' for _ in range(first_wd % 7))
    for d in range(1, ndays + 1):
        import datetime as _dt
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
        inner = f'<div class="tw-day-num">{d}</div>'
        if pnl is not None:
            arrow = "▲" if pnl >= 0 else "▼"
            tone = "tw-win" if pnl >= 0 else "tw-loss"
            inner += f'<div class="tw-day-pnl {tone}">{arrow} {abs(pnl):,.0f}</div>'
        cells += f'<div class="{" ".join(cls)}">{inner}</div>'
    return f'<div class="tw-cal-head">{head}</div><div class="tw-cal">{cells}</div>'


# ---------------------------------------------------------------- streaks + tables
def streaks_html(items):
    out = ""
    for val, lab, tone in items:
        out += (f'<div class="tw-streak"><div class="tw-streak-n {U.tone_cls(tone)}">{val}</div>'
                f'<div class="tw-streak-l">{html.escape(lab)}</div></div>')
    return f'<div class="tw-streaks" style="grid-template-columns:repeat({len(items)},1fr)">{out}</div>'


def table(headers, rows):
    th = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(f'<td class="{c}">{t}</td>' for t, c in row) + "</tr>"
    if not body:
        body = f'<tr><td colspan="{len(headers)}" class="tw-empty">No rows.</td></tr>'
    return (f'<div class="tw-scroll"><table class="tw-table"><thead><tr>{th}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def hbars(items):
    if not items:
        return '<div class="tw-empty">No data.</div>'
    mx = max((abs(v) for _, v, _ in items), default=1) or 1
    rows = ""
    for i, (name, v, color) in enumerate(items):
        w = min(abs(v) / mx * 100, 100)
        rows += (f'<div style="margin-bottom:11px;animation:tw-rise .5s ease both;animation-delay:{i * 45}ms">'
                 f'<div style="display:flex;justify-content:space-between;font:600 12px var(--body);margin-bottom:5px">'
                 f'<span style="color:var(--ink-2)">{html.escape(name)}</span>'
                 f'<span style="font-family:var(--mono);color:{color}">{v:+,.0f}</span></div>'
                 f'<div style="height:7px;background:rgba(255,255,255,.04);border-radius:4px;overflow:hidden">'
                 f'<div style="height:100%;width:{w:.1f}%;background:{color};border-radius:4px;'
                 f'transform-origin:left;animation:tw-grow .7s ease both"></div></div></div>')
    return rows


def journal_card(date_str, entry):
    rows = f'<div class="row"><b>grateful ·</b> {html.escape(entry.get("gratitude", ""))}</div>'
    rows += f'<div class="row"><b>win ·</b> {html.escape(entry.get("win", ""))}</div>'
    if entry.get("lesson"):
        rows += f'<div class="row"><b>lesson ·</b> {html.escape(entry["lesson"])}</div>'
    rows += f'<div class="row" style="margin-top:5px">{html.escape(entry.get("mood", ""))}</div>'
    return f'<div class="tw-jcard"><div class="d">{html.escape(date_str)}</div>{rows}</div>'
