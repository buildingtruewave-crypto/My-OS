"""The dashboard - the heart that pumps every module into one view."""
from __future__ import annotations

import datetime as dt
import html

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U
from .. import widgets as W


def _today_done(habits, log, today):
    return sum(1 for h in habits
               if log.get(h["id"], {}).get(today.isoformat()))


def render(ctx):
    today, t_iso = ctx["today"], ctx["today_iso"]
    now_dt, blocks = ctx["now_dt"], ctx["today_blocks"]
    idx, prog = ctx["active_idx"], ctx["progress"]
    cur, nxt = ctx["current"], ctx["next_block"]
    habits, log = ctx["habits"], ctx["habit_log"]
    goals, issues = ctx["goals"], ctx["issues"]
    journal, weights = ctx["journal"], ctx["weights"]
    clients, daily, sales = ctx["clients"], ctx["sales_daily"], \
        ctx["sales"]
    bots, vault = ctx["bots"], ctx["vault"]
    tasks, income = ctx["tasks"], ctx["income"]
    score, started = ctx["score"], ctx["started"]

    cons = M.overall_consistency(habits, log, 30)
    jstreak = M.journal_streak(journal)
    cc = M.client_counts(clients, today)
    com = M.commission_stats(sales, t_iso)
    tc = M.task_counts(tasks, today)
    window = M.clients_in_window(clients, today)
    sheet = M.call_sheet(clients, today)
    done_today, total_h = _today_done(habits, log, today), len(habits)
    d_entry = daily.get(t_iso) or {}
    sold_today = int(d_entry.get("sold", 0))
    rej_today = int(d_entry.get("system_rej", 0)) \
        + int(d_entry.get("cash_rej", 0))
    inc_week = M.income_total(
        income, (today - dt.timedelta(days=6)).isoformat(), t_iso)
    net = M.net_worth(vault)
    cash = M.cash_on_hand(vault)
    bills_late = M.bills_overdue(vault, today)

    # ---- row 1: five KPI tiles ----
    row1 = [
        UI.tile("Life Score",
                str(score) if score is not None else "--",
                "composite 0-100" if started else "starts Aug 1",
                "mute", "win" if (score or 0) >= 70 else "ink",
                "star", "jewel", 0),
        UI.tile("Follow-ups Today", str(len(cc["due"])),
                "+" + str(len(cc["over"])) + " overdue",
                "loss" if cc["over"] else "mute",
                "win" if cc["due"] else "ink", "users", "accent", 40),
        UI.tile("Sold Today", str(sold_today),
                str(rej_today) + " rejected", "mute",
                "win" if sold_today else "ink", "phone", "win", 80),
        UI.tile("Journal Streak", str(jstreak), "consecutive days",
                "win" if jstreak else "mute",
                "win" if jstreak else "ink", "flame", "jewel", 120),
        UI.tile("Habits Today",
                str(done_today) + "/" + str(total_h), "checked",
                "mute", "ink", "check", "accent", 160),
    ]
    st.markdown(UI.tiles_grid(row1, 5), unsafe_allow_html=True)

    # ---- row 2: consistency spine + right now ----
    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        if any(log.values()):
            series = M.consistency_series(log, habits, 30)
            body = UI.equity_svg(series, "now_eq", kind="pct",
                                 xfmt=lambda d: d.strftime("%d"))
        else:
            body = UI.empty_state(
                "The spine lights up after your first checked day. "
                "Recording begins Aug 1, 2026.")
        st.markdown(UI.panel("Consistency Trend", body,
                             right="last 30 days"),
                    unsafe_allow_html=True)
    with c2:
        cur_tag = cur.get("tag", "Life") if cur else "Life"
        cur_color = D.TAG_COLORS.get(cur_tag, "#7C8AA5")
        st.markdown(UI.panel(
            "Right Now",
            UI.now_card(now_dt.strftime("%H:%M"), cur, cur_tag,
                        cur_color, prog,
                        nxt["time"] if nxt else "--:--",
                        nxt["label"] if nxt else "")),
            unsafe_allow_html=True)

    # ---- row 3: eight stat tiles (life + business + money) ----
    row3 = [
        UI.tile("New Leads 7d", str(cc["new7"]), "ads + live",
                "mute", "ink", "bolt", "accent", 0),
        UI.tile("Active Pipeline", str(cc["active"]), "in journey",
                "mute", "ink", "users", "accent", 30),
        UI.tile("Call Sheet", str(len(sheet)), "phone them",
                "win" if sheet else "mute",
                "win" if sheet else "ink", "phone", "win", 60),
        UI.tile("Return Windows", str(len(window)), "7-day open",
                "mute", "ink", "cal", "jewel", 90),
        UI.tile("Commissions Due", str(len(com["due_today"])),
                "today", "win" if com["due_today"] else "mute",
                "ink", "cash", "win", 120),
        UI.tile("Income 7d", "KSh " + U.fmt_k(inc_week),
                "all sources", "win" if inc_week else "mute",
                "win" if inc_week else "ink", "trend", "win", 150),
        UI.tile("Net Worth", "KSh " + U.fmt_k(net), "everything",
                "mute", "ink", "star", "jewel", 180),
        UI.tile("Cash On Hand", "KSh " + U.fmt_k(cash),
                str(len(bills_late)) + " bills overdue",
                "loss" if bills_late else "mute", "ink",
                "cash", "accent", 210),
    ]
    st.markdown(UI.tiles_grid(row3, 8), unsafe_allow_html=True)

    # ---- row 4: pipeline funnel + income mix ----
    f1, f2 = st.columns([3, 2], gap="medium")
    with f1:
        sc = M.stage_counts(clients)
        items = [(D.STAGE_LABEL[sid], sc.get(sid, 0),
                  D.STAGE_COLOR[sid]) for sid in D.STAGE_IDS
                 if sc.get(sid, 0) > 0]
        st.markdown(UI.panel("TrueWave Pipeline", UI.hbars(items),
                             right=str(len(clients)) + " clients"),
                    unsafe_allow_html=True)
    with f2:
        ibt = M.income_by_type(income)
        items = [(k, v, "#34D399") for k, v in
                 sorted(ibt.items(), key=lambda x: x[1],
                        reverse=True)]
        st.markdown(UI.panel("Income Mix - since Aug 1",
                             UI.hbars(items)),
                    unsafe_allow_html=True)

    # ---- row 5: calendar + today + focus split ----
    c3, c4, c5 = st.columns([5, 3, 4], gap="medium")
    with c3:
        cmap = M.day_consistency_map(log, habits, today.year,
                                     today.month, today)
        st.markdown(UI.panel(
            "Consistency Calendar",
            UI.calendar_html(today.year, today.month, cmap,
                             today=today, pct=True),
            right=today.strftime("%B")), unsafe_allow_html=True)
    with c4:
        je = journal.get(t_iso)
        open_i, over_i = M.issues_open(issues, today)
        wl = M.weight_latest(weights)
        day_n = max(1, (today - D.START_DATE).days + 1) \
            if started else 0
        pairs = [
            ("Recording day",
             str(day_n) if started else "starts Aug 1"),
            ("Blocks done",
             str(max(idx + 1, 0)) + " / " + str(len(blocks))),
            ("Habits done", '<span class="tw-win">'
             + str(done_today) + " / " + str(total_h) + "</span>"),
            ("Tasks", str(tc["done_today"]) + " done - "
             + str(tc["open"]) + " open"),
            ("Journaled", "Yes" if je else "No"),
            ("Follow-ups", str(len(cc["due"])) + " due - "
             + str(len(cc["over"])) + " late"),
            ("Return windows", str(len(window))),
            ("Weight", (U.fmt_num(wl["kg"]) + " kg") if wl else "--"),
        ]
        st.markdown(UI.panel("Today", UI.kv(pairs), right="live"),
                    unsafe_allow_html=True)
    with c5:
        split = M.today_area_split(ctx["routine"], today.weekday())
        total_b = sum(s[1] for s in split) or 1
        st.markdown(UI.panel(
            "Focus Split Today",
            UI.donut(split, str(total_b), "blocks", total_b)),
            unsafe_allow_html=True)

    # ---- row 6: call sheet + streaks ----
    c6, c7 = st.columns([4, 1], gap="medium")
    with c6:
        if sheet:
            body = "".join(UI.client_card(c, today)
                           for c in sheet[:6])
        else:
            body = UI.empty_state(
                "Call sheet is clear. Log inquiries on TrueWave and "
                "they surface here on their day.")
        st.markdown(UI.panel("Today's Call Sheet - hottest first",
                             body, right="TrueWave"),
                    unsafe_allow_html=True)
    with c7:
        w_streak = 0
        for h in habits:
            if h["name"].startswith("Workout"):
                w_streak = M.habit_streak(log, h["id"])
        st.markdown(UI.panel(
            "Streaks",
            UI.streaks_html([
                (jstreak, "journal", "accent"),
                (M.sales_streak(daily, today), "sales logs", "win"),
                (w_streak, "workout", "jewel"),
            ])), unsafe_allow_html=True)

    # ---- row 7: commissions week + vault teaser ----
    c8, c9 = st.columns([3, 2], gap="medium")
    with c8:
        rows = []
        for s, i in M.commissions_window(sales, today, 7):
            rows.append([
                (html.escape(i["due"]), "num"),
                (html.escape(str(s.get("client", ""))), ""),
                (html.escape(str(s.get("phone", ""))), ""),
                (U.fmt_kes(float(i.get("amount", 0))), "num"),
            ])
        st.markdown(UI.panel(
            "Commissions Due - next 7 days",
            UI.table(["Due", "Client", "Phone", "Amount"], rows),
            right="KSh " + U.fmt_k(com["pending"]) + " pending"),
            unsafe_allow_html=True)
    with c9:
        tgt = 150000.0
        pct = max(0.0, min(100.0, net / tgt * 100)) if tgt else 0.0
        body = (
            '<div class="tw-lab" style="margin-bottom:8px">'
            'MONEY &middot; LOCKED</div>'
            + UI.progress(pct, "var(--accent)")
            + UI.kv([("Net worth", "KSh " + U.fmt_k(net)),
                     ("Cash on hand", "KSh " + U.fmt_k(cash))]))
        )
        st.markdown(UI.panel("Archive", body, right="PIN"),
                    unsafe_allow_html=True)

    # ---- row 8: tick habits + rhythm ----
    st.markdown("<div style='height:6px'></div>",
                unsafe_allow_html=True)
    hc1, hc2 = st.columns([2, 3], gap="medium")
    with hc1:
        pct = (done_today / total_h * 100) if total_h else 0
        tone = "tw-win" if pct >= 70 else (
            "tw-loss" if pct < 40 else "tw-ink")
        head = (
            '<div style="display:flex;justify-content:space-between;'
            'align-items:baseline">'
            '<span class="tw-val ' + tone + '" style="font-size:22px">'
            + str(done_today) + "/" + str(total_h) + '</span>'
            '<span class="tw-lab">' + format(pct, ".0f")
            + '% today</span></div>'
        )
        st.markdown(UI.panel("Tick Today's Habits", head),
                    unsafe_allow_html=True)
        W.habit_checklist("now", habits, log, t_iso)
    with hc2:
        st.markdown(UI.panel("Today's Rhythm - " + ctx["day_type"],
                             UI.timeline_html(blocks, idx)),
                    unsafe_allow_html=True)
