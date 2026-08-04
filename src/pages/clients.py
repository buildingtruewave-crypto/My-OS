"""TrueWave - the follow-up cockpit (the star page).
Shows only what a caller needs - name, phone (tap to dial), location, current
stage and next stage - plus the last thing said, so every call picks up exactly
where the previous one ended. One tight action row per client: log a call
result (appended to the living thread), postpone / set next call, move to the
next stage, end or reopen the journey. Heavy data entry and configuration live
on the Sales page so this page stays fast and seamless.
"""
from __future__ import annotations

import datetime as dt
import html

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI

_HEAT = {"Hot": "#F0556B", "Warm": "#F5B544", "Cold": "#7C8AA5"}
_CALL_RESULTS = [
    "Reached - good talk",
    "Reached - callback asked",
    "No answer",
    "Postponed",
    "Declined / cooling",
]
_NEXT_OPTS = [("keep today", 0), ("tomorrow", 1), ("in 2 days", 2),
              ("in 3 days", 3), ("next week", 7)]


def _ago(ts, today):
    try:
        d = dt.date.fromisoformat(str(ts)[:10])
        n = (today - d).days
    except Exception:
        return ""
    if n <= 0:
        return "today"
    if n == 1:
        return "1d ago"
    return str(n) + "d ago"


def _next_stage(c):
    journey = D.journey_ids()
    cur = c.get("stage", "new")
    if cur in journey:
        i = journey.index(cur)
        if i + 1 < len(journey):
            return journey[i + 1]
    return None


def _header_html(c, today):
    stg = c.get("stage", "new")
    heat = c.get("heat", "Warm")
    loc = str(c.get("location", "") or "").strip() or "—"
    phone = str(c.get("phone", "") or "").strip()
    try:
        days = max(0, (today - dt.date.fromisoformat(
            c["created"])).days)
    except Exception:
        days = 0
    plink = ('<a href="tel:' + html.escape(phone)
             + '" style="color:var(--accent);text-decoration:none;'
             'border-bottom:1px dashed rgba(76,141,255,.45)">'
             + html.escape(phone) + '</a>') if phone else \
        '<span class="tw-mute">no number</span>'
    nxt = _next_stage(c)
    nxt_txt = ("next · " + html.escape(D.stage_label(nxt, nxt))) \
        if nxt else "final stage"
    return (
        '<div style="display:flex;align-items:center;gap:9px;'
        'flex-wrap:wrap;margin-bottom:4px">'
        '<span style="font:700 15px/1.2 var(--disp);color:var(--ink)">'
        + html.escape(str(c.get("name", "?"))) + '</span>'
        + UI.stage_chip(stg)
        + UI.badge(heat, _HEAT.get(heat, "#7C8AA5"))
        + '<span class="tw-badge" style="background:'
          'rgba(255,255,255,.04);color:var(--ink-2);'
          'border-color:var(--hair)">📍 '
        + html.escape(loc) + '</span>'
        + '</div>'
        '<div class="tw-sub" style="margin-top:2px">' + plink
        + '  ·  ' + str(days) + 'd  ·  ' + nxt_txt + '</div>'
    )


