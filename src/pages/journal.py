from __future__ import annotations

import streamlit as st

from .. import data as D
from .. import ui as UI


def render(ctx):
    journal = ctx["journal"]
    today = ctx["today"]
    intro = (
        '<div class="tw-empty" '
        + 'style="padding:4px 0 12px;text-align:left">'
        + "One entry a day. Gratitude, the win, "
        + "the lesson, the mood.</div>"
    )
    st.markdown(UI.panel("Daily Reflection", intro),
                unsafe_allow_html=True)

    day = st.date_input("Date", value=today, key="j_date")
    key = day.isoformat()
    cur = journal.get(key, {})
    a, b = st.columns(2)
    with a:
        grat = st.text_input(
            "Grateful for",
            value=cur.get("gratitude", ""), key="j_g",
        )
        win = st.text_input(
            "Today's win",
            value=cur.get("win", ""), key="j_w",
        )
    with b:
        lesson = st.text_input(
            "Lesson", value=cur.get("lesson", ""),
            key="j_l",
        )
        mood_idx = 2
        if cur.get("mood") in D.MOODS:
            mood_idx = D.MOODS.index(cur["mood"])
        mood = st.selectbox("Mood", D.MOODS,
                            index=mood_idx, key="j_m")
    s1, s2, _ = st.columns([1, 1, 4])
    with s1:
        if st.button("Save entry", type="primary",
                     key="j_save"):
            j = dict(journal)
            if any([grat, win, lesson]):
                j[key] = {
                    "gratitude": grat, "win": win,
                    "lesson": lesson, "mood": mood,
                }
            else:
                j.pop(key, None)
            D.save_journal(j)
            st.success("Saved.")
            st.rerun()
    with s2:
        if st.button("Clear", key="j_clear"):
            j = dict(journal)
            j.pop(key, None)
            D.save_journal(j)
            st.rerun()

    st.markdown("<div style='height:8px'></div>",
                unsafe_allow_html=True)
    recent = sorted(journal.items(), reverse=True)[:12]
    if recent:
        body = "".join(UI.journal_card(d, e)
                       for d, e in recent)
        st.markdown(UI.panel("Recent entries", body),
                    unsafe_allow_html=True)
    else:
        st.markdown(
            UI.empty_state("No entries yet."),
            unsafe_allow_html=True,
        )
