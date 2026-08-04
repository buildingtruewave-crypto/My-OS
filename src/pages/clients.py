"""TrueWave - the READ-ONLY follow-up cockpit. Nothing is fillable here, not
even calls - every entry lives on the Sales page. This page is for following
up, searching, watching the cash-offer rejects (amber, never green), the
Returned count, and every client's full progress - including bought clients
with 1st/2nd commission status and ended journeys.
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


def _ord(n):
    return str(n) + ("st" if n == 1 else "nd" if n == 2 else "th")


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


def _client_comms(c, sales):
    phone = str(c.get("phone", "") or "").strip()
    name = str(c.get("name", "") or "").strip().lower()
    out = []
    for s in sales:
        sph = str(s.get("phone", "") or "").strip()
        snm = str(s.get("client", "") or "").strip().lower()
        if (phone and sph and sph == phone) or \
                (name and snm and snm == name):
            for i in s.get("inst", []):
                out.append(i)
    out.sort(key=lambda i: i.get("n", 0))
    return out


def _comm_chips(comms, today):
    if not comms:
        return ""
    bits = []
    for i in comms:
        n = int(i.get("n", 0) or 0)
        paid = bool(i.get("paid"))
        due = str(i.get("due", "") or "")
        if paid:
            bits.append(UI.badge(_ord(n) + " PAID", "#34D399"))
        elif due and due < today.isoformat():
            bits.append(UI.badge(_ord(n) + " OVERDUE", "#F0556B"))
        elif due:
            bits.append(UI.badge(_ord(n) + " due " + due, "#F5B544"))
        else:
            bits.append(UI.badge(_ord(n), "#7C8AA5"))
    return " ".join(bits)


def _card_html(c, ctx):
    today = ctx["today"]
    stg = c.get("stage", "new")
    heat = c.get("heat", "Warm")
    ended = bool(c.get("ended"))
    term = D.terminal_ids()
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
    rows = []
    comms = _client_comms(c, ctx["sales"])
    if comms:
        rows.append(("Commissions", _comm_chips(comms, today)))
    hist = c.get("history", [])
    if hist:
        lt = hist[-1]
        rows.append(("Last touch",
                     html.escape(str(lt.get("note", "")))
                     + " · " + _ago(lt.get("ts", ""), today)))
    if c.get("next_action"):
        na = html.escape(str(c["next_action"]))
        if c.get("next_date"):
            na += " · " + html.escape(str(c["next_date"]))
        rows.append(("Next", na))
    if stg in term or ended:
        odate = (c.get("paid_date") or c.get("returned_date")
                 or c.get("ended_date") or c.get("created", ""))
        rows.append(("Outcome", D.stage_label(stg, stg)
                     + ((" · " + html.escape(str(odate)))
                        if odate else "")))
    body = UI.kv(rows) if rows else '<div class="tw-sub">—</div>'
    return (
        '<div class="tw-card-premium" style="--card-accent:'
        + D.stage_color(stg) + '"><div class="tw-cp-top">'
        '<span class="tw-cp-name">'
        + html.escape(str(c.get("name", "?"))) + '</span>'
        '<span class="tw-cp-chips">' + chips + '</span></div>'
        '<div class="tw-cp-meta">' + plink + '  ·  📍 '
        + html.escape(loc) + '  ·  ' + str(days) + 'd</div>'
        + body + '</div>')


def _client_view(c, ctx, k):
    st.markdown(_card_html(c, ctx), unsafe_allow_html=True)
    with st.expander("full journey + thread"):
        st.markdown(UI.stepper_html(c), unsafe_allow_html=True)
        st.markdown(UI.history_html(c.get("history", [])),
                    unsafe_allow_html=True)


def render(ctx):
    clients, today = ctx["clients"], ctx["today"]
    cc = M.client_counts(clients, today)
    sheet = M.call_sheet(clients, today)
    cashq = M.cash_queue(clients)
    row = [
        UI.tile("Call Sheet", str(len(sheet)), "due today",
                "win" if sheet else "mute",
                "win" if sheet else "ink", "phone", "win", 0),
        UI.tile("Active Pipeline", str(cc["active"]), "in journey",
                "mute", "ink", "users", "accent", 40),
        UI.tile("New This Week", str(cc["new7"]), "ads + live",
                "mute", "ink", "bolt", "accent", 80),
        UI.tile("Cash-Offer Queue", str(cc["cashq"]),
                "rejected → cash", "mute", "ink", "cash", "out", 120),
        UI.tile("Paid & Closed", str(cc["sold"]), "since Aug 1",
                "win" if cc["sold"] else "mute",
                "win" if cc["sold"] else "ink", "check", "win", 160),
        UI.tile("Returned", str(cc["returned"]), "back inside window",
                "loss" if cc["returned"] else "mute",
                "loss" if cc["returned"] else "ink", "bolt", "loss",
                200),
    ]
    st.markdown(UI.tiles_grid(row, 6), unsafe_allow_html=True)
    st.caption("Read-only. Log leads, calls, notes, stages and money on "
               "the Sales page - this page just shows the truth.")

    if sheet:
        st.markdown('<div class="tw-lab" style="margin:10px 0 8px">'
                    "TODAY'S CALL SHEET - hottest first</div>",
                    unsafe_allow_html=True)
        for c in sheet[:10]:
            _client_view(c, ctx, "sh" + c["id"])

    if cashq:
        st.markdown('<div class="tw-lab" style="margin:14px 0 8px">'
                    'CASH-OFFER QUEUE - rejected, still callable</div>',
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
                             "Returned", "Ended"], key="tw_f")
    ql = q.strip().lower()
    term = D.terminal_ids()
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
