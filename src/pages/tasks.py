from __future__ import annotations

import datetime as dt

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import widgets as W


def render(ctx):
    tasks = ctx["tasks"]
    done, total = M.task_counts(tasks)
    overdue = M.overdue_tasks(tasks)
    open_n = total - done
    pct = (done / total * 100) if total else 0

    row = [
        UI.tile("Open", str(open_n), "remaining", "mute", "ink",
                "list", "accent", 0),
        UI.tile("Done", str(done), "cleared", "win", "win",
                "check", "win", 40),
        UI.tile("Overdue", str(overdue), "past due",
                "loss" if overdue else "mute",
                "loss" if overdue else "ink", "bolt", "loss", 80),
        UI.tile("Total", str(total), "tasks", "mute", "ink",
                "hash", "accent", 120),
    ]
    st.markdown(UI.tiles_grid(row, 4), unsafe_allow_html=True)

    head = (
        '<div style="display:flex;justify-content:space-between;'
        + 'align-items:baseline">'
        + '<span class="tw-val ' + ("tw-win" if pct >= 70 else "tw-ink")
        + '" style="font-size:24px">' + str(done) + '/' + str(total)
        + '</span><span class="tw-lab">' + format(pct, ".0f")
        + '% cleared</span></div>'
    )
    st.markdown(UI.panel("Today's List", head), unsafe_allow_html=True)

    filt = st.radio("show", ["Open", "Done", "All"], horizontal=True,
                    key="tk_filt")
    if filt == "Open":
        shown = [t for t in tasks if not t["done"]]
    elif filt == "Done":
        shown = [t for t in tasks if t["done"]]
    else:
        shown = list(tasks)
    W.task_checklist("tk", shown)
    D.save_tasks(tasks)

    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    with st.expander("+  Add a task"):
        a, b = st.columns(2)
        with a:
            text = st.text_input("Task", key="tk_text")
            area = st.selectbox("Area", list(D.TAG_COLORS.keys()),
                                key="tk_area")
        with b:
            pri = st.selectbox("Priority", ["High", "Normal", "Low"],
                               key="tk_pri")
            due = st.date_input("Due", value=dt.date.today(), key="tk_due")
        if st.button("Add task", type="primary",
                     key="tk_add") and text.strip():
            D.add_task({
                "text": text, "area": area, "priority": pri,
                "due": due.isoformat(), "done": False,
            })
            st.rerun()
