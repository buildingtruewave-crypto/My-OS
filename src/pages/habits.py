from __future__ import annotations

import datetime as dt

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U
from .. import widgets as W


def _today_done(habits, log, today):
    done = 0
    for h in habits:
        if log.get(h["id"], {}).get(today.isoformat()):
            done += 1
    return done


def render(ctx):
    habits = ctx["habits"]
    log = ctx["habit_log"]
    today = ctx["today"]
    dates = [today - dt.timedelta(days=o) for o in range(34, -1, -1)]
    cons = M.overall_consistency(habits, log, 30)
    done_today = _today_done(habits, log, today)
    total_h = len(habits)
    best = M.best_habit_streak(log, habits)

    row = [
        UI.tile("Consistency 30d", U.fmt_pct(cons, False), "all habits",
                "win" if cons >= 70 else "mute",
                "win" if cons >= 70 else "ink", "pulse", "win", 0),
        UI.tile("Done Today",
                str(done_today) + "/" + str(total_h), "checked",
                "mute", "ink", "check", "accent", 40),
        UI.tile("Best Streak", str(best), "single habit",
                "win", "win", "flame", "jewel", 80),
        UI.tile("Habits Tracked", str(total_h), "active",
                "mute", "ink", "grid", "accent", 120),
    ]
    st.markdown(UI.tiles_grid(row, 4), unsafe_allow_html=True)

    st.markdown(
        UI.panel("Consistency Wall - last 35 days",
                 UI.habit_grid(habits, log, dates, today),
                 right="green = done"),
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    c1, c2 = st.columns([2, 3], gap="medium")
    with c1:
        pct = (done_today / total_h * 100) if total_h else 0
        tone = "tw-win" if pct >= 70 else ("tw-loss" if pct < 40 else "tw-ink")
        head = (
            '<div style="display:flex;justify-content:space-between;'
            + 'align-items:baseline">'
            + '<span class="tw-val ' + tone + '" style="font-size:24px">'
            + str(done_today) + '/' + str(total_h) + '</span>'
            + '<span class="tw-lab">' + format(pct, ".0f")
            + '% today</span></div>'
        )
        st.markdown(UI.panel("Today", head), unsafe_allow_html=True)
        W.habit_checklist("hab", habits, log, today.isoformat())
    with c2:
        items = []
        for h in habits:
            _d, _t, hpct, streak = M.habit_stats(log, h["id"], 30)
            if hpct >= 70:
                color = "#34D399"
            elif hpct < 40:
                color = "#F0556B"
            else:
                color = "#F5B544"
            label = (h["icon"] + "  " + h["name"] + "  -  streak "
                     + str(streak))
            items.append((label, hpct - 50, color))
        st.markdown(UI.panel("30-day completion", UI.hbars(items)),
                    unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>",
                unsafe_allow_html=True)
    st.markdown(
        '<div class="tw-lab" style="margin:4px 0 8px">EDIT HABITS</div>',
        unsafe_allow_html=True,
    )
    st.caption("One per line:  icon  Name   e.g.  W  Workout")
    txt = st.text_area(
        "habits", value=D.habits_to_text(habits), height=200,
        label_visibility="collapsed", key="hb_text",
    )
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
