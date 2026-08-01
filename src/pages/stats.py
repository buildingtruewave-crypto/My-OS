"""The weekly / monthly review - how the whole operation is managing,
across the pipeline, the money, the spirit, the bots and the body.
Privacy rule: no balances here. Net worth and the climb live only in the
vault. This page shows activity, expected money and process.
"""
from __future__ import annotations

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U

WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def render(ctx):
    habits, log = ctx["habits"], ctx["habit_log"]
    goals, journal = ctx["goals"], ctx["journal"]
    daily, sales = ctx["sales_daily"], ctx["sales"]
    clients, bots = ctx["clients"], ctx["bots"]
    weights, today = ctx["weights"], ctx["today"]
    t_iso, score = ctx["today_iso"], ctx["score"]
    tasks, income = ctx["tasks"], ctx["income"]
    vault = ctx["vault"]
    spiritual = ctx["spiritual"]

    cons = M.overall_consistency(habits, log, 30)
    jcomp = M.journal_completion(journal, 30)
    jstreak = M.journal_streak(journal)
    gavg = (sum(M.goal_pct(g) for g in goals) / len(goals)) \
        if goals else 0.0
    com = M.commission_stats(sales, t_iso)
    cc = M.client_counts(clients, today)
    tc = M.task_counts(tasks, today)
    wk = M.week_sales(daily, today, 7)
    sold_week = sum(v for _l, v in wk)
    wdelta = M.weight_delta(weights)
    days_in = max(0, (today - D.START_DATE).days + 1) \
        if ctx["started"] else 0
    locked = [(s, i) for s, i in com["overdue"]
              if not M.comm_editable(s, i, today)]
    wk_in, wk_out = M.flow_week_inout(vault.get("flow", []), today)
    sp_health = M.spiritual_health(spiritual, 30)
    sp_streak = M.spiritual_streak(spiritual)

    row = [
        UI.tile("Life Score",
                str(score) if score is not None else "--",
                "composite 0-100", "mute",
                "win" if (score or 0) >= 70 else "ink",
                "star", "jewel", 0),
        UI.tile("Recording Day", str(days_in), "since Aug 1, 2026",
                "mute", "ink", "cal", "accent", 40),
        UI.tile("Sold This Week", str(sold_week), "phones",
                "win" if sold_week else "mute",
                "win" if sold_week else "ink", "phone", "win", 80),
        UI.tile("New Clients 7d", str(cc["new7"]), "inquiries",
                "mute", "ink", "users", "accent", 120),
        UI.tile("Weight Change", format(wdelta, "+,.1f") + " kg",
                "since first weigh-in",
                "win" if wdelta >= 0 else "loss", "ink",
                "scale", "jewel", 160),
    ]
    st.markdown(UI.tiles_grid(row, 5), unsafe_allow_html=True)

    w_streak = 0
    for h in habits:
        if h["name"].startswith("Workout"):
            w_streak = M.habit_streak(log, h["id"])
    st.markdown(UI.streaks_html([
        (jstreak, "journal days", "accent"),
        (M.sales_streak(daily, today), "sales tallies", "win"),
        (w_streak, "workout", "jewel"),
        (sp_streak, "spirit", "jewel"),
        (M.best_habit_streak(log, habits), "best habit", "win"),
    ]), unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    sp_series = M.spiritual_series(spiritual, 30)
    if len(sp_series) >= 2:
        st.markdown(UI.panel(
            "Spiritual Pulse",
            UI.equity_svg(sp_series, "st_sp", kind="pct",
                          xfmt=lambda d: d.strftime("%d")),
            right="30d energy · health " + U.fmt_pct(sp_health, False)),
            unsafe_allow_html=True)

    if any(log.values()):
        cseries = M.consistency_series(log, habits, 30)
        st.markdown(UI.panel(
            "Consistency Trend",
            UI.equity_svg(cseries, "st_eq", kind="pct",
                          xfmt=lambda d: d.strftime("%d")),
            right="last 30 days"), unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        cwd = M.consistency_by_weekday(habits, log, 60)
        items = []
        for i, nm in enumerate(WEEK):
            v = cwd[i]
            color = ("#34D399" if v >= 60 else
                     ("#F0556B" if v < 35 else "#F5B544"))
            items.append((nm, v - 50, color))
        st.markdown(UI.panel("Consistency by Weekday",
                             UI.hbars(items)), unsafe_allow_html=True)
    with c2:
        st.markdown(UI.panel("Phones Sold - last 7 days",
                             UI.bars(wk), right="per day"),
                    unsafe_allow_html=True)

    c3, c4 = st.columns(2, gap="medium")
    with c3:
        sc = M.stage_counts(clients)
        rows = []
        for sid in D.all_stage_ids():
            n = sc.get(sid, 0)
            if n:
                rows.append([
                    (UI.badge(D.stage_label(sid, sid),
                              D.stage_color(sid)), ""),
                    (str(n), "num"),
                ])
        st.markdown(UI.panel("Pipeline Distribution",
                             UI.table(["Stage", "Clients"], rows)),
                    unsafe_allow_html=True)
    with c4:
        ibt = M.income_by_type(income)
        items = [(k, v, "#34D399") for k, v in
                 sorted(ibt.items(), key=lambda x: x[1],
                        reverse=True)]
        st.markdown(UI.panel("Income by Source", UI.hbars(items),
                             right=U.fmt_kes(M.income_total(income))),
                    unsafe_allow_html=True)

    c5, c6 = st.columns(2, gap="medium")
    with c5:
        rows = []
        for b in bots["bots"]:
            s = M.bot_stats(bots["logs"], b["id"])
            chip = {"testing": ("TESTING", "#F5B544"),
                    "demo": ("DEMO", "#7C8AA5"),
                    "live": ("LIVE", "#34D399")}.get(
                        b["status"], ("?", "#7C8AA5"))
            tone = "tw-win" if s["pnl"] >= 0 else "tw-loss"
            rows.append([
                (b["name"], ""),
                (UI.badge(chip[0], chip[1]), ""),
                (str(s["n"]), "num"),
                (format(s["wr"], ".0f") + "%", "num"),
                ('<span class="' + tone + '">'
                 + format(s["pnl"], "+,.2f") + "</span>", "num"),
                (format(s["rr"], ".2f") + ":1", "num"),
            ])
        st.markdown(UI.panel("Ventures - Risk vs Reward",
                             UI.table(["Venture", "Status", "Logs",
                                       "WR", "Net", "RR"], rows)),
                    unsafe_allow_html=True)
    with c6:
        body = UI.kv([
            ("Clients paid & closed", str(cc["sold"])),
            ("Returned", str(cc["returned"])),
            ("Lost / declined", str(cc["lost"])),
            ("Cash-offer queue", str(cc["cashq"])),
            ("Commissions collected", U.fmt_kes(com["paid"])),
            ("Commissions pending", U.fmt_kes(com["pending"])),
            ("Locked unpaid (slipping)",
             str(len(locked)) + " - "
             + U.fmt_kes(sum(float(i.get("amount", 0))
                             for _s, i in locked))),
            ("Spirit health 30d", U.fmt_pct(sp_health, False)),
            ("Money in - 7d", U.fmt_kes(wk_in)),
            ("Money out - 7d", U.fmt_kes(wk_out)),
            ("Tasks cleared all-time", str(tc["done_all"])),
        ])
        st.markdown(UI.panel("TrueWave + Spirit + Activity", body),
                    unsafe_allow_html=True)

    c7, c8 = st.columns(2, gap="medium")
    with c7:
        done_n = miss_n = 0
        for h in habits:
            s = log.get(h["id"], {})
            for d, v in s.items():
                if v:
                    done_n += 1
                else:
                    miss_n += 1
        if done_n + miss_n:
            tot = done_n + miss_n
            st.markdown(UI.panel(
                "Habit Outcomes - all time",
                UI.donut([("Done", done_n, "#34D399"),
                          ("Missed", miss_n, "#F0556B")],
                         str(tot), "checks", tot)),
                unsafe_allow_html=True)
        else:
            st.markdown(UI.panel("Habit Outcomes", UI.empty_state(
                "Checks start Aug 1.")), unsafe_allow_html=True)
    with c8:
        st.markdown(UI.panel("How the Score Works", UI.kv([
            ("Life score formula", "40 / 20 / 20 / 20"),
            ("Consistency weight", "40%"),
            ("Journal weight", "20%"),
            ("Sales logging weight", "20%"),
            ("Goal weight", "20%"),
            ("Edit the blend", "metrics.life_score()"),
        ])), unsafe_allow_html=True)
