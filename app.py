"""PULSE - Life Command Center.  Entry point.

Run locally:   pip install -r requirements.txt && streamlit run app.py
Deploy:        see README.md (Streamlit Cloud, Docker, or systemd + nginx).
"""
from __future__ import annotations

import datetime as dt
from datetime import timedelta

import streamlit as st

from src import data as D
from src import metrics as M
from src import theme
from src import ui as UI
from src import util as U
from src.pages import (goals, habits, journal, now, routine,
                       settings, stats, tasks, trading)

# nav glyphs as \uXXXX escapes -> pure-ASCII source, monochrome, copy-safe
NAV = [
    ("\\u25c9", "Now"),
    ("\\u25a6", "Routine"),
    ("\\u2713\\ufe0e", "Habits"),
    ("\\u25d4", "Trading"),
    ("\\u25c6", "Goals"),
    ("\\u2610", "Tasks"),
    ("\\u270e\\ufe0e", "Journal"),
    ("\\u25eb", "Stats"),
    ("\\u2699\\ufe0e", "Settings"),
]
# decode the escapes at import time into real single glyphs
NAV = [(g.encode().decode("unicode_escape"), n) for g, n in NAV]
OPTIONS = [g + "  " + n for g, n in NAV]
PAGES = {
    "Now": now, "Routine": routine, "Habits": habits,
    "Trading": trading, "Goals": goals, "Tasks": tasks,
    "Journal": journal, "Stats": stats, "Settings": settings,
}

st.set_page_config(page_title="PULSE - Life Command Center",
                   page_icon="\\u25c9", layout="wide",
                   initial_sidebar_state="expanded")

D.ensure()

st.markdown("<style>" + theme.CSS + "</style>", unsafe_allow_html=True)
accent = st.session_state.get("accent", "#4C8DFF")
st.markdown("<style>:root{--accent:%s;--accent-soft:%s;}</style>"
            % (accent, U.hexa(accent, 0.16)), unsafe_allow_html=True)

with st.sidebar:
    st.markdown(UI.brand_html(), unsafe_allow_html=True)
    sel = st.radio("nav", OPTIONS, index=0,
                   label_visibility="collapsed", key="nav")
    st.markdown(UI.user_html(st.session_state.get("name", D.DEFAULT_NAME)),
                unsafe_allow_html=True)
page_name = sel.split()[-1]

today = dt.date.today()
offset = float(st.session_state.get("tz_offset", 0))
now_dt = dt.datetime.now() + timedelta(hours=offset)

routine = D.get("routine")
habits = D.get("habits")
log = D.get("habit_log")
goals = D.get("goals")
tasks = D.get("tasks")
journal = D.get("journal")
trades = D.get("trades")
start = st.session_state.get("start_balance", D.START_BALANCE)

today_blocks = M.today_blocks(routine, today.weekday())
active_idx, progress, current, next_block = M.active_block_info(
    today_blocks, now_dt,
)
trade = M.trade_summary(trades, start)

cons = M.overall_consistency(habits, log, 30)
if goals:
    gavg = sum(M.goal_pct(x) for x in goals) / len(goals)
else:
    gavg = 0.0
jcomp = M.journal_completion(journal, 30)
score = M.life_score(cons, jcomp, trade["wr"], gavg)
day_name = today.strftime("%A")
day_sub = today.strftime("%b %d, %Y")
if score >= 70:
    score_tone = "tw-win"
elif score < 40:
    score_tone = "tw-loss"
else:
    score_tone = "tw-accent"

ctx = dict(today=today, now_dt=now_dt, routine=routine,
           today_blocks=today_blocks, active_idx=active_idx,
           progress=progress, current=current, next_block=next_block,
           habits=habits, habit_log=log, goals=goals, tasks=tasks,
           journal=journal, trades=trades, trade=trade, start=start,
           accent=accent,
           name=st.session_state.get("name", D.DEFAULT_NAME))

g, d, s = st.columns([5, 3, 2], gap="medium")
with g:
    st.markdown(UI.greeting_html(ctx["name"]), unsafe_allow_html=True)
with d:
    st.markdown(
        '<div style="padding:.3rem 0"><div class="tw-lab">today</div>'
        + '<div style="font:700 18px/1.1 var(--disp);color:var(--ink)">'
        + day_name + '</div><div class="tw-sub">' + day_sub + '</div></div>',
        unsafe_allow_html=True,
    )
with s:
    st.markdown(
        '<div style="text-align:right;padding:.3rem 0">'
        + '<div class="tw-lab">life score</div>'
        + '<div class="tw-val ' + score_tone + '" style="font-size:30px">'
        + str(score) + '</div></div>',
        unsafe_allow_html=True,
    )

PAGES[page_name].render(ctx)
