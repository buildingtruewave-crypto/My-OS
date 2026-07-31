"""Deriv + Alpaca bots and any other venture: risk taken, what it gave
back, and the demo-to-real transition - reviewed weekly and monthly."""
from __future__ import annotations

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI

_STATUS = {"testing": ("TESTING", "#F5B544"),
           "demo": ("DEMO", "#7C8AA5"),
           "live": ("LIVE", "#34D399")}


def render(ctx):
    bots, today = ctx["bots"], ctx["today"]
    blist, logs = bots["bots"], bots["logs"]

    all_pnl = sum(float(l["pnl"]) for l in logs)
    wins = sum(1 for l in logs if float(l["pnl"]) > 0)
    wr = (wins / len(logs) * 100) if logs else 0.0
    row = [
        UI.tile("Ventures Running", str(len(blist)), "tracked",
                "mute", "ink", "bot", "accent", 0),
        UI.tile("Logs Recorded", str(len(logs)), "since Aug 1",
                "mute", "ink", "list", "accent", 40),
        UI.tile("Net Result", format(all_pnl, "+,.0f"),
                "all ventures", "win" if all_pnl >= 0 else "loss",
                "win" if all_pnl >= 0 else "loss", "trend", "win",
                80),
        UI.tile("Win Rate", format(wr, ".0f") + "%", "all logs",
                "mute", "ink", "target", "jewel", 120),
    ]
    st.markdown(UI.tiles_grid(row, 4), unsafe_allow_html=True)

    cols = st.columns(min(max(len(blist), 1), 2), gap="medium")
    for i, b in enumerate(blist):
        s = M.bot_stats(logs, b["id"])
        st_chip = _STATUS.get(b["status"], ("?", "#7C8AA5"))
        with cols[i % len(cols)]:
            body = UI.kv([
                ("Platform", b.get("platform", "")),
                ("Status", UI.badge(st_chip[0], st_chip[1])
                 + ("  since " + b["live_date"]
                    if b.get("live_date") else "")),
                ("Logs", str(s["n"]) + "  (" + str(s["w"]) + "W / "
                 + str(s["l"]) + "L)"),
                ("Win rate", format(s["wr"], ".0f") + "%"),
                ("Net PnL", '<span class="'
                 + ("tw-win" if s["pnl"] >= 0 else "tw-loss") + '">'
                 + format(s["pnl"], "+,.2f") + "</span>"),
                ("Risk deployed", format(s["risk"], ",.2f")),
                ("Reward : Risk", format(s["rr"], ".2f") + " : 1"),
            ])
            st.markdown(UI.panel(b["name"], body),
                        unsafe_allow_html=True)
            if b["status"] != "live":
                if st.button("Transition to LIVE",
                             key="bl" + b["id"]):
                    D.set_bot_status(b["id"], "live",
                                     ctx["today_iso"])
                    st.rerun()
            recent = [l for l in logs if l["bot"] == b["id"]][:5]
            if recent:
                rows = []
                for l in recent:
                    tone = "tw-win" if float(l["pnl"]) >= 0 else \
                        "tw-loss"
                    rows.append([
                        (l["date"], "num"),
                        (format(float(l["risk"]), ",.2f"), "num"),
                        ('<span class="' + tone + '">'
                         + format(float(l["pnl"]), "+,.2f")
                         + "</span>", "num"),
                        (str(l.get("notes", "")), ""),
                    ])
                st.markdown(UI.table(["Date", "Risk", "PnL", "Notes"],
                                     rows), unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    e1, e2 = st.columns(2, gap="medium")
    with e1:
        st.markdown(UI.panel("Log Today's Run",
                             '<div style="height:2px"></div>'),
                    unsafe_allow_html=True)
        a, b = st.columns(2)
        with a:
            ld = st.date_input("Date", value=today, key="bg_d")
            bot_id = st.selectbox(
                "Venture", [x["id"] for x in blist],
                format_func=lambda i: next(
                    (x["name"] for x in blist if x["id"] == i), i),
                key="bg_b")
        with b:
            risk = st.number_input("Risk taken", 0.0, 10000000.0,
                                   0.0, step=1.0, key="bg_r")
            pnl = st.number_input("Result (+win / -loss)",
                                  -10000000.0, 10000000.0, 0.0,
                                  step=1.0, key="bg_p")
        notes = st.text_input("Notes (strategy, behaviour, fixes)",
                              key="bg_n")
        if st.button("Add log", type="primary", key="bg_add"):
            D.add_bot_log(ld.isoformat(), bot_id, risk, pnl,
                          notes.strip())
            st.rerun()
    with e2:
        st.markdown(UI.panel("Add a Venture",
                             '<div style="height:2px"></div>'),
                    unsafe_allow_html=True)
        nm = st.text_input("Name (e.g. TrueWave inventory, HHO test)",
                           key="ba_n")
        pf = st.text_input("Platform / area", key="ba_p")
        if st.button("Add venture", type="primary",
                     key="ba_add") and nm.strip():
            D.add_bot(nm.strip(), pf.strip())
            st.rerun()
        st.markdown(UI.panel(
            "This Week - all ventures",
            UI.bars(M.bot_week(logs, today, 7)), right="net per day"),
            unsafe_allow_html=True)