def _cockpit(c, ctx, k):
    today, now_str = ctx["today"], ctx["now_str"]
    term = D.terminal_ids()
    ended = bool(c.get("ended")) or c.get("stage") in term
    st.markdown(_header_html(c, today), unsafe_allow_html=True)
    hist = c.get("history", [])
    if hist:
        lt = hist[-1]
        st.caption("Last: " + str(lt.get("note", ""))
                   + "  ·  " + _ago(lt.get("ts", ""), today))
    r1, r2, r3 = st.columns([1.3, 1.1, 1.9])
    with r1:
        result = st.selectbox("call result", _CALL_RESULTS,
                              key=k + "res")
    with r2:
        nxt = st.selectbox("next call", [o[0] for o in _NEXT_OPTS],
                           key=k + "nxt")
    with r3:
        note = st.text_input("what was said", key=k + "note",
                             placeholder="pick up the thread...")
    a1, a2, a3 = st.columns([1, 1.3, 1.1])
    with a1:
        if st.button("Log call", type="primary", key=k + "log"):
            off = dict(_NEXT_OPTS)[nxt]
            nd = ((today + dt.timedelta(days=off)).isoformat()
                  if off > 0 else (c.get("next_date")
                                   or today.isoformat()))
            full = result + ((" - " + note.strip())
                             if note.strip() else "")
            D.update_client(c["id"],
                            {"next_date": nd,
                             "next_action": "Follow-up call"},
                            now_str, log_note=full)
            st.rerun()
    with a2:
        adv = _next_stage(c)
        if adv and not ended:
            if st.button("→ " + D.stage_label(adv, adv),
                         key=k + "adv"):
                D.set_stage(c["id"], adv, now_str)
                st.rerun()
        else:
            st.caption("·")
    with a3:
        if ended:
            if st.button("Reopen journey", key=k + "re"):
                D.reopen_journey(c["id"], now_str)
                st.rerun()
        else:
            if st.button("End journey", key=k + "end"):
                D.end_journey(c["id"], now_str)
                st.rerun()
    with st.expander("conversation thread (" + str(len(hist)) + ")"):
        if hist:
            st.markdown(UI.history_html(hist),
                        unsafe_allow_html=True)
        else:
            st.caption("No touches yet - the first call starts the "
                       "thread.")
    st.markdown("<div style='height:12px;border-bottom:1px solid "
                "rgba(28,39,64,.5);margin-bottom:12px'></div>",
                unsafe_allow_html=True)


def render(ctx):
    clients, today = ctx["clients"], ctx["today"]
    cc = M.client_counts(clients, today)
    sheet = M.call_sheet(clients, today)
    cashq = M.cash_queue(clients)
    window = M.clients_in_window(clients, today)
    row = [
        UI.tile("Call Sheet", str(len(sheet)), "due today",
                "win" if sheet else "mute",
                "win" if sheet else "ink", "phone", "win", 0),
        UI.tile("Active Pipeline", str(cc["active"]), "in journey",
                "mute", "ink", "users", "accent", 40),
        UI.tile("Cash-Offer Queue", str(cc["cashq"]),
                "rejected → cash", "win" if cc["cashq"] else "mute",
                "win" if cc["cashq"] else "ink", "cash", "jewel", 80),
        UI.tile("Return Windows", str(len(window)), "7-day open",
                "mute", "ink", "cal", "jewel", 120),
        UI.tile("Paid & Closed", str(cc["sold"]), "since Aug 1",
                "win", "win", "check", "win", 160),
    ]
    st.markdown(UI.tiles_grid(row, 5), unsafe_allow_html=True)
    st.caption("Logging new leads & full configuration live on Sales. "
               "This page is for calling.")

    st.markdown('<div class="tw-lab" style="margin:10px 0 8px">'
                "TODAY'S CALL SHEET - hottest first</div>",
                unsafe_allow_html=True)
    if sheet:
        for c in sheet[:12]:
            _cockpit(c, ctx, "sh" + c["id"])
    else:
        st.markdown(UI.panel("Call Sheet", UI.empty_state(
            "Nothing due today. Postpone calls below or log new "
            "leads from Sales.")), unsafe_allow_html=True)

    if cashq:
        st.markdown('<div class="tw-lab" style="margin:14px 0 8px">'
                    'CASH-OFFER QUEUE - rejected, still callable'
                    '</div>', unsafe_allow_html=True)
        for c in cashq[:8]:
            _cockpit(c, ctx, "cq" + c["id"])

    q = st.text_input("search any client", key="tw_q",
                      placeholder="name / phone / location / note")
    ql = q.strip().lower()
    if ql:
        shown = []
        for c in clients:
            hay = " ".join([str(c.get("name", "")),
                            str(c.get("phone", "")),
                            str(c.get("location", "")),
                            str(c.get("want", "")),
                            str(c.get("remark", ""))]).lower()
            if ql in hay:
                shown.append(c)
        st.markdown('<div class="tw-lab" style="margin:10px 0 8px">'
                    'RESULTS (' + str(len(shown)) + ')</div>',
                    unsafe_allow_html=True)
        for c in shown[:15]:
            _cockpit(c, ctx, "sr" + c["id"])
