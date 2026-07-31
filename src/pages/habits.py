from __future__ import annotations

import datetime as dt

import streamlit as st

from .. import data as D, metrics as M, ui as UI, widgets as W


def _today_head(habits, log, today):
    done = sum(1 for h in habits if log.get(h["id"], {}).get(today.isoformat()))
    total = len(habits)
    pct = (done / total * 100) if total else 0
    if pct >= 70:
        tone = "tw-win"
    elif pct < 40:
        tone = "tw-loss"
    else:
        tone = "tw-ink"
    return ('<div style="display:flex;justify-content:space-between;align-items:baseline">'
            '<span class="tw-val ' + tone + '" style="font-size:24px">' +
            str(done) + '/' + str(total) + '</span>'
            '<span class="tw-lab">' + format(pct, ".0f") + '% today</span></div>')


def render(ctx):
    habits = ctx["habits"]
    log = ctx["habit_log"]
    today = ctx["today"]
    dates = [today - dt.timedelta(days=o) for o in range(34, -1, -1)]

    st.markdown(UI.panel("Consistency Wall - last 35 days",
                         '<div class="tw-empty" style="padding:4px 0 12px;text-align:left">'
                         'The heartbeat of the app. Green = done, red = missed. '
                         'Tick today\'s habits below and the wall updates live.</div>'),
                unsafe_allow_html=True)
    st.markdown(UI.habit_grid(habits, log, dates, today), unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 3], gap="medium")
    with c1:
        st.markdown(UI.panel("Today", _today_head(habits, log, today)),
                    unsafe_allow_html=True)
        W.habit_checklist("hab", habits, log, today.isoformat())
    with c2:
        items = []
        for h in habits:
            done, total, pct, streak = M.habit_stats(log, h["id"], 30)
            if pct >= 70:
                color = "#34D399"
            elif pct < 40:
                color = "#F0556B"
            else:
                color = "#F5B544"
            label = h["icon"] + "  " + h["name"] + "  -  streak " + str(streak)
            items.append((label, pct - 50, color))
        st.markdown(UI.panel("30-day completion", UI.hbars(items)), unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="tw-lab" style="margin:4px 0 8px">EDIT HABITS</div>',
                unsafe_allow_html=True)
    st.caption("One per line:  icon  Name   e.g.  W  Workout")
    txt = st.text_area("habits", value=D.habits_to_text(habits), height=200,
                       label_visibility="collapsed", key="hb_text")
    a, b, _ = st.columns([1, 1, 4])
    with a:
        if st.button("Save habits", type="primary", key="hb_save"):
            parsed = D.parse_habits_text(txt)
            if parsed:
                D.save_habits(parsed)
                st.success("Saved " + str(len(parsed)) + " habits.")
                st.rerun()
    with b:
        if st.button("Reset to seed", key="hb_reset"):
            D.save_habits(D._seed_habits())
            st.rerun()
