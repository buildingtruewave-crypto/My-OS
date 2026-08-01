"""The day's record. The Day Pulse is picked up automatically from every
module - including spiritual energy - so the journal never asks twice.
"""
from __future__ import annotations

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U


def _pulse_html(p):
    pairs = []
    if p["new_clients"]:
        names = ", ".join(c["name"] for c in p["new_clients"])
        pairs.append(("New inquiries", str(len(p["new_clients"]))
                      + " - " + names))
    if p["followups"]:
        names = ", ".join(c["name"] for c in p["followups"])
        pairs.append(("Follow-ups due", str(len(p["followups"]))
                      + " - " + names))
    if p["moves"]:
        bits = []
        for name, h in p["moves"][:8]:
            bits.append(name + ": " + str(h.get("note", "")))
        pairs.append(("Client touches", " | ".join(bits)))
    if p["outcomes"]:
        names = ", ".join(c["name"] for c in p["outcomes"])
        pairs.append(("Deals closed / returned", names))
    if p["daily"]:
        e = p["daily"]
        pairs.append(("Sales tally",
                      str(e.get("sold", 0)) + " sold - "
                      + str(e.get("system_rej", 0)) + " sys-rej - "
                      + str(e.get("cash_rej", 0)) + " cash-rej"))
    if p["sales"]:
        pairs.append(("Sales logged", str(len(p["sales"]))))
    if p["inst_due"]:
        pairs.append(("Commissions due", str(len(p["inst_due"]))))
    if p["income"]:
        tot = sum(float(x.get("amount", 0)) for x in p["income"])
        pairs.append(("Money in", U.fmt_kes(tot) + " - "
                      + ", ".join(x.get("type", "")
                                  for x in p["income"])))
    if p["flow"]:
        net = sum(M.flow_effect(f) for f in p["flow"])
        pairs.append(("Daily flow", str(len(p["flow"]))
                      + " entries - net " + U.fmt_kes(net, True)))
    if p.get("spiritual") is not None:
        pairs.append(("Spirit energy", str(p["spiritual"])))
    if p["bot_logs"]:
        net = sum(float(l["pnl"]) for l in p["bot_logs"])
        pairs.append(("Bot logs", str(len(p["bot_logs"]))
                      + " - net " + format(net, "+,.0f")))
    if p["tasks_done"]:
        pairs.append(("Tasks cleared", str(len(p["tasks_done"]))))
    if p["weight"]:
        pairs.append(("Weigh-in",
                      U.fmt_num(p["weight"]["kg"]) + " kg"))
    return UI.kv(pairs)


def render(ctx):
    journal, today = ctx["journal"], ctx["today"]
    streak = M.journal_streak(journal)
    comp = M.journal_completion(journal, 30)

    row = [
        UI.tile("Current Streak", str(streak), "consecutive days",
                "win" if streak else "mute",
                "win" if streak else "ink", "flame", "jewel", 0),
        UI.tile("30-day Completion", U.fmt_pct(comp, False),
                "consistency", "win" if comp >= 70 else "mute",
                "win" if comp >= 70 else "ink", "check", "win", 40),
        UI.tile("Total Entries", str(len(journal)), "since Aug 1",
                "mute", "ink", "edit", "accent", 80),
        UI.tile("Sales Streak",
                str(M.sales_streak(ctx["sales_daily"], today)),
                "days with a tally", "mute", "ink", "phone",
                "accent", 120),
    ]
    st.markdown(UI.tiles_grid(row, 4), unsafe_allow_html=True)

    day = st.date_input("Date", value=today, key="j_date")
    key = day.isoformat()
    cur = journal.get(key, {})

    p = M.day_pulse(key, ctx)
    st.markdown(UI.panel("Day Pulse - picked up automatically",
                         _pulse_html(p), right=key),
                unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>",
                unsafe_allow_html=True)
    st.markdown(UI.panel("Write the Day",
                         '<div style="height:2px"></div>'),
                unsafe_allow_html=True)
    happened = st.text_area("What happened today?",
                            value=cur.get("happened", ""), height=90,
                            key="j_h")
    a, b, c = st.columns(3)
    with a:
        win = st.text_input("Win", value=cur.get("win", ""),
                            key="j_w")
    with b:
        lesson = st.text_input("Lesson", value=cur.get("lesson", ""),
                               key="j_l")
    with c:
        mood_idx = D.MOODS.index(cur["mood"]) \
            if cur.get("mood") in D.MOODS else 2
        mood = st.selectbox("Mood", D.MOODS, index=mood_idx,
                            key="j_m")
    s1, s2, _ = st.columns([1, 1, 4])
    with s1:
        if st.button("Save entry", type="primary", key="j_save"):
            j = dict(journal)
            if any([happened, win, lesson]):
                j[key] = {"happened": happened, "win": win,
                          "lesson": lesson, "mood": mood}
            else:
                j.pop(key, None)
            D.save_journal(j)
            st.success("Saved.")
            st.rerun()
    with s2:
        if st.button("Clear", key="j_clear"):
            j = dict(journal)
            j.pop(key, None)
            D.save_journal(j)
            st.rerun()

    st.markdown("<div style='height:8px'></div>",
                unsafe_allow_html=True)
    recent = sorted(journal.items(), reverse=True)[:12]
    if recent:
        st.markdown(UI.panel(
            "Recent entries",
            "".join(UI.journal_card(d, e) for d, e in recent)),
            unsafe_allow_html=True)
    else:
        st.markdown(UI.panel("Recent entries", UI.empty_state(
            "Your first entry lands tomorrow, Aug 1.")),
            unsafe_allow_html=True)
