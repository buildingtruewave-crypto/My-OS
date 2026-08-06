"""Signals - the live nerve center. Counts and the feed are computed here
directly from the event log (no dependency on metrics helpers), so the page
works with any metrics version. The Connection Map documents, declaratively,
what every action ripples into; the live feed shows each ripple on a
color-matched rail. Events are fired by the data layer itself whenever a
client moves, a journey ends/reopens, a sale logs, a commission pays or a
follow-back is set - so this page fills itself as you work.
"""
from __future__ import annotations
import html
import streamlit as st
from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U

_CASH = "#FB923C"


def _counts(events, t_iso):
    evs = events or []
    return {
        "today": sum(1 for e in evs if e.get("date") == t_iso),
        "autopilot": sum(1 for e in evs if e.get("autopilot")),
        "total": len(evs),
    }


def _feed(events, limit=30):
    out = []
    for e in (events or [])[:limit]:
        out.append({
            "date": e.get("date", ""),
            "time": e.get("time", ""),
            "label": e.get("title", ""),
            "detail": e.get("note", ""),
            "autopilot": bool(e.get("autopilot")),
            "color": D.EVENT_COLOR.get(e.get("type", ""), "#8893AB"),
        })
    return out


def _cash_tile(n, delay):
    vc = _CASH if n else "var(--mute)"
    return ('<div class="tw-tile" style="animation-delay:' + str(delay)
            + 'ms"><div class="tw-tile-top"><span class="tw-lab">'
            'Cash-Offer Queue</span><span class="tw-chip" '
            'style="background:' + U.hexa(_CASH, 0.14) + ';color:'
            + _CASH + '">' + UI.ICONS.get("cash", "") + '</span></div>'
            '<div class="tw-val" style="color:' + vc + '">' + str(n)
            + '</div><div class="tw-sub" style="color:' + vc + '">'
            'rejected → cash</div></div>')


def _feed_row(s, i):
    auto = ('<span class="tw-badge" style="background:'
            'rgba(217,70,239,.14);color:#D946EF;border-color:'
            'rgba(217,70,239,.4)">AUTO</span>') if s["autopilot"] else ""
    rail = ('<div class="tw-log-rail" style="background:' + s["color"]
            + ';box-shadow:0 0 10px ' + U.hexa(s["color"], 0.4)
            + '"></div>')
    tm = ('<span class="tw-time"><span class="tw-time-d">'
          + html.escape(s["date"]) + '</span>'
          + ('<span class="tw-time-t">' + html.escape(s["time"])
             + '</span>' if s["time"] else "") + '</span>')
    main = ('<span style="color:' + s["color"] + ';font-weight:700">'
            + html.escape(s["label"]) + '</span>'
            + ('  ·  ' + html.escape(s["detail"])
               if s["detail"] else ""))
    return ('<div class="tw-log" style="animation-delay:'
            + str(min(i * 25, 300)) + 'ms">' + rail
            + '<div class="tw-log-body"><div class="tw-log-top">' + tm
            + auto + '</div><div class="tw-log-main">' + main
            + '</div></div></div>')


def _connection_map():
    rows = []
    for etype, targets in D.CONNECTIONS.items():
        color = D.EVENT_COLOR.get(etype, "#8893AB")
        label = D.EVENT_LABELS.get(etype, etype)
        chips = "  ".join(
            '<span class="tw-badge" style="background:'
            'rgba(255,255,255,.04);color:var(--ink-2);border-color:'
            'var(--hair)">' + html.escape(tgt) + '</span>'
            for tgt, _d in targets)
        detail = "  →  ".join(html.escape(d) for _t, d in targets)
        rows.append(
            '<div style="display:flex;align-items:flex-start;gap:14px;'
            'padding:12px 0;border-bottom:1px solid rgba(28,39,64,.5)">'
            '<div style="flex:0 0 200px">'
            '<div style="font:700 13px var(--disp);color:' + color + '">'
            + html.escape(label) + '</div>'
            '<div class="tw-sub" style="margin-top:5px">' + chips
            + '</div></div>'
            '<div style="flex:1;font:500 12.5px/1.6 var(--body);'
            'color:var(--ink-2)">' + detail + '</div></div>')
    return "".join(rows)


def render(ctx):
    events = D.get_events()
    today_iso = ctx["today_iso"]
    clients = ctx["clients"]
    tasks = ctx["tasks"]
    sc = _counts(events, today_iso)
    cq = M.cash_queue(clients)
    auto_tasks = [t for t in tasks if t.get("auto")]
    row = [
        UI.tile("Signals Today", str(sc["today"]), "ripples fired",
                "win" if sc["today"] else "mute",
                "win" if sc["today"] else "ink", "pulse", "accent", 0),
        UI.tile("Autopilot Actions", str(sc["autopilot"]),
                "created for you", "jewel", "jewel", "bot", "jewel", 40),
        _cash_tile(len(cq), 80),
        UI.tile("Auto-Tasks Live", str(len(auto_tasks)),
                "spawned by events", "accent", "ink", "list", "accent",
                120),
        UI.tile("Total Signals", str(sc["total"]), "since Aug 1",
                "mute", "ink", "hash", "accent", 160),
    ]
    st.markdown(UI.tiles_grid(row, 5), unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>",
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        feed = _feed(events, 30)
        if feed:
            body = ('<div class="tw-loglist">'
                    + "".join(_feed_row(s, i)
                              for i, s in enumerate(feed))
                    + '</div>')
        else:
            body = UI.empty_state(
                "No signals yet. Move a client on TrueWave, save a "
                "call, log a sale or pay a commission - and watch it "
                "ripple here instantly.")
        st.markdown(UI.panel("Live Signal Feed", body,
                             right="newest first"),
                    unsafe_allow_html=True)
    with c2:
        if cq:
            items = [(c.get("name", "?") + " · "
                      + str(c.get("heat", "")), 1,
                      D.stage_color(c.get("stage", "new")))
                     for c in cq[:8]]
            st.markdown(UI.panel("Cash-Offer Queue - live",
                                 UI.hbars(items),
                                 right=str(len(cq)) + " queued"),
                        unsafe_allow_html=True)
        else:
            st.markdown(UI.panel("Cash-Offer Queue - live",
                                 UI.empty_state(
                                     "When a client gets a CASH OFFER - "
                                     "CREDIT outcome, they load here "
                                     "automatically. If they come back "
                                     "into the journey, they leave this "
                                     "queue for good."),
                                 right="rejected bucket"),
                        unsafe_allow_html=True)
        if auto_tasks:
            trows = []
            for t in auto_tasks[:8]:
                trows.append([
                    (html.escape(str(t.get("text", ""))), ""),
                    (html.escape(str(t.get("due", "--"))), "num"),
                    (UI.badge(str(t.get("priority", "")), "#8B7CFF"),
                     ""),
                ])
            st.markdown(UI.panel("Autopilot Tasks",
                                 UI.table(["Task", "Due", "Priority"],
                                          trows)),
                        unsafe_allow_html=True)
        else:
            st.markdown(UI.panel("Autopilot Tasks",
                                 UI.empty_state(
                                     "Autopilot creates follow-up tasks "
                                     "for you - they'll appear here.")),
                        unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    st.markdown(UI.panel("The Connection Map - what ripples where",
                         _connection_map(),
                         right="declarative + live"),
                unsafe_allow_html=True)
