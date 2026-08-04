"""Sales - lead intake + daily tally + commissions + income.
Lead form calls add_client with the exact argument order data.py expects
(budget passed empty), then stores location via update_client, so it works
with the current data layer. Marking a commission PAID drops the cash into a
chosen pocket (live). Commissions auto-due +20/+50 days, locked after.
"""
from __future__ import annotations

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U


def _pocket_options(vault):
    positions = vault.get("positions", [])
    names = ["— none —"] + [p["name"] for p in positions]
    ids = [""] + [p["id"] for p in positions]
    return names, ids


def _lead_form(ctx):
    with st.expander("+  Log a new lead"):
        a, b, c3 = st.columns(3)
        with a:
            name = st.text_input("Client name", key="cl_n")
            phone = st.text_input("Phone number", key="cl_p")
            source = st.selectbox("Source", D.SOURCES, key="cl_s")
        with b:
            loc = st.text_input("Location", key="cl_loc",
                                placeholder="e.g. Kasarani, Nairobi")
            want = st.text_input("Wants (phone / model)", key="cl_w")
            heat = st.selectbox("Heat", D.HEATS, key="cl_h")
        with c3:
            note = st.text_input(
                "First note", key="cl_note",
                placeholder="texted from the ad, wants an iPhone...")
        if st.button("Add lead", type="primary",
                     key="cl_add") and name.strip():
            D.add_client(name.strip(), phone.strip(), source, heat,
                         want.strip(), "", note.strip(),
                         ctx["today_iso"], ctx["now_str"])
            if loc.strip():
                newc = st.session_state["clients"][0]
                D.update_client(newc["id"],
                                {"location": loc.strip()},
                                ctx["now_str"])
            st.rerun()


