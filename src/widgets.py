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
