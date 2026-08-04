"""TrueWave - the clean, read-only follow-up cockpit.
Shows the follow-back clock, today's call sheet, search and ALL clients
(cash-offer clients simply appear in All Clients - no separate queue).
Each client's journey is a neat dot-track with only the current + next
stage named - no wall of stage labels. All filling happens on Sales.
"""
from __future__ import annotations

import datetime as dt
import html

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U

_HEAT = {"Hot": "#F0556B", "Warm": "#F5B544", "Cold": "#7C8AA5"}


def _fmt_when(fa):
    try:
        d = dt.datetime.fromisoformat(fa)
        return d.strftime("%a %b %d · %H:%M")
    except Exception:
        return str(fa)


def _journey_bar(c):
    """A neat journey: a thin dot-track plus ONLY the current stage chip
    and the next stage name. No wall of labels."""
    cur = c.get("stage", "new")
    journey = D.journey_ids()
    idx = journey.index(cur) if cur in journey else -1
    dots = []
    for i, sid in enumerate(journey):
        if idx >= 0 and i < idx:
            col = "#34D399"
            glow = ""
        elif i == idx:
            col = "#4C8DFF"
            glow = "box-shadow:0 0 8px #4C8DFF;"
        else:
            col = "#1C2740"
            glow = ""
        dots.append('<span style="width:9px;height:9px;border-radius:50%;'
                    'background:' + col + ';display:inline-block;'
                    'flex:0 0 auto;' + glow + '"></span>')
    bar = ('<div style="display:flex;align-items:center;gap:5px;'
           'margin:2px 0 9px;flex-wrap:wrap">'
           + "".join(dots) + '</div>')
    if idx >= 0:
        nxt_txt = ""
        if idx + 1 < len(journey):
            nxt_txt = ('<span class="tw-sub">next · '
                       + html.escape(D.stage_label(journey[idx + 1],
                                                   journey[idx + 1]))
                       + '</span>')
        cur_html = ('<div style="display:flex;align-items:center;gap:8px;'
                    'flex-wrap:wrap">' + UI.stage_chip(cur)
                    + nxt_txt + '</div>')
    else:
        cur_html = ('<div style="display:flex;align-items:center;gap:8px;'
                    'flex-wrap:wrap">' + UI.stage_chip(cur)
                    + '<span class="tw-sub">off the main path</span></div>')
    return bar + cur_html


def _follow_clock(ctx):
    clients, now_dt = ctx["clients"], ctx["now_dt"]
    fbs = M.follow_backs(clients, now_dt)
    if not fbs:
        st.markdown(UI.panel(
            "Follow-Back Clock",
            UI.empty_state("No scheduled call-backs. When a client says "
                           "'call me at 3', set it on the Sales client "
                           "desk and it will appear here at exactly that "
                           "time."),
            right="never miss a call-back"),
            unsafe_allow_html=True)
        return
    rows = []
    for c, fa, due in fbs:
        phone = str(c.get("phone", "") or "").strip()
        plink = ('<a href="tel:' + html.escape(phone)
                 + '" style="color:var(--accent)">'
                 + html.escape(phone) + '</a>') if phone else "—"
        if due:
            chip = UI.badge("FOLLOW NOW / MISSED", "#F0556B")
        else:
            chip = UI.badge("at " + _fmt_when(fa), "#F5B544")
        rows.append(
            '<div class="tw-log r-neutral" style="margin-bottom:8px">'
            '<div class="tw-log-rail"></div>'
            '<div class="tw-log-body"><div class="tw-log-top">'
            + chip + '</div><div class="tw-log-main">'
            + html.escape(str(c.get("name", "?"))) + '  ·  ' + plink
            + '  ·  ' + html.escape(str(c.get("location", "") or ""))
            + '</div></div></div>')
    st.markdown(UI.panel(
        "Follow-Back Clock - be in the app at the time",
        "".join(rows), right=str(len(fbs)) + " scheduled"),
        unsafe_allow_html=True)
    opts = {str(c.get("name", "?")) + "  ·  " + _fmt_when(fa): c
            for c, fa, _d in fbs}
    pick = st.selectbox("mark a follow-back done", list(opts.keys()),
                        key="tw_done_sel")
    if st.button("Mark followed", type="primary", key="tw_done"):
        c = opts[pick]
        D.update_client(c["id"], {"follow_done": True,
                                  "follow_at": ""},
                        ctx["now_str"], log_note="Followed back")
        st.rerun()


