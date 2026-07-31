"""TrueWave - the phone business pipeline. Every inquiry is logged with
a promised follow-up date, a remark and the reason they won't buy today,
so tomorrow's dashboard knows exactly who to call."""
from __future__ import annotations

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI

OUTCOME_MAP = {
    "Still open": "open",
    "Sold": "sold",
    "Rejected - system": "rejected_system",
    "Rejected - cash only": "rejected_cash",
}


def _outcome_controls(c, today, key):
    o1, o2, o3 = st.columns([2, 2, 1])
    with o1:
        out = st.selectbox(
            "outcome", ["Still open", "Sold", "Rejected - system",
                        "Rejected - cash only", "Reschedule"],
            key=key + "o", label_visibility="collapsed")
    with o2:
        nd = st.date_input("new date", value=today, key=key + "d",
                           label_visibility="collapsed")
    with o3:
        if st.button("Save", key=key + "s"):
            if out == "Reschedule":
                c["promised"] = nd.isoformat()
                c["status"] = "open"
            else:
                c["status"] = OUTCOME_MAP[out]
                if out != "Still open":
                    c["outcome_date"] = today.isoformat()
            D.save_clients(st.session_state["clients"])
            st.rerun()


def _section(title, clients, today, key):
    if not clients:
        return
    st.markdown('<div class="tw-lab" style="margin:12px 0 8px">'
                + title.upper() + ' &middot; ' + str(len(clients))
                + '</div>', unsafe_allow_html=True)
    for c in clients:
        st.markdown(UI.client_card(c, today), unsafe_allow_html=True)
        _outcome_controls(c, today, key + c["id"])


def render(ctx):
    clients, today = ctx["clients"], ctx["today"]
    t_iso = ctx["today_iso"]
    cc = M.client_counts(clients, today)

    row = [
        UI.tile("Due Today", str(len(cc["due"])), "call now",
                "win" if cc["due"] else "mute",
                "win" if cc["due"] else "ink", "clock", "win", 0),
        UI.tile("Overdue", str(len(cc["over"])), "promised earlier",
                "loss" if cc["over"] else "mute",
                "loss" if cc["over"] else "ink", "bolt", "loss", 40),
        UI.tile("Next 7 Days", str(len(cc["up"])), "upcoming",
                "mute", "ink", "cal", "accent", 80),
        UI.tile("Open Pipeline", str(cc["open"]), "active inquiries",
                "mute", "ink", "users", "accent", 120),
        UI.tile("Sold", str(cc["sold"]), "since Aug 1",
                "win", "win", "check", "win", 160),
        UI.tile("Rejected", str(cc["rej"]), "system + cash-only",
                "mute", "ink", "x", "jewel", 200),
    ]
    st.markdown(UI.tiles_grid(row, 6), unsafe_allow_html=True)

    with st.expander("+  Log a client inquiry"):
        a, b, c3 = st.columns(3)
        with a:
            name = st.text_input("Client name", key="cl_n")
            phone = st.text_input("Phone number", key="cl_p")
            want = st.text_input("Wants (phone / model)", key="cl_w")
        with b:
            budget = st.text_input("Budget (KSh)", key="cl_b")
            source = st.selectbox("Source", D.SOURCES, key="cl_s")
            heat = st.selectbox("Heat", D.HEATS, key="cl_h")
        with c3:
            promised = st.date_input("Promised / follow-up date",
                                     value=today, key="cl_d")
            remark = st.text_input("Remark (when they'll need it)",
                                   key="cl_r")
            why_not = st.text_input("Why not today?", key="cl_y")
        if st.button("Add to pipeline", type="primary",
                     key="cl_add") and name.strip():
            D.add_client({
                "name": name.strip(), "phone": phone.strip(),
                "want": want.strip(), "budget": budget.strip(),
                "source": source, "heat": heat,
                "created": t_iso, "promised": promised.isoformat(),
                "remark": remark.strip(),
                "why_not": why_not.strip(),
            })
            st.rerun()

    _section("Overdue - they promised earlier", cc["over"], today, "ov")
    _section("Due today", cc["due"], today, "du")
    _section("Upcoming - next 7 days", cc["up"], today, "up")

    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    rows = []
    for c in clients:
        st_chip = {"open": ("OPEN", "#4C8DFF"),
                   "sold": ("SOLD", "#34D399"),
                   "rejected_system": ("REJ - SYSTEM", "#F0556B"),
                   "rejected_cash": ("REJ - CASH", "#F5B544")}.get(
                       c.get("status"), ("?", "#7C8AA5"))
        rows.append([
            (c.get("created", ""), "num"),
            (str(c.get("name", "")), ""),
            (str(c.get("phone", "")), "num"),
            (str(c.get("want", "")), ""),
            (str(c.get("source", "")), ""),
            (c.get("promised", "") or "--", "num"),
            (UI.badge(st_chip[0], st_chip[1]), ""),
        ])
    st.markdown(UI.panel("All inquiries",
                         UI.table(["Logged", "Name", "Phone", "Wants",
                                   "Source", "Promised", "Status"],
                                  rows)), unsafe_allow_html=True)
