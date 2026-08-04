"""TrueWave - the clean, premium, READ-ONLY view of the phone business.
Shows the whole journey for every client (including ended, cash-offer,
returned & exchanged, phone-issue and never-started cases) with clean labels
everywhere - no raw codes. All filling happens on Sales.
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


def _chips(c):
    stg = c.get("stage", "new")
    heat = c.get("heat", "Warm")
    bits = [UI.stage_chip(stg), UI.badge(heat, _HEAT.get(heat, "#7C8AA5"))]
    if c.get("ended"):
        bits.append(UI.badge("ENDED", "#7C8AA5"))
    if D.is_cash_offer(c):
        bits.append(UI.badge("CASH OFFER", "#F5B544"))
    if c.get("hold_reason"):
        bits.append(UI.badge(c["hold_reason"].upper(), "#FB923C"))
    if c.get("return_outcome"):
        bits.append(UI.badge(c["return_outcome"].upper(), "#FB923C"))
    return " ".join(bits)


def _head_html(c, today):
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
    return (
        '<div class="tw-cp-top"><span class="tw-cp-name">'
        + html.escape(str(c.get("name", "?"))) + '</span>'
        '<span class="tw-cp-chips">' + _chips(c) + '</span></div>'
        '<div class="tw-cp-meta">' + plink + '  ·  📍 '
        + html.escape(loc) + '  ·  ' + str(days) + 'd</div>')


def _journey_kv(c):
    rows = []
    if c.get("plan"):
        rows.append(("Plan", html.escape(c["plan"])))
    if c.get("pre_credit") and c["pre_credit"] != "pending":
        rows.append(("Pre-approval", html.escape(c["pre_credit"])))
    if c.get("credit") and c["credit"] != "pending":
        rows.append(("Credit outcome", html.escape(c["credit"])))
    if c.get("hold_reason"):
        rows.append(("Never started - reason",
                     html.escape(c["hold_reason"])))
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
        out.append(
            '<div class="tw-mem"><span class="tw-mem-dot"></span>'
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
                + _head_html(c, today) + '</div>',
                unsafe_allow_html=True)
    with st.expander("view full journey"):
        st.markdown(UI.stepper_html(c), unsafe_allow_html=True)
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
    cashq = M.cash_queue(clients)
    window = M.clients_in_window(clients, today)
    row = [
        UI.tile("Call Sheet", str(len(sheet)), "due today",
                "win" if sheet else "mute",
                "win" if sheet else "ink", "phone", "win", 0),
        UI.tile("Active Pipeline", str(cc["active"]), "in journey",
                "mute", "ink", "users", "accent", 40),
        UI.tile("New This Week", str(cc["new7"]), "ads + live",
                "mute", "ink", "bolt", "accent", 80),
        UI.tile("Cash-Offer Queue", str(cc["cashq"]), "rejected",
                "mute", "ink", "cash", "out", 120),
        UI.tile("Paid & Closed", str(cc["sold"]), "since Aug 1",
                "win" if cc["sold"] else "mute",
                "win" if cc["sold"] else "ink", "check", "win", 160),
        UI.tile("Returned", str(cc["returned"]), "incl. exchanged",
                "loss" if cc["returned"] else "mute",
                "loss" if cc["returned"] else "ink", "bolt", "loss",
                200),
    ]
    st.markdown(UI.tiles_grid(row, 6), unsafe_allow_html=True)
    st.caption("Read-only view. Log leads, calls, stages, credit, "
               "delivery, returns and phone issues on the Sales page.")

    if sheet:
        st.markdown('<div class="tw-lab" style="margin:10px 0 8px">'
                    "TODAY'S CALL SHEET - hottest first</div>",
                    unsafe_allow_html=True)
        for c in sheet[:10]:
            _client_view(c, ctx, "sh" + c["id"])

    if cashq:
        st.markdown('<div class="tw-lab" style="margin:14px 0 8px">'
                    'CASH-OFFER QUEUE - rejected to cash</div>',
                    unsafe_allow_html=True)
        for c in cashq[:8]:
            _client_view(c, ctx, "cq" + c["id"])

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
        if ql:
            hay = " ".join([str(c.get("name", "")),
                            str(c.get("phone", "")),
                            str(c.get("location", "")),
                            str(c.get("want", "")),
                            str(c.get("remark", ""))]).lower()
            if ql not in hay:
                continue
        if filt == "Active" and not M.is_active_pipeline(c):
            continue
        if filt == "Cash offers" and not D.is_cash_offer(c):
            continue
        if filt == "Won" and c.get("stage") != won:
            continue
        if filt == "Returned" and c.get("stage") != ret:
            continue
        if filt == "Ended" and not c.get("ended"):
            continue
        if filt == "Never started" and not c.get("hold_reason"):
            continue
        shown.append(c)
    shown.sort(key=lambda c: (
        0 if M.is_active_pipeline(c) else
        (1 if D.is_cash_offer(c) else 2),
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
