from __future__ import annotations

import streamlit as st

from .. import data as D, metrics as M, ui as UI, util as U, widgets as W


def render(ctx):
    today = ctx["today"]; now_dt = ctx["now_dt"]
    blocks = ctx["today_blocks"]; idx = ctx["active_idx"]; prog = ctx["progress"]
    cur = ctx["current"]; nxt = ctx["next_block"]
    habits = ctx["habits"]; log = ctx["habit_log"]; goals = ctx["goals"]
    tasks = ctx["tasks"]; journal = ctx["journal"]; ts = ctx["trade"]

    st.markdown(UI.panel(today.strftime("%A · %b %d, %Y"),
                         UI.now_card(now_dt.strftime("%H:%M"), cur,
                                     cur.get("tag", "Life") if cur else "Life",
                                     D.TAG_COLORS.get(cur.get("tag", "Life"), "#7C8AA5") if cur else "#7C8AA5",
                                     prog,
                                     nxt["time"] if nxt else "--:--",
                                     nxt["label"] if nxt else ""), delay=0),
                unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        st.markdown(UI.panel("Today's Rhythm", UI.timeline_html(blocks, idx)),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(UI.panel("Today's Habits",
                             '<div id="hcheck"></div>', delay=40) if False else
                    UI.panel("Today's Habits", _habit_panel_body(ctx)),
                    unsafe_allow_html=True)
        W.habit_checklist("now", habits, log, today.isoformat())

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    g1, g2, g3 = st.columns(3, gap="medium")
    with g1:
        body = ""
        for g in goals[:3]:
            pct = M.goal_pct(g)
            color = "#34D399" if pct >= 80 else ("#F5B544" if pct >= 40 else "#F0556B")
            body += (f'<div class="tw-stat"><span class="k">{U.html_escape(g["title"])}</span>'
                     f'<span class="v" style="color:{color}">{pct:.0f}%</span></div>')
        st.markdown(UI.panel("Goals", body or '<div class="tw-empty">No goals.</div>', delay=0),
                    unsafe_allow_html=True)
    with g2:
        tone = "tw-win" if ts["today_pnl"] >= 0 else "tw-loss"
        body = (f'<div class="tw-stat"><span class="k">Today PnL</span>'
                f'<span class="v {tone}">{U.fmt_money(ts["today_pnl"], True)}</span></div>'
                f'<div class="tw-stat"><span class="k">Win streak</span>'
                f'<span class="v tw-win">{ts["win_streak"]}</span></div>'
                f'<div class="tw-stat"><span class="k">Loss streak</span>'
                f'<span class="v tw-loss">{ts["loss_streak"]}</span></div>'
                f'<div class="tw-stat"><span class="k">Win rate</span>'
                f'<span class="v">{U.fmt_pct(ts["wr"], False)}</span></div>')
        st.markdown(UI.panel("Trading", body, delay=60), unsafe_allow_html=True)
    with g3:
        latest = sorted(journal.items(), reverse=True)
        if latest:
            d, e = latest[0]
            st.markdown(UI.panel("Last Reflection", UI.journal_card(d, e), delay=120),
                        unsafe_allow_html=True)
        else:
            st.markdown(UI.panel("Last Reflection",
                                 '<div class="tw-empty">Write today\'s entry in Journal.</div>', delay=120),
                        unsafe_allow_html=True)


def _habit_panel_body(ctx):
    log = ctx["habit_log"]; today = ctx["today"]; habits = ctx["habits"]
    done = sum(1 for h in habits if log.get(h["id"], {}).get(today.isoformat()))
    total = len(habits)
    pct = done / total * 100 if total else 0
    tone = "tw-win" if pct >= 70 else ("tw-loss" if pct < 40 else "tw-ink")
    return (f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px">'
            f'<span class="tw-val {tone}" style="font-size:22px">{done}/{total}</span>'
            f'<span class="tw-lab">done today · {pct:.0f}%</span></div>')


# tiny alias so the goals panel can escape without importing html everywhere
import html as _html
U.html_escape = _html.escape
