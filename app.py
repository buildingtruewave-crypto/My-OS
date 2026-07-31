"""PULSE — Life Command Center.  Entry point.

Run locally:   pip install -r requirements.txt && streamlit run app.py
Deploy:        see README.md (Streamlit Cloud, Docker, or systemd + nginx).
"""
from __future__ import annotations

import datetime as dt
from datetime import timedelta

import streamlit as st

from src import data as D, metrics as M, theme, ui as UI
from src.pages import (goals, habits, journal, now, routine, settings, stats,
                       tasks, trading)

st.set_page_config(page_title="PULSE — Life Command Center", page_icon="◉",
                   layout="wide", initial_sidebar_state="expanded")

D.ensure()

st.markdown(theme.CSS, unsafe_allow_html=True)
accent = st.session_state.get("accent", "#4C8DFF")
st.markdown("<style>:root{--accent:%s;--accent-soft:%s;}</style>"
            % (accent, D._rgba(accent) if hasattr(D, "_rgba") else _rgba(accent)),
            unsafe_allow_html=True)


def _rgba(hex_color):
    from src import util as U
    return U.hexa(hex_color, 0.16)


# ---------------------------------------------------------------- sidebar
NAV = [("◉", "Now"), ("▤", "Routine"), ("✓", "Habits"), ("◔", "Trading"),
       ("⚑", "Goals"), ("☑", "Tasks"), ("✎", "Journal"), ("◧", "Stats"), ("⚙", "Settings")]
OPTIONS = [f"{g}  {n}" for g, n in NAV]
PAGES = {"Now": now, "Routine": routine, "Habits": habits, "Trading": trading,
         "Goals": goals, "Tasks": tasks, "Journal": journal, "Stats": stats, "Settings": settings}

with st.sidebar:
    st.markdown(UI.brand_html(), unsafe_allow_html=True)
    sel = st.radio("nav", OPTIONS, index=0, label_visibility="collapsed", key="nav")
    st.markdown(UI.user_html(st.session_state.get("name", D.DEFAULT_NAME)), unsafe_allow_html=True)
page_name = sel.split()[-1]

# ---------------------------------------------------------------- context
today = dt.date.today()
offset = float(st.session_state.get("tz_offset", 0))
now_dt = dt.datetime.now() + timedelta(hours=offset)

routine = D.get("routine"); habits = D.get("habits"); log = D.get("habit_log")
goals = D.get("goals"); tasks = D.get("tasks"); journal = D.get("journal")
trades = D.get("trades"); start = st.session_state.get("start_balance", D.START_BALANCE)

today_blocks = M.today_blocks(routine, today.weekday())
active_idx, progress, current, next_block = M.active_block_info(today_blocks, now_dt)
trade = M.trade_summary(trades, start)

ctx = dict(today=today, now_dt=now_dt, routine=routine, today_blocks=today_blocks,
           active_idx=active_idx, progress=progress, current=current, next_block=next_block,
           habits=habits, habit_log=log, goals=goals, tasks=tasks, journal=journal,
           trades=trades, trade=trade, start=start, accent=accent,
           name=st.session_state.get("name", D.DEFAULT_NAME))

# ---------------------------------------------------------------- top bar
g, d, s = st.columns([5, 3, 2], gap="medium")
with g:
    st.markdown(UI.greeting_html(ctx["name"]), unsafe_allow_html=True)
with d:
    cons = M.overall_consistency(habits, log, 30)
    st.markdown(f'<div style="padding:.3rem 0"><div class="tw-lab">today</div>'
                f'<div style="font:700 18px/1.1 var(--disp);color:var(--ink)">'
                f'{today.strftime("%A")}</div>'
                f'<div class="tw-sub">{today.strftime("%b %d, %Y")}</div></div>',
                unsafe_allow_html=True)
with s:
    gavg = (sum(M.goal_pct(x) for x in goals) / len(goals)) if goals else 0.0
    jcomp = M.journal_completion(journal, 30)
    score = M.life_score(cons, jcomp, trade["wr"], gavg)
    tone = "tw-win" if score >= 70 else ("tw-loss" if score < 40 else "tw-accent")
    st.markdown(f'<div style="text-align:right;padding:.3rem 0"><div class="tw-lab">life score</div>'
                f'<div class="tw-val {tone}" style="font-size:30px">{score}</div></div>',
                unsafe_allow_html=True)

PAGES[page_name].render(ctx)
