from __future__ import annotations

import streamlit as st

from .. import metrics as M, ui as UI, util as U


def render(ctx):
    ts = ctx["trade"]; trades = ctx["trades"]; start = ctx["start"]
    if trades.empty:
        st.markdown(UI.empty_state("No trades logged."), unsafe_allow_html=True)
        return

    row = [
        UI.tile("Net PnL", U.fmt_money(ts["net"], True), U.fmt_pct(ts["wr"], False),
                "win" if ts["net"] >= 0 else "loss", "win" if ts["net"] >= 0 else "loss", "↗", "accent", 0),
        UI.tile("Win Rate", U.fmt_pct(ts["wr"], False), f'{ts["w"]}W / {ts["l"]}L", "mute", "ink", "◎", "jewel", 40),
        UI.tile("Trades", str(ts["n"]), "", "mute", "ink", "≣", "accent", 80),
        UI.tile("Win Streak", str(ts["win_streak"]), "", "win", "win", "🔥", "win", 120),
        UI.tile("Loss Streak", str(ts["loss_streak"]), "", "loss", "loss", "⚠", "loss", 160),
    ]
    st.markdown(UI.tiles_grid(row, 5), unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        st.markdown(UI.panel("Equity Curve", UI.equity_svg(ts["eq_pts"], "tr_eq"),
                             right="all time"), unsafe_allow_html=True)
    with c2:
        g = trades.copy(); g["ym"] = g["dt"].dt.to_period("M")
        monthly = [(str(p), float(v)) for p, v in g.groupby("ym")["pnl"].sum().sort_index().items()]
        st.markdown(UI.panel("Monthly PnL", UI.monthly_bars(monthly[-12:])), unsafe_allow_html=True)

    c3, c4 = st.columns([3, 2], gap="medium")
    with c3:
        rows = []
        for _, t in ts["recent"].iterrows():
            tone = "tw-win" if t["pnl"] >= 0 else "tw-loss"
            rows.append([(t["dt"].strftime("%b %d %H:%M"), "num"), (t["asset"], ""),
                         (f'<span class="tw-dir {t["direction"]}">{t["direction"]}</span>', ""),
                         (f'{t["entry"]:,.4g}', "num"), (f'{t["exit"]:,.4g}', "num"),
                         (f'{t["lots"]:.2f}', "num"), (U.fmt_money(t["pnl"], True), f"num {tone}"),
                         (t["strategy"], "")])
        st.markdown(UI.panel("Recent Trades",
                             UI.table(["Time", "Asset", "Dir", "Entry", "Exit", "Lots", "PnL", "Strategy"], rows)),
                    unsafe_allow_html=True)
    with c4:
        y, m = ctx["today"].year, ctx["today"].month
        month_pnl = {d: v for d, v in ts["day_pnl"].items() if d.year == y and d.month == m}
        st.markdown(UI.panel(f"Signed Days · {ctx['today'].strftime('%b %Y')}",
                             UI.calendar_html(y, m, month_pnl, today=ctx["today"])),
                    unsafe_allow_html=True)
