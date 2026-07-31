from __future__ import annotations

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U

AREAS = ["Work", "Home", "Money", "Health", "Other"]


def render(ctx):
    goals, issues, today = ctx["goals"], ctx["issues"], ctx["today"]
    t_iso = ctx["today_iso"]
    on, at, done = M.goal_buckets(goals)
    gavg = (sum(M.goal_pct(g) for g in goals) / len(goals)) \
        if goals else 0.0
    open_i, over_i = M.issues_open(issues, today)

    row = [
        UI.tile("Avg Progress", U.fmt_pct(gavg, False), "all goals",
                "win" if gavg >= 60 else "mute",
                "win" if gavg >= 60 else "ink", "target", "accent",
                0),
        UI.tile("On Track", str(on), ">= 60%", "win", "win",
                "check", "win", 40),
        UI.tile("At Risk", str(at), "< 60%", "loss", "loss",
                "bolt", "loss", 80),
        UI.tile("Fixes Overdue", str(len(over_i)), "need attention",
                "loss" if over_i else "mute",
                "loss" if over_i else "ink", "flag", "jewel", 120),
    ]
    st.markdown(UI.tiles_grid(row, 4), unsafe_allow_html=True)

    if goals:
        cols = st.columns(min(len(goals), 3))
        for i, g in enumerate(goals):
            pct = M.goal_pct(g)
            color = ("#34D399" if pct >= 80 else
                     ("#F5B544" if pct >= 40 else "#F0556B"))
            with cols[i % len(cols)]:
                st.markdown(UI.goal_html(g, pct, color),
                            unsafe_allow_html=True)
    else:
        st.markdown(UI.panel("Goals", UI.empty_state(
            "No goals yet - add your first target below.")),
            unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    st.markdown(UI.panel("Issues & Fixes - things that need a date",
                         '<div style="height:2px"></div>'),
                unsafe_allow_html=True)
    if open_i:
        for i in open_i:
            overdue = i.get("due") and i["due"] < t_iso
            c1, c2, c3 = st.columns([1, 5, 1.4])
            with c1:
                if st.checkbox("done", value=False,
                               key="is" + i["id"]):
                    i["done"] = True
                    D.save_issues(issues)
                    st.rerun()
            with c2:
                st.markdown('<div style="padding-top:8px;font:600 '
                            '13px/1.3 var(--body);color:var(--ink-2)">'
                            + str(i["text"]) + "</div>",
                            unsafe_allow_html=True)
            with c3:
                chip = ("OVERDUE", "#F0556B") if overdue else \
                    ("DUE", "#F5B544")
                st.markdown('<div style="padding-top:8px">'
                            + UI.badge(chip[0], chip[1])
                            + ' <span class="tw-sub">'
                            + str(i.get("due", "--"))
                            + "</span></div>", unsafe_allow_html=True)
    else:
        st.caption("Nothing broken right now.")
    a, b, c, d = st.columns([3, 1.4, 1.4, 1])
    with a:
        itxt = st.text_input("Issue", key="is_t",
                             placeholder="what needs fixing")
    with b:
        iarea = st.selectbox("area", AREAS, key="is_a")
    with c:
        idue = st.date_input("fix by", value=today, key="is_d")
    with d:
        st.markdown("<div style='height:26px'></div>",
                    unsafe_allow_html=True)
        if st.button("Add", type="primary",
                     key="is_add") and itxt.strip():
            D.add_issue(itxt.strip(), iarea, idue.isoformat())
            st.rerun()

    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    with st.expander("+  Add / update a goal", expanded=not goals):
        mode = st.radio("mode", ["Add new", "Update progress"],
                        horizontal=True, key="g_mode")
        if mode == "Add new":
            a, b = st.columns(2)
            with a:
                title = st.text_input("Title", key="g_t")
                metric = st.text_input("Metric label", "units",
                                       key="g_m")
                target = st.number_input("Target", 0.0, None, 10.0,
                                         step=1.0, key="g_tg")
            with b:
                current = st.number_input("Current", 0.0, None, 0.0,
                                          step=1.0, key="g_c")
                quarter = st.text_input("Quarter / deadline",
                                        "by Jan 2027", key="g_q")
            if st.button("Add goal", type="primary",
                         key="g_add") and title.strip():
                D.add_goal({"title": title, "metric": metric,
                            "target": target, "current": current,
                            "quarter": quarter})
                st.rerun()
        else:
            if goals:
                titles = [g["title"] for g in goals]
                sel = st.selectbox("Goal", titles, key="g_sel")
                g = next(x for x in goals if x["title"] == sel)
                nv = st.number_input("New current value", 0.0, None,
                                     float(g["current"]), step=1.0,
                                     key="g_nv")
                if st.button("Update", type="primary", key="g_up"):
                    g["current"] = nv
                    D.save_goals(goals)
                    st.rerun()
