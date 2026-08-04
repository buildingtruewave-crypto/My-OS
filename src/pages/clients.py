"""TrueWave - the living, read-only view of every client journey. Each card
carries name, tap-to-dial phone, location, ID number, heat, a phase-based
journey map (Call System / Application / Credit / Delivery / Outcome) with
the current stage glowing, and the conversation thread. ID number is
searchable. All filling lives on Sales.
"""
from __future__ import annotations

import html

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U

_HEAT = {"Hot": "#F0556B", "Warm": "#F5B544", "Cold": "#7C8AA5"}
PHASES = [
    ("CALL SYSTEM", ["new", "followup", "undecided"], "#4C8DFF"),
    ("APPLICATION", ["agreed", "prescreen", "docs", "briefing"],
     "#2DD4BF"),
    ("CREDIT", ["preapproved", "pre_not_answered", "pre_not_ready",
                "cash_offer"], "#D946EF"),
    ("DELIVERY", ["deposit", "ready", "assigned", "out", "delivered",
                  "failed_delivery"], "#34D399"),
    ("OUTCOME", ["paid", "declined", "returned", "exchanged", "lost"],
     "#F0556B"),
]


def _status(c):
    if c.get("ended"):
        return ("ENDED", "#7C8AA5")
    role = D.stage_role(c.get("stage", ""))
    if role == "won":
        return ("PAID", "#34D399")
    if role == "returned":
        return ("RETURNED", "#F0556B")
    if role == "lost":
        return ("CLOSED", "#7C8AA5")
    if M.is_cash_offer(c):
        return ("CASH OFFER", "#FB923C")
    return ("IN JOURNEY", D.stage_color(c.get("stage", "new")))


def _journey_map(c):
    cur = c.get("stage", "new")
    journey = D.journey_ids()
    idx = journey.index(cur) if cur in journey else -1
    out = []
    for pname, ids, pcol in PHASES:
        active_phase = cur in ids
        chips = []
        for sid in ids:
            if sid == cur:
                chips.append('<span style="background:' + pcol
                             + ';color:#04101f;font-weight:800;'
                             'padding:3px 8px;border-radius:999px;'
                             'font:700 9px var(--mono);">'
                             + html.escape(D.stage_label(sid, sid))
                             + '</span>')
            else:
                chips.append('<span style="color:var(--mute);'
                             'font:600 9px var(--mono);padding:3px 4px;">'
                             + html.escape(D.stage_label(sid, sid))
                             + '</span>')
        head = ('<span style="color:' + (pcol if active_phase
                else "var(--mute)") + ';font:700 10px var(--disp);'
                'letter-spacing:.14em;">' + pname + '</span>')
        out.append('<div style="margin:6px 0;">' + head
                   + '<div style="display:flex;gap:4px;flex-wrap:wrap;'
                   'margin-top:4px;">' + "".join(chips) + '</div></div>')
    return '<div style="margin:6px 0 4px;">' + "".join(out) + '</div>'