def _card_html(c, today):
    stg = c.get("stage", "new")
    heat = c.get("heat", "Warm")
    ended = bool(c.get("ended"))
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
    chips = UI.stage_chip(stg) + " " + UI.badge(heat,
                                                _HEAT.get(heat, "#7C8AA5"))
    if ended:
        chips += " " + UI.badge("ENDED", "#7C8AA5")
    if M.is_cash_offer(c):
        chips += " " + UI.badge("CASH OFFER", "#F5B544")
    return ('<div class="tw-cp-top"><span class="tw-cp-name">'
            + html.escape(str(c.get("name", "?"))) + '</span>'
            '<span class="tw-cp-chips">' + chips + '</span></div>'
            '<div class="tw-cp-meta">' + plink + '  ·  📍 '
            + html.escape(loc) + '  ·  ' + str(days) + 'd</div>')


def _journey_kv(c):
    rows = []
    if c.get("follow_at") and not c.get("follow_done"):
        rows.append(("Follow-back at", html.escape(
            _fmt_when(c["follow_at"]))))
    if c.get("plan"):
        rows.append(("Plan", html.escape(c["plan"])))
    if c.get("pre_credit") and c["pre_credit"] != "pending":
        rows.append(("Pre-approval", html.escape(c["pre_credit"])))
    if c.get("credit") and c["credit"] != "pending":
        rows.append(("Credit outcome", html.escape(c["credit"])))
    if c.get("next_action"):
        na = html.escape(c["next_action"])
        if c.get("next_date"):
            na += " · " + html.escape(c["next_date"])
        rows.append(("Next", na))
    if c.get("delivered_date"):
        rows.append(("Delivered", html.escape(c["delivered_date"])))
    if c.get("paid_date"):
        rows.append(("Paid", html.escape(c["paid_date"])))
    if c.get("returned_date"):
        ro = c.get("return_outcome") or "Returned"
        rows.append((html.escape(ro),
                     html.escape(c["returned_date"])))
    if c.get("remark"):
        rows.append(("Remark", html.escape(c["remark"])))
    return rows


def _service_html(c):
    svc = c.get("service", []) or []
    if not svc:
        return ""
    out = []
    for s in svc[-6:][::-1]:
        out.append('<div class="tw-mem"><span class="tw-mem-dot"></span>'
                   '<div class="tw-mem-body"><div class="tw-mem-ts">'
                   + html.escape(str(s.get("ts", ""))) + '</div>'
                   '<div class="tw-mem-nt"><b>'
                   + html.escape(str(s.get("issue", ""))) + '</b> → '
                   + html.escape(str(s.get("action", "")))
                   + (' · ' + html.escape(str(s.get("note", "")))
                      if s.get("note") else '') + '</div></div></div>')
    return ('<div class="tw-lab" style="margin:8px 0 4px">'
            'PHONE ISSUE LOG</div>' + "".join(out))


