"""PULSE - Life Command Center (TrueWave edition). Entry point.
Run locally:  pip install -r requirements.txt && streamlit run app.py
Time: Africa/Nairobi (EAT). Recording starts 1 August 2026.
"""
from __future__ import annotations

import streamlit as st
from datetime import timedelta

from src import data as D
from src import metrics as M
from src import theme
from src import ui as UI
from src import util as U
from src.pages import (bots, clients, goals, habits, journal,
                       now, routine, sales, settings, stats, vault)

NAV = [
    ("\u25c9", "Now"),
    ("\u25a6", "Routine"),
    ("\u25c8", "TrueWave"),
    ("\u25a4", "Sales"),
    ("\u270e\ufe0e", "Journal"),
    ("\u2713\ufe0e", "Habits"),
    ("\u25d4", "Bots"),
    ("\u25c6", "Goals"),
    ("\u25eb", "Stats"),
    ("\u25a3", "Archive"),
    ("\u2699\ufe0e", "Settings"),
]
NAV = [(g.encode().decode("unicode_escape"), n) for g, n in NAV]
OPTIONS = [g + "   " + n for g, n in NAV]
PAGES = {
    "Now": now, "Routine": routine, "TrueWave": clients,
    "Sales": sales, "Journal": journal, "Habits": habits,
    "Bots": bots, "Goals": goals, "Stats": stats,
    "Archive": vault, "Settings": settings,
}

st.set_page_config(page_title="PULSE - Life Command Center",
                   page_icon="\u25c9", layout="wide",
                   initial_sidebar_state="expanded")
D.ensure()
st.markdown("<style>" + theme.CSS + "</style>",
            unsafe_allow_html=True)
accent = st.session_state.get("accent", "#4C8DFF")
st.markdown(
    "<style>:root{--accent:%s;--accent-soft:%s;}</style>"
    % (accent, U.hexa(accent, 0.16)), unsafe_allow_html=True)

with st.sidebar:
    st.markdown(UI.brand_html(), unsafe_allow_html=True)
    sel = st.radio("nav", OPTIONS, index=0,
                   label_visibility="collapsed", key="nav")
    st.markdown(UI.user_html(
        st.session_state.get("name", D.DEFAULT_NAME),
        "Operator - Nairobi"), unsafe_allow_html=True)

page_name = sel.split()[-1]

offset = float(st.session_state.get("tz_offset", 0))
now_dt = U.now_local() + timedelta(hours=offset)
today = now_dt.date()
today_iso = today.isoformat()
wd = today.weekday()
day_type = "Weekday" if wd < 5 else ("Saturday" if wd == 5 else "Sunday")

routine = D.get("routine")
habits = D.get("habits")
log = D.get("habit_log")
goals = D.get("goals")
issues = D.get("issues")
journal = D.get("journal")
weights = D.get("weights")
clients_l = D.get("clients")
sales_daily = D.get("sales_daily")
sales_l = D.get("sales")
bots_d = D.get("bots")
vault_d = D.get("vault")

today_blocks = M.today_blocks(routine, wd)
active_idx, progress, current, next_block = M.active_block_info(
    today_blocks, now_dt)

cons = M.overall_consistency(habits, log, 30)
jcomp = M.journal_completion(journal, 30)
srate = M.sales_rate(sales_daily, today, 30)
gavg = (sum(M.goal_pct(g) for g in goals) / len(goals)) if goals else 0.0
started = today >= D.START_DATE
score = M.life_score(cons, jcomp, srate, gavg) if started else None

ctx = dict(today=today, today_iso=today_iso, now_dt=now_dt,
           day_type=day_type, routine=routine,
           today_blocks=today_blocks, active_idx=active_idx,
           progress=progress, current=current,
           next_block=next_block, habits=habits, habit_log=log,
           goals=goals, issues=issues, journal=journal,
           weights=weights, clients=clients_l,
           sales_daily=sales_daily, sales=sales_l, bots=bots_d,
           vault=vault_d, started=started, score=score,
           accent=accent,
           name=st.session_state.get("name", D.DEFAULT_NAME))

g, d, s = st.columns([5, 3, 2], gap="medium")
with g:
    st.markdown(UI.greeting_html(ctx["name"]),
                unsafe_allow_html=True)
with d:
    st.markdown(
        '<div style="padding:.3rem 0"><div class="tw-lab">today</div>'
        '<div style="font:700 18px/1.1 var(--disp);color:var(--ink)">'
        + today.strftime("%A") + "</div>"
        + '<div class="tw-sub">' + today.strftime("%b %d, %Y")
        + " &middot; " + day_type + " &middot; Nairobi</div></div>",
        unsafe_allow_html=True)
with s:
    sv = str(score) if score is not None else "--"
    if score is None:
        tone = "tw-mute"
    elif score >= 70:
        tone = "tw-win"
    elif score < 40:
        tone = "tw-loss"
    else:
        tone = "tw-accent"
    st.markdown(
        '<div style="text-align:right;padding:.3rem 0">'
        '<div class="tw-lab">life score</div>'
        '<div class="tw-val ' + tone + '" style="font-size:30px">'
        + sv + "</div></div>", unsafe_allow_html=True)

PAGES[page_name].render(ctx)
