from __future__ import annotations

import html

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U
from .. import widgets as W


def _today_head(habits, log, today):
    done = 0
    for h in habits:
        if log.get(h["id"], {}).get(today.isoformat()):
            done += 1
    total = len(habits)
    pct = (done / total * 100) if total else 0
    if pct >= 70:
        tone = "tw-win"
    elif pct < 40:
        tone = "tw-loss"
    else:
        tone = "tw-ink"
    return (
        '<div style="display:flex;'
        + 'justify-content:space-between;'
        + 'align-items:baseline">'
        + '<span class="tw-val ' + tone
        + '" style="font-size:22px">'
        + str(done) + '/' + str(total) + '</span>'
        + '<span class="tw-lab">done today - '
        + format(pct, ".0f") + '%</span></div>'
    )


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

    if cur:
        cur_tag = cur.get("tag", "Life")
        cur_color = D.TAG_COLORS.get(cur_tag, "#7C8AA5")
    else:
        cur_tag = "Life"
        cur_color = "#7C8AA5"
    nxt_time = nxt["time"] if nxt else "--:--"
    nxt_label = nxt["label"] if nxt else ""

    title = today.strftime("%A - %b %d, %Y")
    now_html = UI.now_card(
        now_dt.strftime("%H:%M"), cur, cur_tag,
        cur_color, prog, nxt_time, nxt_label,
    )
    st.markdown(UI.panel(title, now_html, delay=0),
                unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        st.markdown(
            UI.panel("Today's Rhythm",
                     UI.timeline_html(blocks, idx)),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            UI.panel("Today's Habits",
                     _today_head(habits, log, today),
                     delay=40),
            unsafe_allow_html=True,
        )
        W.habit_checklist("now", habits, log,
                          today.isoformat())

    st.markdown("<div style='height:6px'></div>",
                unsafe_allow_html=True)
    g1, g2, g3 = st.columns(3, gap="medium")
    with g1:
        body = []
        for g in goals[:3]:
            pct = M.goal_pct(g)
            if pct >= 80:
                color = "#34D399"
            elif pct >= 40:
                color = "#F5B544"
            else:
                color = "#F0556B"
            gt = html.escape(g["title"])
            body.append(
                '<div class="tw-stat"><span class="k">'
                + gt + '</span>'
                + '<span class="v" style="color:'
                + color + '">' + format(pct, ".0f")
                + '%</span></div>'
            )
        gbody = "".join(body)
        if not gbody:
            gbody = '<div class="tw-empty">No goals.</div>'
        st.markdown(UI.panel("Goals", gbody, delay=0),
                    unsafe_allow_html=True)
    with g2:
        if ts["today_pnl"] >= 0:
            tone = "tw-win"
        else:
            tone = "tw-loss"
        body = (
            '<div class="tw-stat"><span class="k">Today PnL</span>'
            + '<span class="v ' + tone + '">'
            + U.fmt_money(ts["today_pnl"], True)
            + '</span></div>'
            + '<div class="tw-stat"><span class="k">Win streak</span>'
            + '<span class="v tw-win">'
            + str(ts["win_streak"]) + '</span></div>'
            + '<div class="tw-stat"><span class="k">Loss streak</span>'
            + '<span class="v tw-loss">'
            + str(ts["loss_streak"]) + '</span></div>'
            + '<div class="tw-stat"><span class="k">Win rate</span>'
            + '<span class="v">'
            + U.fmt_pct(ts["wr"], False) + '</span></div>'
        )
        st.markdown(UI.panel("Trading", body, delay=60),
                    unsafe_allow_html=True)
    with g3:
        latest = sorted(journal.items(), reverse=True)
        if latest:
            d, e = latest[0]
            st.markdown(
                UI.panel("Last Reflection",
                         UI.journal_card(d, e), delay=120),
                unsafe_allow_html=True,
            )
        else:
            empty = (
                '<div class="tw-empty">'
                + "Write today's entry in Journal.</div>"
            )
            st.markdown(
                UI.panel("Last Reflection", empty, delay=120),
                unsafe_allow_html=True,
            )
