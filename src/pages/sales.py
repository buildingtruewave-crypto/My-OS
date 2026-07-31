"""Daily sales log + commission instalments (1st / 2nd due dates, paid
or unpaid-with-reason) so money that should arrive never disappears."""
from __future__ import annotations

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U


def render(ctx):
    daily, sales = ctx["sales_daily"], ctx["sales"]
    today, t_iso = ctx["today"], ctx["today_iso"]

    sold_week = sum(v for _l, v in M.week_sales(daily, today, 7))
    sold_all = sum(int(e.get("sold", 0)) for e in daily.values())
    sys30, cash30 = M.rejects_30d(daily, today)
    com = M.commission_stats(sales, t_iso)

    row = [
        UI.tile("Sold This Week", str(sold_week), "phones",
                "win" if sold_week else "mute",
                "win" if sold_week else "ink", "phone", "win", 0),
        UI.tile("Sold Since Aug 1", str(sold_all), "all time",
                "mute", "ink", "trend", "accent", 40),
        UI.tile("System Rejects", str(sys30), "30 days",
                "mute", "ink", "x", "jewel", 80),
        UI.tile("Cash-Only Rejects", str(cash30), "30 days",
                "mute", "ink", "cash", "jewel", 120),
        UI.tile("Commissions Pending",
                "KSh " + U.fmt_k(com["pending"]), "uncollected",
                "mute", "ink", "clock", "accent", 160),
        UI.tile("Overdue Instalments", str(len(com["overdue"])),
                "KSh " + U.fmt_k(sum(float(i.get("amount", 0))
                                     for _s, i in com["overdue"])),
                "loss" if com["overdue"] else "mute",
                "loss" if com["overdue"] else "ink", "bolt", "loss",
                200),
    ]
    st.markdown(UI.tiles_grid(row, 6), unsafe_allow_html=True)

    f1, f2 = st.columns(2, gap="medium")
    with f1:
        st.markdown(UI.panel("End-of-Day Tally",
                             '<div style="height:2px"></div>'),
                    unsafe_allow_html=True)
        cur = daily.get(t_iso) or {}
        dte = st.date_input("Date", value=today, key="sd_d")
        a, b, c = st.columns(3)
        with a:
            sold = st.number_input("Phones sold", 0, 500,
                                   int(cur.get("sold", 0)), key="sd_s")
        with b:
            sysr = st.number_input("Rejected by system", 0, 500,
                                   int(cur.get("system_rej", 0)),
                                   key="sd_y")
        with c:
            cashr = st.number_input("Cash-only rejects", 0, 500,
                                    int(cur.get("cash_rej", 0)),
                                    key="sd_c")
        notes = st.text_input("Notes", value=cur.get("notes", ""),
                              key="sd_n")
        if st.button("Save tally", type="primary", key="sd_save"):
            D.save_daily_entry(dte.isoformat(), {
                "sold": int(sold), "system_rej": int(sysr),
                "cash_rej": int(cashr), "notes": notes.strip(),
            })
            st.success("Saved.")
            st.rerun()
    with f2:
        st.markdown(UI.panel("Log a Sale + Commission Split",
                             '<div style="height:2px"></div>'),
                    unsafe_allow_html=True)
        sd = st.date_input("Sale date", value=today, key="sl_d")
        cl = st.text_input("Client", key="sl_c")
        ph = st.text_input("Phone / model", key="sl_p")
        comm = st.number_input("Total commission (KSh)", 0.0,
                               1000000.0, 0.0, step=50.0, key="sl_t")
        i1, i2 = st.columns(2)
        with i1:
            a1 = st.number_input("1st instalment (KSh)", 0.0,
                                 1000000.0, 0.0, step=50.0, key="sl_a1")
            d1 = st.date_input("1st due", value=today, key="sl_d1")
        with i2:
            a2 = st.number_input("2nd instalment (KSh)", 0.0,
                                 1000000.0, 0.0, step=50.0, key="sl_a2")
            d2 = st.date_input("2nd due", value=today, key="sl_d2")
        if st.button("Add sale", type="primary", key="sl_add"):
            inst = []
            if a1 > 0:
                inst.append({"amount": a1, "due": d1.isoformat()})
            if a2 > 0:
                inst.append({"amount": a2, "due": d2.isoformat()})
            if not inst and comm > 0:
                inst.append({"amount": comm, "due": sd.isoformat()})
            D.add_sale({"date": sd.isoformat(), "client": cl.strip(),
                        "phone": ph.strip(), "commission": comm,
                        "inst": inst})
            st.rerun()

    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    st.markdown('<div class="tw-lab" style="margin:4px 0 8px">'
                'COMMISSION TRACKER - MARK PAID OR WHY NOT</div>',
                unsafe_allow_html=True)
    inst_rows = []
    for s in sales:
        for i in s.get("inst", []):
            inst_rows.append((s, i))
    inst_rows.sort(key=lambda p: (p[1].get("due") or "",
                                  p[1].get("paid", False)))
    if not inst_rows:
        st.markdown(UI.panel("Commissions", UI.empty_state(
            "No instalments yet - log a sale above.")),
            unsafe_allow_html=True)
    for s, i in inst_rows:
        status = ("PAID", "#34D399") if i.get("paid") else (
            ("OVERDUE", "#F0556B")
            if (i.get("due") or "") < t_iso else ("DUE", "#F5B544"))
        c1, c2, c3, c4, c5 = st.columns([1.2, 2, 1.2, 2.4, 1])
        with c1:
            st.markdown('<div style="padding-top:6px">'
                        '<div class="tw-sub">'
                        + str(i.get("due", "--")) + '</div>'
                        + UI.badge(status[0], status[1]) + '</div>',
                        unsafe_allow_html=True)
        with c2:
            st.caption(str(s.get("client", "?")) + " - "
                       + str(s.get("phone", "")))
        with c3:
            st.markdown('<div class="tw-val" style="font-size:16px;'
                        'padding-top:8px">'
                        + U.fmt_kes(float(i.get("amount", 0)))
                        + '</div>', unsafe_allow_html=True)
        with c4:
            reason = st.text_input("reason unpaid",
                                   value=i.get("reason", ""),
                                   key="cr" + i["id"],
                                   placeholder="why it hasn't landed")
        with c5:
            paid = st.checkbox("paid", value=bool(i.get("paid")),
                               key="cp" + i["id"])
            if st.button("Save", key="cb" + i["id"]):
                i["paid"] = bool(paid)
                i["reason"] = reason.strip()
                D.save_sales(sales)
                st.rerun()

    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    t1, t2 = st.columns(2, gap="medium")
    with t1:
        rows = []
        for d_iso in sorted(daily.keys(), reverse=True)[:10]:
            e = daily[d_iso]
            rows.append([
                (d_iso, "num"), (str(e.get("sold", 0)), "num"),
                (str(e.get("system_rej", 0)), "num"),
                (str(e.get("cash_rej", 0)), "num"),
                (str(e.get("notes", "")), ""),
            ])
        st.markdown(UI.panel("Recent Tallies",
                             UI.table(["Date", "Sold", "Sys-Rej",
                                       "Cash-Rej", "Notes"], rows)),
                    unsafe_allow_html=True)
    with t2:
        rows = []
        for s in sales[:12]:
            n_inst = len(s.get("inst", []))
            n_paid = sum(1 for i in s.get("inst", []) if i.get("paid"))
            rows.append([
                (s.get("date", ""), "num"),
                (str(s.get("client", "")), ""),
                (str(s.get("phone", "")), ""),
                (U.fmt_kes(float(s.get("commission", 0))), "num"),
                (str(n_paid) + "/" + str(n_inst), "num"),
            ])
        st.markdown(UI.panel("Sales Log",
                             UI.table(["Date", "Client", "Phone",
                                       "Commission", "Paid"], rows)),
                    unsafe_allow_html=True)
