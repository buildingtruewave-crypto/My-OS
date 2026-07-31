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
            key="s_name",
        )
        if name != st.session_state.get("name"):
            st.session_state["name"] = name
            D._save_prefs()

        cur = st.session_state.get("accent", "#4C8DFF")
        cur_label = "Electric Blue"
        for k, v in D.ACCENTS.items():
            if v == cur:
                cur_label = k
        keys = list(D.ACCENTS.keys())
        acc = st.radio("accent", keys, index=keys.index(cur_label),
                       label_visibility="collapsed", key="s_acc")
        if D.ACCENTS[acc] != cur:
            st.session_state["accent"] = D.ACCENTS[acc]
            D._save_prefs()
            st.rerun()

        off = st.number_input(
            "Clock offset (hrs)", -12.0, 14.0,
            value=float(st.session_state.get("tz_offset", 0)),
            step=0.5, key="s_off",
        )
        if off != st.session_state.get("tz_offset"):
            st.session_state["tz_offset"] = float(off)
            D._save_prefs()
        st.caption("Adjust if the host clock is not your local time.")

    with c2:
        st.markdown(UI.panel("Data Engine",
                             '<div style="height:2px"></div>'),
                    unsafe_allow_html=True)
        seed = st.number_input(
            "Random seed", 1, 9999999999,
            value=int(st.session_state.get("seed", D.DEFAULT_SEED)),
            step=1, key="s_seed",
        )
        if st.button("Regenerate everything", key="s_regen"):
            D.regenerate(seed)
            st.rerun()
        st.caption("Overwrites the data/ files on a VPS.")

        ea, eb = st.columns(2)
        with ea:
            st.download_button("Export all (.zip)", D.export_zip(),
                               file_name="pulse_life.zip",
                               mime="application/zip", key="s_zip")
        with eb:
            if st.button("Reset to fresh seed", key="s_reset"):
                D.regenerate(D.DEFAULT_SEED)
                st.rerun()

    deploy = (
        '<div class="tw-stat"><span class="k">Now</span>'
        + '<span class="v">streamlit run app.py - or Streamlit Cloud</span></div>'
        + '<div class="tw-stat"><span class="k">VPS</span>'
        + '<span class="v">docker compose up -d - or systemd + nginx</span></div>'
        + '<div class="tw-stat"><span class="k">Persistence</span>'
        + '<span class="v">data/*.json + data/trades.csv</span></div>'
        + '<div class="tw-stat"><span class="k">Design rule</span>'
        + '<span class="v tw-accent">colour = outcome - routine = spine</span></div>'
    )
    st.markdown(UI.panel("Deployment", deploy), unsafe_allow_html=True)
