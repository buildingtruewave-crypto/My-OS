from __future__ import annotations

import datetime as dt

import streamlit as st

from .. import metrics as M
from .. import ui as UI
from .. import util as U


def _last30():
    today = dt.date.today()
    out = []
    for o in range(30):
        day = today - dt.timedelta(days=o)
        out.append(day.isoformat())
    return out


def render(ctx):
    habits = ctx["habits"]
    log = ctx["habit_log"]
    goals = ctx["goals"]
    journal = ctx["journal"]
    ts = ctx["trade"]

    cons = M.overall_consistency(habits, log, 30)
    jcomp = M.journal_completion(journal, 30)
    if goals:
        gavg = sum(M.goal_pct(g) for g in goals) / len(goals)
    else:
        gavg = 0.0
    score = M.life_score(cons, jcomp, ts["wr"], gavg)
    n_trades = ts["n"]
    n_goals = len(goals)
    jstreak = M.journal_streak(journal)

    if score >= 70:
        s_d = "win"
        s_v = "win"
    elif score < 40:
        s_d = "loss"
        s_v = "loss"
    else:
        s_d = "mute"
        s_v = "ink"

    row = [
        UI.tile("Life Score", str(score),
                "composite 0-100", s_d, s_v,
                "*", "jewel", 0),
        UI.tile("Consistency", U.fmt_pct(cons, False),
                "30-day habits", "mute", "ink",
                "v", "win", 40),
        UI.tile("Journal", U.fmt_pct(jcomp, False),
                "streak " + str(jstreak), "mute",
                "ink", "j", "accent", 80),
        UI.tile("Trade Win Rate",
                U.fmt_pct(ts["wr"], False),
                str(n_trades) + " trades", "mute",
                "ink", "@", "jewel", 120),
        UI.tile("Goal Progress",
                U.fmt_pct(gavg, False),
                str(n_goals) + " active", "mute",
                "ink", "g", "accent", 160),
    ]
    st.markdown(UI.tiles_grid(row, 5),
                unsafe_allow_html=True)

    if habits:
        first_name = habits[0]["name"]
        first_streak = M.habit_streak(log, habits[0]["id"])
    else:
        first_name = "habit"
        first_streak = 0
    st.markdown(
        UI.streaks_html([
            (first_streak, first_name, "win"),
            (jstreak, "journal days", "accent"),
            (ts["win_streak"], "trade wins", "win"),
            (ts["loss_streak"], "trade losses", "loss"),
        ]),
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        cwd = M.consistency_by_weekday(habits, log, 60)
        names = ["Mon", "Tue", "Wed", "Thu",
                 "Fri", "Sat", "Sun"]
        items = []
        for i, nm in enumerate(names):
            v = cwd[i]
            if v >= 60:
                color = "#34D399"
            elif v < 35:
                color = "#F0556B"
            else:
                color = "#F5B544"
            items.append((nm, v - 50, color))
        st.markdown(
            UI.panel("Consistency by Weekday",
                     UI.hbars(items)),
            unsafe_allow_html=True,
        )
    with c2:
        last = _last30()
        done = 0
        missed = 0
        for h in habits:
            s = log.get(h["id"], {})
            for d in last:
                if s.get(d):
                    done += 1
                elif d in s:
                    missed += 1
        segs = [("Done", done, "#34D399"),
                ("Missed", missed, "#F0556B")]
        tot = max(done + missed, 1)
        st.markdown(
            UI.panel("Habit Outcomes - 30d",
                     UI.donut(segs, str(tot),
                              "checks", tot)),
            unsafe_allow_html=True,
        )
