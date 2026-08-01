"""Routine - today's timeline sits directly under the KPI strip (above the
7-day grid), exactly as the operator reads their day top-to-bottom."""
from __future__ import annotations

import html

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI

NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def render(ctx):
    routine, today = ctx["routine"], ctx["today"]

    counts = [len(M.today_blocks(routine, w)) for w in range(7)]
    avg_b = sum(counts) / 7.0 if counts else 0.0
    tb = M.today_blocks(routine, today.weekday())
    work_b = sum(1 for b in tb
                 if b.get("tag") in ("Sales", "Content"))
    earliest = tb[0]["time"] if tb else "--:--"
    latest = tb[-1]["time"] if tb else "--:--"
    row = [
        UI.tile("Avg Blocks / Day", format(avg_b, ".1f"), "7-day mean",
                "mute", "ink", "list", "accent", 0),
        UI.tile("Work Blocks", str(work_b), "content + sales today",
                "mute", "ink", "trend", "accent", 40),
        UI.tile("First Block", earliest, "start",
                "mute", "ink", "clock", "win", 80),
        UI.tile("Last Block", latest, "lights out",
                "mute", "ink", "clock", "jewel", 120),
    ]
    st.markdown(UI.tiles_grid(row, 4), unsafe_allow_html=True)

    st.markdown(UI.panel(
        "Today's Timeline - " + ctx["day_type"],
        UI.timeline_html(ctx["today_blocks"], ctx["active_idx"])),
        unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>",
                unsafe_allow_html=True)
    cols = st.columns(7, gap="small")
    for w in range(7):
        body = []
        for b in M.today_blocks(routine, w):
            body.append(
                '<div class="tw-stat">'
                '<span class="k" style="font-family:var(--mono)">'
                + b["time"] + '</span>'
                '<span class="v" style="font-size:11px;'
                'font-family:var(--body);font-weight:600;'
                'color:var(--ink-2)">' + html.escape(b["label"])
                + '</span></div>')
        with cols[w]:
            st.markdown(UI.panel(
                NAMES[w],
                "".join(body) or '<div class="tw-empty">rest</div>'),
                unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>",
                unsafe_allow_html=True)
    st.markdown('<div class="tw-lab" style="margin:4px 0 8px">'
                'PASTE / EDIT YOUR ROUTINE</div>',
                unsafe_allow_html=True)
    st.caption(
        "One block per line:  HH:MM  Label  #Tag  @scope   -   "
        "tags: Content Sales Body Mind Life Rest Focus   -   "
        "scope: @weekdays @sat @sun @weekend @all or @mon,wed,fri")
    txt = st.text_area("routine", value=D.routine_to_text(routine),
                       height=320, label_visibility="collapsed",
                       key="rt_text")
    a, b, _ = st.columns([1, 1, 4])
    with a:
        if st.button("Save routine", type="primary", key="rt_save"):
            parsed = D.parse_routine_text(txt)
            if parsed:
                D.save_routine(parsed)
                st.success("Saved " + str(len(parsed)) + " blocks.")
                st.rerun()
            else:
                st.error("Could not parse any blocks - check format.")
    with b:
        if st.button("Reset to my plan", key="rt_reset"):
            D.save_routine(D._seed_routine())
            st.rerun()
