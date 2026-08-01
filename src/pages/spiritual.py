"""Spirit - the daily record of time with God. The operator logs minutes,
the word received, what they felt, acts of devotion, gratitude and a depth
rating; the app derives a Spiritual Energy score (never random) and a
30-day pulse. Nothing is auto-filled or auto-deducted - it is the operator's
honest account, rendered alive.
"""
from __future__ import annotations

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U


def _present(e):
    if not e:
        return False
    return (float(e.get("minutes", 0) or 0) > 0
            or bool((e.get("felt") or "").strip())
            or bool((e.get("word") or "").strip())
            or bool(e.get("acts"))
            or bool((e.get("gratitude") or "").strip()))


def render(ctx):
    spiritual = ctx["spiritual"]
    today = ctx["today"]
    t_iso = ctx["today_iso"]

    e = spiritual.get(t_iso, {}) or {}
    energy = M.spiritual_energy(e) if e else 0
    streak = M.spiritual_streak(spiritual)
    health = M.spiritual_health(spiritual, 30)
    series = M.spiritual_series(spiritual, 30)

    row = [
        UI.tile("Spirit Energy", str(energy), "today",
                "win" if energy >= 70 else ("mute" if energy == 0
                                            else "accent"),
                "win" if energy >= 70 else ("ink" if energy == 0
                                            else "accent"),
                "flame", "jewel", 0),
        UI.tile("Streak", str(streak), "days with God",
                "win" if streak else "mute",
                "win" if streak else "ink", "pulse", "win", 40),
        UI.tile("30-day Health", U.fmt_pct(health, False),
                "average energy", "win" if health >= 60 else "mute",
                "win" if health >= 60 else "ink", "star", "accent", 80),
        UI.tile("Minutes Today",
                str(int(float(e.get("minutes", 0) or 0))),
                "time set apart", "mute", "ink", "clock", "accent", 120),
    ]
    st.markdown(UI.tiles_grid(row, 4), unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        if len(series) >= 2:
            body = UI.equity_svg(series, "sp_eq", kind="pct",
                                 xfmt=lambda d: d.strftime("%d"))
            right = "last 30 days"
        else:
            body = UI.empty_state(
                "The spiritual pulse draws itself from your first "
                "entry with God.")
            right = "energy"
        st.markdown(UI.panel("Spiritual Pulse", body, right=right),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(UI.panel(
            "How Energy Is Earned",
            UI.kv([
                ("Presence", "25 - showed up today"),
                ("Time", "25 - up to 60 min"),
                ("Depth", "25 - how connected (1-5)"),
                ("Devotion", "15 - up to 3 acts"),
                ("Reflection", "10 - wrote what you feel"),
            ]), right="deterministic"),
            unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>",
                unsafe_allow_html=True)
    st.markdown(UI.panel("Today With God",
                         '<div style="height:2px"></div>'),
                unsafe_allow_html=True)
    a, b = st.columns(2)
    with a:
        minutes = st.number_input("Minutes (prayer + word + worship)",
                                  0.0, 1440.0,
                                  float(e.get("minutes", 0) or 0),
                                  step=5.0, key="sp_min")
        depth = st.selectbox("Depth - how present / connected",
                             D.SPIRIT_DEPTHS,
                             index=max(0, min(4, int(e.get("depth", 3)
                                                 or 3) - 1)),
                             format_func=lambda d: str(d) + " / 5",
                             key="sp_dep")
    with b:
        acts = st.multiselect("Acts of devotion", D.SPIRIT_ACTS,
                              default=e.get("acts", []), key="sp_act")
        word = st.text_input("The word - what God spoke / scripture",
                             value=e.get("word", ""), key="sp_word")
    felt = st.text_area("What do you feel?",
                        value=e.get("felt", ""), height=90,
                        key="sp_felt")
    gratitude = st.text_input("Gratitude to God",
                              value=e.get("gratitude", ""),
                              key="sp_grat")

    s1, s2, _ = st.columns([1, 1, 4])
    with s1:
        if st.button("Save", type="primary", key="sp_save"):
            entry = {
                "minutes": float(minutes),
                "depth": int(depth),
                "acts": list(acts),
                "word": word.strip(),
                "felt": felt.strip(),
                "gratitude": gratitude.strip(),
            }
            sp = dict(spiritual)
            if _present(entry):
                sp[t_iso] = entry
            else:
                sp.pop(t_iso, None)
            D.save_spiritual(sp)
            st.success("Saved.")
            st.rerun()
    with s2:
        if st.button("Clear", key="sp_clear"):
            sp = dict(spiritual)
            sp.pop(t_iso, None)
            D.save_spiritual(sp)
            st.rerun()

    st.markdown("<div style='height:8px'></div>",
                unsafe_allow_html=True)
    recent = sorted(spiritual.items(), reverse=True)[:12]
    if recent:
        st.markdown(UI.panel(
            "Recent days with God",
            "".join(UI.spiritual_card(d, en, M.spiritual_energy(en))
                    for d, en in recent)),
            unsafe_allow_html=True)
    else:
        st.markdown(UI.panel("Recent days with God", UI.empty_state(
            "Begin tomorrow - set apart the first minutes.")),
            unsafe_allow_html=True)