def _client_view(c, ctx, k):
    today = ctx["today"]
    st.markdown('<div class="tw-card-premium" style="--card-accent:'
                + D.stage_color(c.get("stage", "new")) + '">'
                + _card_html(c, today) + '</div>',
                unsafe_allow_html=True)
    with st.expander("view full journey + thread"):
        st.markdown(_journey_bar(c), unsafe_allow_html=True)
        kv = _journey_kv(c)
        if kv:
            st.markdown(UI.kv(kv), unsafe_allow_html=True)
        st.markdown(_service_html(c), unsafe_allow_html=True)
        st.markdown('<div class="tw-lab" style="margin:8px 0 4px">'
                    'CONVERSATION THREAD</div>',
                    unsafe_allow_html=True)
        st.markdown(UI.history_html(c.get("history", [])),
                    unsafe_allow_html=True)
        if c.get("ended"):
            st.caption("Ended - reopen & reschedule from the Sales "
                       "client desk when they reach out.")


def render(ctx):
    clients, today = ctx["clients"], ctx["today"]
    cc = M.client_counts(clients, today)
    sheet = M.call_sheet(clients, today)
    window = M.clients_in_window(clients, today)
    row = [
        UI.tile("Call Sheet", str(len(sheet)), "due today",
                "win" if sheet else "mute",
                "win" if sheet else "ink", "phone", "win", 0),
        UI.tile("Active Pipeline", str(cc["active"]), "in journey",
                "mute", "ink", "users", "accent", 40),
        UI.tile("New This Week", str(cc["new7"]), "ads + live",
                "mute", "ink", "bolt", "accent", 80),
        UI.tile("Return Windows", str(len(window)), "7-day open",
                "mute", "ink", "cal", "jewel", 120),
        UI.tile("Paid & Closed", str(cc["sold"]), "since Aug 1",
                "win" if cc["sold"] else "mute",
                "win" if cc["sold"] else "ink", "check", "win", 160),
        UI.tile("Returned", str(cc["returned"]), "incl. exchanged",
                "loss" if cc["returned"] else "mute",
                "loss" if cc["returned"] else "ink", "bolt", "loss",
                200),
    ]
    st.markdown(UI.tiles_grid(row, 6), unsafe_allow_html=True)

    _follow_clock(ctx)

    if sheet:
        st.markdown('<div class="tw-lab" style="margin:14px 0 8px">'
                    "TODAY'S CALL SHEET - hottest first</div>",
                    unsafe_allow_html=True)
        for c in sheet[:10]:
            _client_view(c, ctx, "sh" + c["id"])

    s1, s2 = st.columns([3, 2])
    with s1:
        q = st.text_input("search any client", key="tw_q",
                          placeholder="name / phone / location / note")
    with s2:
        filt = st.selectbox("show",
                            ["All", "Active", "Cash offers", "Won",
                             "Returned", "Ended", "Never started"],
                            key="tw_f")
    ql = q.strip().lower()
    won = D.role_id("won")
    ret = D.role_id("returned")
    shown = []
    for c in clients:
        if filt == "Active" and not M.is_active_pipeline(c):
            continue
        if filt == "Cash offers" and not M.is_cash_offer(c):
            continue
        if filt == "Won" and c.get("stage") != won:
            continue
        if filt == "Returned" and c.get("stage") != ret:
            continue
        if filt == "Ended" and not c.get("ended"):
            continue
        if filt == "Never started" and not c.get("hold_reason"):
            continue
        if ql:
            hay = " ".join([str(c.get("name", "")),
                            str(c.get("phone", "")),
                            str(c.get("location", "")),
                            str(c.get("want", "")),
                            str(c.get("remark", ""))]).lower()
            if ql not in hay:
                continue
        shown.append(c)
    shown.sort(key=lambda c: (
        0 if M.is_active_pipeline(c) else
        (1 if M.is_cash_offer(c) else 2),
        c.get("next_date") or c.get("created") or "9999"))
    st.markdown('<div class="tw-lab" style="margin:10px 0 8px">'
                'ALL CLIENTS (' + str(len(shown)) + ')</div>',
                unsafe_allow_html=True)
    if not shown:
        st.markdown(UI.panel("Clients", UI.empty_state(
            "No clients match - log a lead on Sales.")),
            unsafe_allow_html=True)
    for c in shown[:40]:
        _client_view(c, ctx, "al" + c["id"])
