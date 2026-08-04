"""TrueWave - the living, read-only view of every client journey. Each card
carries name, tap-to-dial phone, location, ID number, heat, and the
conversation thread. ID number is searchable. Today's call sheet stays on
top on days someone is due. Cash offers are shown only as an orange count
tile (green is reserved for sales) - every client, including cash-offer
ones, is outlined once in the ALL CLIENTS list. All filling lives on Sales.
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
_CASH = "#FB923C"
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


def _cash_tile(n, delay=80):
    vc = _CASH if n else "var(--mute)"
    return (
        '<div class="tw-tile" style="animation-delay:' + str(delay)
        + 'ms"><div class="tw-tile-top">'
        '<span class="tw-lab">Cash Offers</span>'
        '<span class="tw-chip" style="background:rgba(251,146,60,.14);'
        'color:' + _CASH + '">' + UI.ICONS.get("cash", "")
        + '</span></div>'
        '<div class="tw-val" style="color:' + vc + '">' + str(n)
        + '</div>'
        '<div class="tw-sub" style="color:' + vc + '">'
        'rejected to cash</div></div>'
    )


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
        + "  " + UI.badge(heat, _HEAT.get(heat, "#7C8AA5"))
        + '</span></div>'
        '<div class="tw-cp-meta">' + plink + idhtml + '  ·  📍 '
        + html.escape(loc) + '  ·  ' + str(days) + 'd</div></div>',
        unsafe_allow_html=True)
    with st.expander("view conversation thread"):
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
    row = [
        UI.tile("Call Sheet", str(len(sheet)), "in-progress due today",
                "win" if sheet else "mute",
                "win" if sheet else "ink", "phone", "win", 0),
        UI.tile("Active Journey", str(cc["active"]), "in process",
                "mute", "ink", "users", "accent", 40),
        _cash_tile(cc["cashq"]),
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
