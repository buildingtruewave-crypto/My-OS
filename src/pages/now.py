"""The dashboard.  Mirrors the reference composition:
5 KPIs -> 2-col hero -> 8 stat tiles -> 3-col row -> recent + streaks."""
from __future__ import annotations

import html

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
    today = ctx["today"]
    now_dt = ctx["now_dt"]
    blocks = ctx["today_blocks"]
    idx = ctx["active_idx"]
    prog = ctx["progress"]
    cur = ctx["current"]
    nxt = ctx["next_block"]
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
    done_today = _today_done(habits, log, today)
    total_h = len(habits)
    jstreak = M.journal_streak(journal)

    # ---- row 1: five KPI tiles ----
    row1 = [
        UI.tile("Life Score", str(score), "composite 0-100",
                "win" if score >= 70 else "mute",
                "win" if score >= 70 else "ink",
                "star", "jewel", 0),
        UI.tile("Consistency", U.fmt_pct(cons, False), "30-day habits",
                "win", "win", "pulse", "win", 40),
        UI.tile("Today's Habits",
                str(done_today) + "/" + str(total_h),
                "checked today", "mute", "ink",
                "check", "accent", 80),
        UI.tile("Trading Today",
                U.fmt_money(ts["today_pnl"], True),
                str(ts["today_n"]) + " trade(s)",
                "win" if ts["today_pnl"] >= 0 else "loss",
                "win" if ts["today_pnl"] >= 0 else "loss",
                "trend", "accent", 120),
        UI.tile("Journal Streak", str(jstreak), "consecutive days",
                "win", "win", "flame", "jewel", 160),
    ]
    st.markdown(UI.tiles_grid(row1, 5), unsafe_allow_html=True)

    # ---- row 2: hero line + right-now card ----
    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        series = M.consistency_series(log, habits, 30)
        svg = UI.equity_svg(series, "now_eq", kind="pct",
                            xfmt=lambda d: d.strftime("%d"))
        st.markdown(UI.panel("Consistency Trend", svg,
                             right="last 30 days"),
                    unsafe_allow_html=True)
    with c2:
        if cur:
            cur_tag = cur.get("tag", "Life")
            cur_color = D.TAG_COLORS.get(cur_tag, "#7C8AA5")
        else:
            cur_tag = "Life"
            cur_color = "#7C8AA5"
        nxt_time = nxt["time"] if nxt else "--:--"
        nxt_label = nxt["label"] if nxt else ""
        st.markdown(
            UI.panel("Right Now",
                     UI.now_card(now_dt.strftime("%H:%M"), cur,
                                 cur_tag, cur_color, prog,
                                 nxt_time, nxt_label)),
            unsafe_allow_html=True,
        )

    # ---- row 3: eight stat tiles ----
    on, at, gdone = M.goal_buckets(goals)
    open_t, total_t = M.task_counts(ctx["tasks"])
    row3 = [
        UI.tile("Habits", str(total_h), "tracked", "mute", "ink",
                "grid", "accent", 0),
        UI.tile("Done Today", str(done_today), "checked",
                "win", "win", "check", "win", 30),
        UI.tile("Missed Today", str(total_h - done_today), "open",
                "loss", "loss", "x", "loss", 60),
        UI.tile("Best Streak", str(M.best_habit_streak(log, habits)),
                "habits", "win", "win", "flame", "win", 90),
        UI.tile("Journal 30d", U.fmt_pct(jcomp, False), "completion",
                "mute", "ink", "edit", "accent", 120),
        UI.tile("Win Rate", U.fmt_pct(ts["wr"], False),
                str(ts["n"]) + " trades", "mute", "ink",
                "target", "jewel", 150),
        UI.tile("Goals On Track", str(on),
                str(gdone) + " done - " + str(at) + " at risk",
                "mute", "ink", "flag", "accent", 180),
        UI.tile("Tasks Open", str(open_t),
                str(total_t) + " total", "mute", "ink",
                "list", "accent", 210),
    ]
    st.markdown(UI.tiles_grid(row3, 8), unsafe_allow_html=True)

    # ---- row 4: calendar + today summary + focus donut ----
    y, m = today.year, today.month
    c3, c4, c5 = st.columns([5, 3, 4], gap="medium")
    with c3:
        cmap = M.day_consistency_map(log, habits, y, m, today)
        st.markdown(
            UI.panel("Consistency Calendar",
                     UI.calendar_html(y, m, cmap, today=today, pct=True),
                     right=today.strftime("%B")),
            unsafe_allow_html=True,
        )
    with c4:
        today_entry = journal.get(today.isoformat())
        mood = today_entry.get("mood", "-") if today_entry else "-"
        journ = "Yes" if today_entry else "No"
        body = (
            '<div class="tw-stat"><span class="k">Blocks done</span>'
            + '<span class="v">' + str(max(idx + 1, 0)) + ' / '
            + str(len(blocks)) + '</span></div>'
            + '<div class="tw-stat"><span class="k">Habits done</span>'
            + '<span class="v tw-win">' + str(done_today) + ' / '
            + str(total_h) + '</span></div>'
            + '<div class="tw-stat"><span class="k">Journaled</span>'
            + '<span class="v">' + html.escape(journ) + '</span></div>'
            + '<div class="tw-stat"><span class="k">Trades today</span>'
            + '<span class="v">' + str(ts["today_n"]) + '</span></div>'
            + '<div class="tw-stat"><span class="k">Mood</span>'
            + '<span class="v">' + html.escape(mood) + '</span></div>'
        )
        st.markdown(UI.panel("Today", body, right="live"),
                    unsafe_allow_html=True)
    with c5:
        split = M.today_area_split(ctx["routine"], today.weekday())
        total_b = sum(s[1] for s in split) or 1
        st.markdown(
            UI.panel("Focus Split Today",
                     UI.donut(split, str(total_b), "blocks", total_b)),
            unsafe_allow_html=True,
        )

    # ---- row 5: recent trades + streaks ----
    c6, c7 = st.columns([4, 1], gap="medium")
    with c6:
        rows = []
        for _, t in ts["recent"].iterrows():
            tone = "tw-win" if t["pnl"] >= 0 else "tw-loss"
            dtstr = t["dt"].strftime("%b %d %H:%M")
            dr = t["direction"]
            en = format(t["entry"], ",.4g")
            ex = format(t["exit"], ",.4g")
            lo = format(t["lots"], ".2f")
            pnl = U.fmt_money(t["pnl"], True)
            dirspan = ('<span class="tw-dir ' + dr + '">' + dr + '</span>')
            rows.append([
                (dtstr, "num"), (t["asset"], ""), (dirspan, ""),
                (en, "num"), (ex, "num"), (lo, "num"),
                (pnl, "num " + tone), (t["strategy"], ""),
            ])
        st.markdown(
            UI.panel("Recent Trades",
                     UI.table(["Time", "Asset", "Dir", "Entry", "Exit",
                               "Lots", "PnL", "Strategy"], rows)),
            unsafe_allow_html=True,
        )
    with c7:
        first_name = habits[0]["name"] if habits else "habit"
        first_streak = M.habit_streak(log, habits[0]["id"]) if habits else 0
        st.markdown(
            UI.panel("Streaks",
                     UI.streaks_html([
                         (first_streak, first_name, "win"),
                         (jstreak, "journal", "accent"),
                     ])),
            unsafe_allow_html=True,
        )

    # ---- today habits checklist (interactive) ----
    st.markdown("<div style='height:6px'></div>",
                unsafe_allow_html=True)
    hc1, hc2 = st.columns([2, 3], gap="medium")
    with hc1:
        pct = (done_today / total_h * 100) if total_h else 0
        tone = "tw-win" if pct >= 70 else ("tw-loss" if pct < 40 else "tw-ink")
        head = (
            '<div style="display:flex;justify-content:space-between;'
            + 'align-items:baseline">'
            + '<span class="tw-val ' + tone + '" style="font-size:22px">'
            + str(done_today) + '/' + str(total_h) + '</span>'
            + '<span class="tw-lab">' + format(pct, ".0f")
            + '% today</span></div>'
        )
        st.markdown(UI.panel("Tick Today's Habits", head),
                    unsafe_allow_html=True)
        W.habit_checklist("now", habits, log, today.isoformat())
    with hc2:
        st.markdown(
            UI.panel("Today's Rhythm",
                     UI.timeline_html(blocks, idx)),
            unsafe_allow_html=True,
        )
