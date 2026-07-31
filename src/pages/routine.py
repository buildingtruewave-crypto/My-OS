from __future__ import annotations

import html

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI


def _esc(s):
    return html.escape(str(s))


NAMES = [
    "Mon",
    "Tue",
    "Wed",
    "Thu",
    "Fri",
    "Sat",
    "Sun",
]


def render(ctx):
    routine = ctx["routine"]
    today = ctx["today"]
    intro = (
        '<div class="tw-empty" '
        + 'style="padding:4px 0 12px;text-align:left">'
        + "Every other page hangs off this schedule. "
        + "Edit it below - or paste your real routine "
        + "and PULSE re-orients instantly.</div>"
    )
    st.markdown(UI.panel("This Week's Spine", intro),
                unsafe_allow_html=True)

    cols = st.columns(7, gap="small")
    for w in range(7):
        blocks = M.today_blocks(routine, w)
        body = []
        for b in blocks:
            bt = b["time"]
            bl = _esc(b["label"])
            body.append(
                '<div class="tw-stat">'
                + '<span class="k" '
                + 'style="font-family:var(--mono)">'
                + bt + '</span>'
                + '<span class="v" '
                + 'style="font-size:11px;'
                + 'font-family:var(--body);'
                + 'font-weight:600;'
                + 'color:var(--ink-2)">'
                + bl + '</span></div>'
            )
        bhtml = "".join(body)
        if not bhtml:
            bhtml = '<div class="tw-empty">rest</div>'
        with cols[w]:
            st.markdown(UI.panel(NAMES[w], bhtml),
                        unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>",
                unsafe_allow_html=True)
    st.markdown(
        UI.panel("Today's Timeline",
                 UI.timeline_html(ctx["today_blocks"],
                                  ctx["active_idx"])),
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:8px'></div>",
                unsafe_allow_html=True)
    st.markdown(
        '<div class="tw-lab" '
        + 'style="margin:4px 0 8px">'
        + 'PASTE / EDIT YOUR ROUTINE</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "One block per line:  HH:MM  Label  #Tag  @scope   "
        "tags: Trade Body Mind Life Rest Focus - "
        "scope: @weekdays @weekend @all or @mon,wed,fri"
    )
    txt = st.text_area(
        "routine", value=D.routine_to_text(routine),
        height=320, label_visibility="collapsed",
        key="rt_text",
    )
    a, b, _ = st.columns([1, 1, 4])
    with a:
        if st.button("Save routine", type="primary",
                     key="rt_save"):
            parsed = D.parse_routine_text(txt)
            if parsed:
                D.save_routine(parsed)
                st.success("Saved " + str(len(parsed))
                           + " blocks.")
                st.rerun()
            else:
                st.error(
                    "Could not parse any blocks - "
                    "check the format."
                )
    with b:
        if st.button("Reset to seed", key="rt_reset"):
            D.save_routine(D._seed_routine())
            st.rerun()
