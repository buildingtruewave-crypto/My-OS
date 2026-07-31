"""Interactive widgets that write straight back to the data layer."""
from __future__ import annotations

import streamlit as st

from . import data as D


def habit_checklist(prefix, habits, log, today_str):
    if not habits:
        st.caption("No habits yet - add them on the Habits page.")
        return
    changed = False
    for h in habits:
        hid = h["id"]
        stored = bool(log.get(hid, {}).get(today_str, False))
        label = h["icon"] + "  " + h["name"]
        c = st.checkbox(label, value=stored, key=prefix + "h" + hid)
        if c != stored:
            log.setdefault(hid, {})[today_str] = c
            changed = True
    if changed:
        D.save_habit_log(log)


def task_checklist(prefix, tasks, today_iso):
    if not tasks:
        st.caption("No tasks here - add one below.")
        return
    changed = False
    pri = {"High": "H", "Normal": "N", "Low": "L"}
    for t in tasks:
        icon = pri.get(t.get("priority", "Normal"), "*")
        label = "[" + icon + "]   " + t["text"]
        c = st.checkbox(label, value=bool(t.get("done")),
                        key=prefix + "t" + t["id"])
        if c != bool(t.get("done")):
            t["done"] = c
            t["done_date"] = today_iso if c else ""
            changed = True
    if changed:
        D.save_tasks(tasks)
