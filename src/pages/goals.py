from __future__ import annotations

import streamlit as st

from .. import data as D, metrics as M, ui as UI


def render(ctx):
    goals = ctx["goals"]
    st.markdown(UI.panel("Quarterly Targets",
                         '<div class="tw-empty" style="padding:4px 0 12px;text-align:left">'
                         'The numbers you are steering this quarter.</div>'),
                unsafe_allow_html=True)

    if goals:
        cols = st.columns(min(len(goals), 3))
        for i, g in enumerate(goals):
            pct = M.goal_pct(g)
            color = "#34D399" if pct >= 80 else ("#F5B544" if pct >= 40 else "#F0556B")
            with cols[i % len(cols)]:
                st.markdown(UI.goal_html(g, pct, color), unsafe_allow_html=True)
    else:
        st.markdown(UI.empty_state("No goals yet."), unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    with st.expander("＋  Add / update a goal", expanded=not goals):
        mode = st.radio("mode", ["Add new", "Update progress"], horizontal=True, key="g_mode")
        if mode == "Add new":
            a, b = st.columns(2)
            with a:
                title = st.text_input("Title", key="g_t")
                metric = st.text_input("Metric label", "units", key="g_m")
                target = st.number_input("Target", 0.0, None, 10.0, step=1.0, key="g_tg")
            with b:
                current = st.number_input("Current", 0.0, None, 0.0, step=1.0, key="g_c")
                quarter = st.text_input("Quarter / deadline", "Q3", key="g_q")
            if st.button("Add goal", type="primary", key="g_add") and title.strip():
                D.add_goal({"title": title, "metric": metric, "target": target,
                            "current": current, "quarter": quarter}); st.rerun()
        else:
            if goals:
                sel = st.selectbox("Goal", [g["title"] for g in goals], key="g_sel")
                g = next(x for x in goals if x["title"] == sel)
                nv = st.number_input("New current value", 0.0, None, float(g["current"]),
                                     step=1.0, key="g_nv")
                if st.button("Update", type="primary", key="g_up"):
                    g["current"] = nv; D.save_goals(goals); st.rerun()
