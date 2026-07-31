from __future__ import annotations

import streamlit as st

from .. import metrics as M
from .. import ui as UI
from .. import util as U

WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def render(ctx):
    habits = ctx["habits"]
    log = ctx["habit_log"]
    goals = ctx["goals"]
    journal = ctx["journal"]
    ts = ctx["trade"]
    trades = ctx["trades"]

    cons = M.overall_consistency(habits, log, 30)
    jcomp = M.journal_completion(journal, 30)
    if goals:
        gavg = sum(M.goal_pct(g) for g in goals) / len(goals)
    else:
        gavg = 0.0
    score = M.life_score(cons, jcomp, ts["wr"], gavg)
    jstreak = M.journal_streak(journal)

    if score >= 70:
        s_d, s_v = "win", "win"
    elif score < 40:
        s_d, s_v = "loss", "loss"
    else:
        s_d, s_v = "mute", "ink"

    row = [
        UI.tile("Life Score", str(score), "composite 0-100", s_d, s_v,
                "star", "jewel", 0),
        UI.tile("Consistency", U.fmt_pct(cons, False), "30-day habits",
                "mute", "ink", "pulse", "win", 40),
        UI.tile("Journal", U.fmt_pct(jcomp, False),
                "streak " + str(jstreak), "mute", "ink",
                "edit", "accent", 80),
        UI.tile("Trade Win Rate", U.fmt_pct(ts["wr"], False),
                str(ts["n"]) + " trades", "mute", "ink",
                "target", "jewel", 120),
        UI.tile("Goal Progress", U.fmt_pct(gavg, False),
                str(len(goals)) + " active", "mute", "ink",
                "flag", "accent", 160),
    ]
    st.markdown(UI.tiles_grid(row, 5), unsafe_allow_html=True)

    first_name = habits[0]["name"] if habits else "habit"
    first_streak = M.habit_streak(log, habits[0]["id"]) if habits else 0
    st.markdown(
        UI.streaks_html([
            (first_streak, first_name, "win"),
            (jstreak, "journal days", "accent"),
            (ts["win_streak"], "trade wins", "win"),
            (ts["loss_streak"], "trade losses", "loss"),
        ]),
        unsafe_allow_html=True,
    )

    # consistency trend line (the glowing spine, in %)
    series = M.consistency_series(log, habits, 30)
    st.markdown(
        UI.panel("Consistency Trend",
                 UI.equity_svg(series, "st_eq", kind="pct",
                               xfmt=lambda d: d.strftime("%d")),
                 right="last 30 days"),
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        cwd = M.consistency_by_weekday(habits, log, 60)
        items = []
        for i, nm in enumerate(WEEK):
            v = cwd[i]
            if v >= 60:
                color = "#34D399"
            elif v < 35:
                color = "#F0556B"
            else:
                color = "#F5B544"
            items.append((nm, v - 50, color))
        st.markdown(UI.panel("Consistency by Weekday",
                             UI.hbars(items)),
                    unsafe_allow_html=True)
    with c2:
        mat = M.trade_heatmap(trades)
        st.markdown(
            UI.panel("Trading - Weekday x Session",
                     UI.heatmap_html(mat, WEEK, M.HOUR_BUCKETS)),
            unsafe_allow_html=True,
        )

    c3, c4 = st.columns(2, gap="medium")
    with c3:
        last = [(today_iso(o)) for o in range(30)]
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
                     UI.donut(segs, str(tot), "checks", tot)),
            unsafe_allow_html=True,
        )
    with c4:
        body = (
            '<div class="tw-stat"><span class="k">Life score formula</span>'
            + '<span class="v">40/20/20/20</span></div>'
            + '<div class="tw-stat"><span class="k">Consistency weight</span>'
            + '<span class="v">40%</span></div>'
            + '<div class="tw-stat"><span class="k">Journal weight</span>'
            + '<span class="v">20%</span></div>'
            + '<div class="tw-stat"><span class="k">Trade win weight</span>'
            + '<span class="v">20%</span></div>'
            + '<div class="tw-stat"><span class="k">Goal weight</span>'
            + '<span class="v">20%</span></div>'
        )
        st.markdown(UI.panel("How the Score Works", body),
                    unsafe_allow_html=True)


def today_iso(o):
    import datetime as dt
    return (dt.date.today() - dt.timedelta(days=o)).isoformat()
