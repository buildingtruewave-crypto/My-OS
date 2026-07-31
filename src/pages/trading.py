from __future__ import annotations

import streamlit as st

from .. import ui as UI, util as U


def render(ctx):
    ts = ctx["trade"]
    trades = ctx["trades"]
    if trades.empty:
        st.markdown(UI.empty_state("No trades logged."), unsafe_allow_html=True)
        return

    w = ts["w"]
    l = ts["l"]
    n = ts["n"]
    net = ts["net"]
    wr = ts["wr"]
    ws = ts["win_streak"]
    ls = ts["loss_streak"]
    net_tone = "win" if net >= 0 else "loss"
    wl_txt = str(w) + "W / " + str(l) + "L"

    row = [
        UI.tile("Net PnL", U.fmt_money(net, True), U.fmt_pct(wr, False),
                net_tone, net_tone, "~", "accent", 0),
        UI.tile("Win Rate", U.fmt_pct(wr, False), wl_txt, "mute", "ink", "@", "jewel", 40),
        UI.tile("Trades", str(n), "", "mute", "ink", "#", "accent", 80),
        UI.tile("Win Streak", str(ws), "", "win", "win", "+", "win", 120),
        UI.tile("Loss Streak", str(ls), "", "loss", "loss", "!", "loss", 160),
    ]
    st.markdown(UI.tiles_grid(row, 5), unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        st.markdown(UI.panel("Equity Curve", UI.equity_svg(ts["eq_pts"], "tr_eq"),
                             right="all time"), unsafe_allow_html=True)
    with c2:
        g = trades.copy()
        g["ym"] = g["dt"].dt.to_period("M")
        monthly = [(str(p), float(v))
                   for p, v in g.groupby("ym")["pnl"].sum().sort_index().items()]
        st.markdown(UI.panel("Monthly PnL", UI.monthly_bars(monthly[-12:])),
                    unsafe_allow_html=True)

    c3, c4 = st.columns([3, 2], gap="medium")
    with c3:
        rows = []
        for _, t in ts["recent"].iterrows():
            tone = "tw-win" if t["pnl"] >= 0 else "tw-loss"
            dtstr = t["dt"].strftime("%b %d %H:%M")
            dr = t["direction"]
            en = format(t["entry"], ",.4g")
            ex = format(t["exit"], ",.4g")
            lo = format(t["lots"], ".2f")
            pnl = U.fmt_money(t["pnl"], True)
            strat = t["strategy"]
            dirspan = '<span class="tw-dir ' + dr + '">' + dr + '</span>'
            rows.append([(dtstr, "num"), (t["asset"], ""), (dirspan, ""),
                         (en, "num"), (ex, "num"), (lo, "num"),
                         (pnl, "num " + tone), (strat, "")])
        st.markdown(UI.panel("Recent Trades",
                             UI.table(["Time", "Asset", "Dir", "Entry", "Exit",
                                       "Lots", "PnL", "Strategy"], rows)),
                    unsafe_allow_html=True)
    with c4:
        y = ctx["today"].year
        m = ctx["today"].month
        month_pnl = {d: v for d, v in ts["day_pnl"].items() if d.year == y and d.month == m}
        title = "Signed Days - " + ctx["today"].strftime("%b %Y")
        st.markdown(UI.panel(title,
                             UI.calendar_html(y, m, month_pnl, today=ctx["today"])),
                    unsafe_allow_html=True)
