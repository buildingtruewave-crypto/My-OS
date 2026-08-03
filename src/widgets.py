"""Interactive widgets that write straight back to the data layer."""
from __future__ import annotations

import streamlit as st

from . import data as D


def habit_checklist(prefix, habits, log, today_str):
    """Render the habit list. Auto-detected habits (journal / sales /
    client touches / weigh-in) are shown read-only because they fill
    themselves from real data; only manual habits are tickable. When a
    manual habit is ticked, only manual habits are persisted, so the
    auto-filled ones never get written into storage."""
    if not habits:
        st.caption("No habits yet - add them on the Habits page.")
        return
    changed = False
    for h in habits:
        hid = h["id"]
        src = D.habit_source(h)
        value = bool(log.get(hid, {}).get(today_str, False))
        label = h["icon"] + "  " + h["name"]
        if src:
            st.checkbox(label, value=value, key=prefix + "h" + hid,
                        disabled=True,
                        help="Filled automatically from your real data")
        else:
            c = st.checkbox(label, value=value, key=prefix + "h" + hid)
            if c != value:
                log.setdefault(hid, {})[today_str] = c
                changed = True
    if changed:
        manual = {}
        for h in habits:
            if not D.habit_source(h):
                hid = h["id"]
                if hid in log:
                    manual[hid] = dict(log[hid])
        D.save_habit_log(manual)


def task_checklist(prefix, tasks, today_iso):
    if not tasks:
        st.caption("No tasks here - add one below.")
        return
    changed = False
    pri = {"High": "H", "Normal": "N", "Low": "L"}
    for t in tasks:
        icon = pri.get(t.get("priority", "Normal"), "*")
        label = "[" + icon + "]    " + t["text"]
        c = st.checkbox(label, value=bool(t.get("done")),
                        key=prefix + "t" + t["id"])
        if c != bool(t.get("done")):
            t["done"] = c
            t["done_date"] = today_iso if c else ""
            changed = True
    if changed:
        D.save_tasks(tasks)
