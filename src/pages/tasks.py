from __future__ import annotations

import datetime as dt

import streamlit as st

from .. import data as D, ui as UI, widgets as W


def render(ctx):
    tasks = ctx["tasks"]
    done, total = _counts(tasks)
    pct = done / total * 100 if total else 0
    tone = "tw-win" if pct >= 70 else ("tw-loss" if pct < 30 else "tw-ink")
    st.markdown(UI.panel("Today's List",
                         f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
                         f'<span class="tw-val {tone}" style="font-size:24px">{done}/{total}</span>'
                         f'<span class="tw-lab">{pct:.0f}% cleared</span></div>'),
                unsafe_allow_html=True)

    filt = st.radio("show", ["Open", "Done", "All"], horizontal=True, key="tk_filt")
    shown = [t for t in tasks if (filt == "All") or (filt == "Open" and not t["done"])
             or (filt == "Done" and t["done"])]
    W.task_checklist("tk", shown)
    if shown != tasks:
        # re-sync done flags back into master list (objects are shared refs)
        D.save_tasks(tasks)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    with st.expander("＋  Add a task"):
        a, b = st.columns(2)
        with a:
            text = st.text_input("Task", key="tk_text")
            area = st.selectbox("Area", list(D.TAG_COLORS.keys()), key="tk_area")
        with b:
            pri = st.selectbox("Priority", ["High", "Normal", "Low"], key="tk_pri")
            due = st.date_input("Due", value=dt.date.today(), key="tk_due")
        if st.button("Add task", type="primary", key="tk_add") and text.strip():
            D.add_task({"text": text, "area": area, "priority": pri,
                        "due": due.isoformat(), "done": False}); st.rerun()


def _counts(tasks):
    return sum(1 for t in tasks if t.get("done")), len(tasks)
