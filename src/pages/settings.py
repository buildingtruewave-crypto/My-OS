from __future__ import annotations

import streamlit as st

from .. import data as D, ui as UI, util as U


def render(ctx):
    st.markdown(UI.panel("Preferences",
                         '<div class="tw-empty" style="padding:4px 0 12px;text-align:left">'
                         'Make PULSE yours, manage the clock, and move your data.</div>'),
                unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<div class="tw-lab" style="margin:4px 0 10px">PROFILE</div>', unsafe_allow_html=True)
        name = st.text_input("Display name", value=st.session_state.get("name", D.DEFAULT_NAME), key="s_name")
        if name != st.session_state.get("name"):
            st.session_state["name"] = name; D._save_prefs()

        st.markdown('<div class="tw-lab" style="margin:18px 0 10px">ACCENT</div>', unsafe_allow_html=True)
        cur = st.session_state.get("accent", "#4C8DFF")
        cur_label = next((k for k, v in D.ACCENTS.items() if v == cur), "Electric Blue")
        acc = st.radio("accent", list(D.ACCENTS.keys()),
                       index=list(D.ACCENTS.keys()).index(cur_label),
                       label_visibility="collapsed", key="s_acc")
        if D.ACCENTS[acc] != cur:
            st.session_state["accent"] = D.ACCENTS[acc]; D._save_prefs(); st.rerun()

        st.markdown('<div class="tw-lab" style="margin:18px 0 10px">CLOCK OFFSET (HRS)</div>', unsafe_allow_html=True)
        off = st.number_input("offset", -12.0, 14.0, value=float(st.session_state.get("tz_offset", 0)),
                              step=0.5, key="s_off")
        if off != st.session_state.get("tz_offset"):
            st.session_state["tz_offset"] = float(off); D._save_prefs()
        st.caption("Adjust if the host clock isn't your local time.")

    with c2:
        st.markdown('<div class="tw-lab" style="margin:4px 0 10px">DATA ENGINE</div>', unsafe_allow_html=True)
        seed = st.number_input("Random seed", 1, 9_999_999_999,
                               value=int(st.session_state.get("seed", D.DEFAULT_SEED)), step=1, key="s_seed")
        if st.button("Regenerate everything", key="s_regen"):
            D.regenerate(seed); st.rerun()
        st.caption("Overwrites the data/ files on a VPS.")

        st.markdown('<div class="tw-lab" style="margin:18px 0 10px">MOVE YOUR LIFE</div>', unsafe_allow_html=True)
        ea, eb = st.columns(2)
        with ea:
            st.download_button("Export all (.zip)", D.export_zip(),
                               file_name="pulse_life.zip", mime="application/zip", key="s_zip")
        with eb:
            if st.button("Reset to fresh seed", key="s_reset"):
                D.regenerate(D.DEFAULT_SEED); st.rerun()

    st.markdown(UI.panel("Deployment",
                         '<div class="tw-stat"><span class="k">Now</span>'
                         '<span class="v">streamlit run app.py  ·  or Streamlit Cloud</span></div>'
                         '<div class="tw-stat"><span class="k">VPS</span>'
                         '<span class="v">docker compose up -d  ·  or systemd + nginx (see /deploy)</span></div>'
                         '<div class="tw-stat"><span class="k">Persistence</span>'
                         '<span class="v">data/*.json + data/trades.csv</span></div>'
                         '<div class="tw-stat"><span class="k">Design rule</span>'
                         '<span class="v tw-accent">colour = outcome · routine = spine</span></div>'),
                unsafe_allow_html=True)