def _card(c, ctx, k):
    today = ctx["today"]
    st_label, st_color = _status(c)
    heat = c.get("heat", "Warm")
    loc = str(c.get("location", "") or "").strip() or "—"
    phone = str(c.get("phone", "") or "").strip()
    idn = str(c.get("id_number", "") or "").strip()
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
    idhtml = (' · ID ' + html.escape(idn)) if idn else ""
    st.markdown(
        '<div class="tw-card-premium" style="--card-accent:'
        + st_color + '"><div class="tw-cp-top">'
        '<span class="tw-cp-name">'
        + html.escape(str(c.get("name", "?"))) + '</span>'
        '<span class="tw-cp-chips">' + UI.badge(st_label, st_color)
        + " " + UI.badge(heat, _HEAT.get(heat, "#7C8AA5"))
        + '</span></div>'
        '<div class="tw-cp-meta">' + plink + idhtml + '  ·  📍 '
        + html.escape(loc) + '  ·  ' + str(days) + 'd</div></div>',
        unsafe_allow_html=True)
    with st.expander("view journey + thread"):
        st.markdown(_journey_map(c), unsafe_allow_html=True)
        kv = []
        if c.get("follow_at") and not c.get("follow_done"):
            kv.append(("Follow-back", html.escape(
                str(c["follow_at"]).replace("T", " · "))))
        if c.get("plan"):
            kv.append(("Plan", html.escape(c["plan"])))
        if c.get("prescreen"):
            kv.append(("Pre-screen", html.escape(c["prescreen"])))
        if c.get("credit"):
            kv.append(("Credit", html.escape(c["credit"])))
        if c.get("delivery_mode"):
            kv.append(("Delivery", html.escape(c["delivery_mode"])))
        if c.get("failed_reason"):
            kv.append(("Failed", html.escape(c["failed_reason"])))
        if c.get("delivered_date"):
            kv.append(("Delivered", html.escape(c["delivered_date"])))
        if c.get("paid_date"):
            kv.append(("Paid", html.escape(c["paid_date"])))
        if c.get("returned_date"):
            kv.append(("Returned", html.escape(c["returned_date"])))
        if kv:
            st.markdown(UI.kv(kv), unsafe_allow_html=True)
        st.markdown('<div class="tw-lab" style="margin:8px 0 4px">'
                    'CONVERSATION THREAD</div>',
                    unsafe_allow_html=True)
        st.markdown(UI.history_html(c.get("history", [])),
                    unsafe_allow_html=True)


def render(ctx):
    clients, today = ctx["clients"], ctx["today"]
    cc = M.client_counts(clients, today)
    window = M.clients_in_window(clients, today)
    sheet = M.call_sheet(clients, today)
    cashq = M.cash_queue(clients)
    row = [
        UI.tile("Call Sheet", str(len(sheet)), "in-progress due today",
                "win" if sheet else "mute",
                "win" if sheet else "ink", "phone", "win", 0),
        UI.tile("Active Journey", str(cc["active"]), "in process",
                "mute", "ink", "users", "accent", 40),
        UI.tile("Cash Offers", str(cc["cashq"]), "rejected to cash",
                "win" if cc["cashq"] else "mute",
                "win" if cc["cashq"] else "ink", "cash", "out", 80),
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
    st.caption("Read-only. Log leads, calls and journey steps on Sales.")

    if sheet:
        st.markdown('<div class="tw-lab" style="margin:14px 0 8px">'
                    "TODAY'S CALL SHEET - hottest first</div>",
                    unsafe_allow_html=True)
        for c in sheet[:10]:
            _card(c, ctx, "sh" + c["id"])

    if cashq:
        st.markdown('<div class="tw-lab" style="margin:14px 0 8px">'
                    'CASH-OFFER QUEUE - rejected to cash</div>',
                    unsafe_allow_html=True)
        for c in cashq[:8]:
            _card(c, ctx, "cq" + c["id"])

    s1, s2 = st.columns([3, 2])
    with s1:
        q = st.text_input("search (name / phone / ID number)",
                          key="tw_q")
    with s2:
        filt = st.selectbox("show",
                            ["All", "Call System", "Application",
                             "Credit", "Delivery", "Outcomes",
                             "Cash offers"], key="tw_f")
    ql = q.strip().lower()
    qd = "".join(ch for ch in ql if ch.isdigit())
    shown = []
    for c in clients:
        stg = c.get("stage", "new")
        if filt == "Call System" and stg not in PHASES[0][1]:
            continue
        if filt == "Application" and stg not in PHASES[1][1]:
            continue
        if filt == "Credit" and stg not in PHASES[2][1]:
            continue
        if filt == "Delivery" and stg not in PHASES[3][1]:
            continue
        if filt == "Outcomes" and stg not in PHASES[4][1]:
            continue
        if filt == "Cash offers" and not M.is_cash_offer(c):
            continue
        if ql:
            hay = " ".join([str(c.get("name", "")),
                            str(c.get("phone", "")),
                            str(c.get("id_number", "")),
                            str(c.get("location", "")),
                            str(c.get("want", ""))]).lower()
            if not ((ql in hay)
                    or (qd and qd in "".join(
                        ch for ch in str(c.get("phone", ""))
                        if ch.isdigit()))
                    or (qd and qd in "".join(
                        ch for ch in str(c.get("id_number", ""))
                        if ch.isdigit()))):
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
        _card(c, ctx, "al" + c["id"])
