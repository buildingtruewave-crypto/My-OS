from __future__ import annotations

import streamlit as st

from .. import metrics as M, ui as UI, util as U


def render(ctx):
    habits = ctx["habits"]; log = ctx["habit_log"]; goals = ctx["goals"]
    journal = ctx["journal"]; ts = ctx["trade"]

    cons = M.overall_consistency(habits, log, 30)
    jcomp = M.journal_completion(journal, 30)
    gavg = (sum(M.goal_pct(g) for g in goals) / len(goals)) if goals else 0.0
    score = M.life_score(cons, jcomp, ts["wr"], gavg)

    row = [
        UI.tile("Life Score", str(score), "composite · 0–100",
                "win" if score >= 70 else ("loss" if score < 40 else "mute"),
                "win" if score >= 70 else ("loss" if score < 40 else "ink"), "★", "jewel", 0),
        UI.tile("Consistency", U.fmt_pct(cons, False), "30-day habits", "mute", "ink", "✓", "win", 40),
        UI.tile("Journal", U.fmt_pct(jcomp, False), f'🔥 {M.journal_streak(journal)} day streak',
                "mute", "ink", "✎", "accent", 80),
        UI.tile("Trade Win Rate", U.fmt_pct(ts["wr"], False), f'{ts["n"]} trades', "mute", "ink", "◎", "jewel", 120),
        UI.tile("Goal Progress", U.fmt_pct(gavg, False), f'{len(goals)} active', "mute", "ink", "⚑", "accent", 160),
    ]
    st.markdown(UI.tiles_grid(row, 5), unsafe_allow_html=True)

    st.markdown(UI.streaks_html([
        (M.habit_streak(log, habits[0]["id"]) if habits else 0, (habits[0]["name"] if habits else "habit"), "win"),
        (M.journal_streak(journal), "journal days", "accent"),
        (ts["win_streak"], "trade wins", "win"),
        (ts["loss_streak"], "trade losses", "loss"),
    ]), unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        cwd = M.consistency_by_weekday(habits, log, 60)
        items = [(n, cwd[i] - 50, "#34D399" if cwd[i] >= 60 else ("#F0556B" if cwd[i] < 35 else "#F5B544"))
                 for i, n in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])]
        st.markdown(UI.panel("Consistency by Weekday", UI.hbars(items)), unsafe_allow_html=True)
    with c2:
        segs = [("Done", sum(1 for h in habits for d in _last30() if log.get(h["id"], {}).get(d)), "#34D399"),
                ("Missed", sum(1 for h in habits for d in _last30() if d in log.get(h["id"], {}) and not log.get(h["id"], {}).get(d)), "#F0556B")]
        tot = max(segs[0][1] + segs[1][1], 1)
        st.markdown(UI.panel("Habit Outcomes · 30d",
                             UI.donut(segs, str(tot), "checks", tot)), unsafe_allow_html=True)


def _last30():
    import datetime as dt
    today = dt.date.today()
    return [(today - dt.timedelta(days=o)).isoformat() for o in range(30)]
