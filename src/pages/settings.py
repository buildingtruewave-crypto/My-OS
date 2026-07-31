from __future__ import annotations

import streamlit as st

from .. import data as D
from .. import ui as UI


def render(ctx):
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown(UI.panel("Profile & Look",
                             '<div style="height:2px"></div>'),
                    unsafe_allow_html=True)
        name = st.text_input(
            "Display name",
            value=st.session_state.get("name", D.DEFAULT_NAME),
            key="s_name")
        if name != st.session_state.get("name"):
            D.set_pref("name", name)
        cur = st.session_state.get("accent", "#4C8DFF")
        cur_label = next((k for k, v in D.ACCENTS.items() if v == cur),
                         "Electric Blue")
        keys = list(D.ACCENTS.keys())
        acc = st.radio("accent", keys, index=keys.index(cur_label),
                       label_visibility="collapsed", key="s_acc")
        if D.ACCENTS[acc] != cur:
            D.set_pref("accent", D.ACCENTS[acc])
            st.rerun()
        off = st.number_input(
            "Clock offset (hrs from Nairobi)", -12.0, 14.0,
            value=float(st.session_state.get("tz_offset", 0)),
            step=0.5, key="s_off")
        if off != st.session_state.get("tz_offset"):
            D.set_pref("tz_offset", float(off))
        st.caption("Clock is Africa/Nairobi (EAT). Adjust only if "
                   "the host drifts.")
        pin = st.text_input("Archive PIN", type="password",
                            value=str(st.session_state.get(
                                "pin", D.DEFAULT_PIN)), key="s_pin")
        if st.button("Save PIN", key="s_pinb"):
            D.set_pref("pin", pin.strip() or D.DEFAULT_PIN)
            st.success("PIN saved.")
            st.rerun()
        st.caption("The money manager hides inside the Archive nav "
                   "item. Default PIN is 2580 - change it.")
    with c2:
        st.markdown(UI.panel("Data Engine",
                             '<div style="height:2px"></div>'),
                    unsafe_allow_html=True)
        st.markdown(UI.kv([
            ("Recording starts", "Friday, 1 August 2026"),
            ("Timezone", "Africa/Nairobi (EAT, UTC+3)"),
            ("Persistence", "data/*.json - survives reboot"),
            ("Fake data", "none - everything is hand-entered"),
        ]), unsafe_allow_html=True)
        ea, eb = st.columns(2)
        with ea:
            st.download_button("Export all (.zip)", D.export_zip(),
                               file_name="pulse_life.zip",
                               mime="application/zip", key="s_zip")
        with eb:
            confirm = st.checkbox("I understand", key="s_conf")
            if st.button("Wipe all records", key="s_reset",
                         disabled=not confirm):
                D.reset_all()
                st.rerun()
        st.caption("Wipe keeps your routine, habit names and profile "
                   "but clears every record back to empty.")
    deploy = (
        '<div class="tw-stat"><span class="k">Now</span>'
        '<span class="v">streamlit run app.py</span></div>'
        '<div class="tw-stat"><span class="k">VPS</span>'
        '<span class="v">docker compose up -d</span></div>'
        '<div class="tw-stat"><span class="k">Phone</span>'
        '<span class="v">open the same URL - layout is responsive</span>'
        '</div>'
        '<div class="tw-stat"><span class="k">Design rule</span>'
        '<span class="v tw-accent">colour = outcome - routine = spine'
        '</span></div>'
    )
    st.markdown(UI.panel("Deployment", deploy), unsafe_allow_html=True)
