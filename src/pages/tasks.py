from __future__ import annotations

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import widgets as W


def render(ctx):
    tasks, today = ctx["tasks"], ctx["today"]
    tc = M.task_counts(tasks, today)
    pct = (tc["done_today"] / tc["total"] * 100) if tc["total"] else 0

    row = [
        UI.tile("Open", str(tc["open"]), "remaining",
                "mute", "ink", "list", "accent", 0),
        UI.tile("Done Today", str(tc["done_today"]), "cleared",
                "win" if tc["done_today"] else "mute",
                "win" if tc["done_today"] else "ink",
                "check", "win", 40),
        UI.tile("Overdue", str(tc["overdue"]), "past due",
                "loss" if tc["overdue"] else "mute",
                "loss" if tc["overdue"] else "ink", "bolt", "loss",
                80),
        UI.tile("Total", str(tc["total"]), "tasks",
                "mute", "ink", "hash", "accent", 120),
    ]
    st.markdown(UI.tiles_grid(row, 4), unsafe_allow_html=True)

    head = (
        '<div style="display:flex;justify-content:space-between;'
        'align-items:baseline">'
        '<span class="tw-val '
        + ("tw-win" if pct >= 70 else "tw-ink")
        + '" style="font-size:24px">' + str(tc["done_today"]) + "/"
        + str(tc["total"]) + '</span>'
        '<span class="tw-lab">' + format(pct, ".0f")
        + '% of the list cleared today</span></div>'
    )
    st.markdown(UI.panel("Today's List", head),
                unsafe_allow_html=True)
    filt = st.radio("show", ["Open", "Done", "All"], horizontal=True,
                    key="tk_filt")
    if filt == "Open":
        shown = [t for t in tasks if not t.get("done")]
    elif filt == "Done":
        shown = [t for t in tasks if t.get("done")]
    else:
        shown = list(tasks)
    shown.sort(key=lambda t: (bool(t.get("done")),
                              t.get("due") or "9999"))
    W.task_checklist("tk", shown, ctx["today_iso"])

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
            due = st.date_input("Due", value=today, key="tk_due")
        if st.button("Add task", type="primary",
                     key="tk_add") and text.strip():
            D.add_task({
                "text": text.strip(), "area": area, "priority": pri,
                "due": due.isoformat(),
            })
            st.rerun()