def render(ctx):
    daily, sales = ctx["sales_daily"], ctx["sales"]
    income = ctx["income"]
    vault = ctx["vault"]
    today, t_iso = ctx["today"], ctx["today_iso"]
    now_time = ctx["now_dt"].strftime("%H:%M")
    pnames, pids = _pocket_options(vault)

    _lead_form(ctx)

    sold_week = sum(v for _l, v in M.week_sales(daily, today, 7))
    sys30, cash30 = M.rejects_30d(daily, today)
    com = M.commission_stats(sales, t_iso)
    locked = [(s, i) for s, i in com["overdue"]
              if not M.comm_editable(s, i, today)]
    month_lo = today.replace(day=1).isoformat()
    inc_month = M.income_total(income, month_lo, t_iso)
    row = [
        UI.tile("Sold This Week", str(sold_week), "phones",
                "win" if sold_week else "mute",
                "win" if sold_week else "ink", "phone", "win", 0),
        UI.tile("System Rejects", str(sys30), "30 days",
                "mute", "ink", "x", "jewel", 40),
        UI.tile("Cash-Only Rejects", str(cash30), "30 days",
                "mute", "ink", "cash", "jewel", 80),
        UI.tile("Commissions Pending",
                "KSh " + U.fmt_k(com["pending"]), "expected",
                "mute", "ink", "clock", "accent", 120),
        UI.tile("Locked Overdue", str(len(locked)),
                "KSh " + U.fmt_k(sum(float(i.get("amount", 0))
                                     for _s, i in locked))
                + " slipping",
                "loss" if locked else "mute",
                "loss" if locked else "ink", "lock", "loss", 160),
        UI.tile("Income This Month", "KSh " + U.fmt_k(inc_month),
                "all sources", "win" if inc_month else "mute",
                "win" if inc_month else "ink", "trend", "win", 200),
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
        st.markdown(UI.panel(
            "Log a Sale - commissions auto-due +20 / +50 days",
            '<div style="height:2px"></div>'), unsafe_allow_html=True)
        sd = st.date_input("Sale date", value=today, key="sl_d")
        cl = st.text_input("Client", key="sl_c")
        ph = st.text_input("Phone / model", key="sl_p")
        dv = st.date_input("Delivered date (anchors the windows)",
                           value=today, key="sl_dv")
        i1, i2 = st.columns(2)
        with i1:
            a1 = st.number_input("1st commission (KSh)", 0.0,
                                 1000000.0, 0.0, step=50.0, key="sl_a1")
        with i2:
            a2 = st.number_input("2nd commission (KSh)", 0.0,
                                 1000000.0, 0.0, step=50.0, key="sl_a2")
        if st.button("Add sale", type="primary", key="sl_add"):
            inst = []
            if a1 > 0:
                inst.append({"n": 1, "amount": a1,
                             "window": D.COMM_WINDOWS[1]})
            if a2 > 0:
                inst.append({"n": 2, "amount": a2,
                             "window": D.COMM_WINDOWS[2]})
            if inst:
                D.add_sale({"date": sd.isoformat(),
                            "client": cl.strip(), "phone": ph.strip(),
                            "delivered_date": dv.isoformat(),
                            "commission": float(a1) + float(a2),
                            "inst": inst})
                st.rerun()

    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    st.markdown('<div class="tw-lab" style="margin:4px 0 8px">'
                'COMMISSION TRACKER - MARK PAID TO DROP CASH INTO A '
                'POCKET (LIVE)</div>', unsafe_allow_html=True)
    inst_rows = []
    for s in sales:
        for i in s.get("inst", []):
            inst_rows.append((s, i))
    inst_rows.sort(key=lambda p: (p[1].get("due") or "",
                                  bool(p[1].get("paid", False))))
    if not inst_rows:
        st.markdown(UI.panel("Commissions", UI.empty_state(
            "No instalments yet - log a sale above.")),
            unsafe_allow_html=True)
    for s, i in inst_rows:
        editable = M.comm_editable(s, i, today)
        was_paid = bool(i.get("paid"))
        if was_paid:
            chip = ("PAID", "#34D399")
        elif not editable:
            chip = ("LOCKED - UNPAID", "#F0556B")
        elif (i.get("due") or "") < t_iso:
            chip = ("OVERDUE", "#F0556B")
        else:
            chip = ("DUE " + str(i.get("window", 20)) + "d", "#F5B544")
        c1, c2, c3, c4, c5, c6 = st.columns(
            [1.2, 1.8, 1.0, 1.8, 1.4, 0.9])
        with c1:
            st.markdown('<div style="padding-top:6px">'
                        '<div class="tw-sub">'
                        + str(i.get("due", "--")) + '</div>'
                        + UI.badge(chip[0], chip[1]) + '</div>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown(UI.client_line(s.get("client", ""),
                                       s.get("phone", "")),
                        unsafe_allow_html=True)
        with c3:
            st.markdown('<div style="padding-top:6px">'
                        + UI.amt_span(float(i.get("amount", 0)),
                                      signed=False, tone="flat")
                        + '</div>', unsafe_allow_html=True)
        with c4:
            if editable:
                reason = st.text_input("reason unpaid",
                                       value=i.get("reason", ""),
                                       key="cr" + i["id"],
                                       placeholder="why it hasn't landed")
            else:
                st.caption("locked - "
                           + (i.get("reason") or "no reason recorded"))
        with c5:
            if editable and not was_paid:
                psel = st.selectbox("drop into pocket on pay", pnames,
                                    key="cpk" + i["id"])
            elif was_paid:
                st.caption("paid " + str(i.get("paid_date", ""))
                           + (" → " + str(i.get("paid_pocket", ""))
                              if i.get("paid_pocket") else ""))
            else:
                st.caption("locked")
        with c6:
            if editable:
                paid = st.checkbox("paid", value=was_paid,
                                   key="cp" + i["id"])
                if st.button("Save", key="cb" + i["id"]):
                    if paid and not was_paid:
                        i["paid_date"] = t_iso
                        if pnames and psel != "— none —":
                            pid = pids[pnames.index(psel)]
                            D.move_money(pid, float(i.get("amount", 0)),
                                         "in",
                                         note="commission: "
                                         + str(s.get("client", "")),
                                         time_str=now_time, txid="")
                        i["paid_pocket"] = psel
                    i["paid"] = bool(paid)
                    i["reason"] = reason.strip() if editable else \
                        i.get("reason", "")
                    D.save_sales(sales)
                    st.rerun()
            else:
                st.markdown('<div style="padding-top:10px">'
                            + UI.badge("LOCKED", "#7C8AA5") + '</div>',
                            unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>",
                unsafe_allow_html=True)
    st.markdown('<div class="tw-lab" style="margin:4px 0 8px">'
                'INCOME &amp; EXTRAS - BONUS / DRV / STOCK / GIFTS'
                '</div>', unsafe_allow_html=True)
    g1, g2 = st.columns([3, 2], gap="medium")
    with g1:
        a, b, c = st.columns([1.2, 1.4, 1.2])
        with a:
            idate = st.date_input("date", value=today, key="in_d")
            itype = st.selectbox("type", D.INCOME_TYPES, key="in_t")
        with b:
            iamt = st.number_input("amount (KSh)", 0.0, 100000000.0,
                                   0.0, step=100.0, key="in_a")
        with c:
            inote = st.text_input("note", key="in_n")
        ipk = st.selectbox("also drop into pocket (optional)", pnames,
                           key="in_pk")
        if st.button("Add income", type="primary",
                     key="in_add") and iamt > 0:
            D.add_income(idate.isoformat(), itype, iamt, inote.strip())
            if ipk != "— none —":
                pid = pids[pnames.index(ipk)]
                D.move_money(pid, float(iamt), "in",
                             note="income: " + itype
                             + (" - " + inote.strip() if inote.strip()
                                else ""),
                             time_str=now_time, txid="")
            st.rerun()
        st.markdown(UI.income_log_rows(income, 12),
                    unsafe_allow_html=True)
    with g2:
        ibt = M.income_by_type(income)
        items = [(k, v, "#34D399") for k, v in
                 sorted(ibt.items(), key=lambda x: x[1],
                       reverse=True)]
        st.markdown(UI.panel("By Source - since Aug 1", UI.hbars(items),
                             right=U.fmt_kes(M.income_total(income))),
                    unsafe_allow_html=True)

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
            n_paid = sum(1 for i in s.get("inst", [])
                         if i.get("paid"))
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
