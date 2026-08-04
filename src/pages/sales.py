"""Sales - lead intake + the full journey desk + tally + commissions + income.
Add a lead, then carry it to the end on the same page: move stage, plan &
numbers, docs, credit outcome, delivery & return window, paid / declined /
returned, journey-end / reopen, and a touch log. Uses only long-standing
data.py helpers so nothing breaks. Marking a commission PAID drops the cash
into a chosen pocket (live). Commissions auto-due +20/+50 days, locked after.
"""
from __future__ import annotations

import datetime as dt

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


def _plan_options():
    return [""] + [p["label"] for p in D.get_plans()]


# ---------------------------------------------------------------------------
# lead intake
# ---------------------------------------------------------------------------
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
                D.update_client(newc["id"], {"location": loc.strip()},
                                ctx["now_str"])
            st.rerun()


# ---------------------------------------------------------------------------
# journey desk pieces (ported, universal helpers only)
# ---------------------------------------------------------------------------
def _journey(c, ctx, k):
    today, now_str = ctx["today"], ctx["now_str"]
    ids = D.all_stage_ids()
    st.markdown(UI.stepper_html(c), unsafe_allow_html=True)
    j1, j2 = st.columns([2, 1])
    with j1:
        cur_idx = ids.index(c["stage"]) if c["stage"] in ids else 0
        ns = st.selectbox("Move to stage", ids,
                          format_func=D.stage_label,
                          index=cur_idx, key=k + "st")
    with j2:
        st.markdown("<div style='height:26px'></div>",
                    unsafe_allow_html=True)
        if st.button("Move stage", type="primary", key=k + "mv"):
            if ns != c["stage"]:
                D.set_stage(c["id"], ns, now_str)
                st.rerun()
    plan_opts = _plan_options()
    cur_p = c.get("plan", "") or ""
    pi = plan_opts.index(cur_p) if cur_p in plan_opts else 0
    plan = st.radio("Payment plan", plan_opts, index=pi,
                    horizontal=True,
                    format_func=lambda p: p or "Not chosen",
                    key=k + "pl")
    if plan != cur_p:
        D.update_client(c["id"], {"plan": plan}, now_str,
                        "Plan -> " + (plan or "none"))
        st.rerun()
    if plan:
        note = D.plan_note(plan)
        if note:
            st.caption(note)
    q1, q2 = st.columns(2)
    with q1:
        qual = st.text_input("Qualified (M-Pesa review)",
                             value=c.get("qualified", ""), key=k + "qf")
        dep = st.number_input("Deposit (KSh)", 0.0, 1000000.0,
                              float(c.get("deposit", 0) or 0),
                              step=500.0, key=k + "dp")
    with q2:
        wkly = st.number_input("Weekly (KSh)", 0.0, 1000000.0,
                               float(c.get("weekly", 0) or 0),
                               step=100.0, key=k + "wk")
        na = st.text_input("Next action",
                           value=c.get("next_action", ""), key=k + "na")
    nd = st.date_input("Next action date", value=today, key=k + "nd")
    if st.button("Save plan & numbers", key=k + "sv"):
        D.update_client(c["id"], {
            "qualified": qual, "deposit": float(dep),
            "weekly": float(wkly), "next_action": na,
            "next_date": nd.isoformat(),
        }, now_str, "Plan / numbers / next action updated")
        st.rerun()


def _verify(c, ctx, k):
    today, now_str = ctx["today"], ctx["now_str"]
    ids = D.all_stage_ids()
    dr = D.role_id("delivered")
    wr = D.role_id("won")
    rr = D.role_id("returned")
    st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                'DOCS &amp; VERIFICATION</div>', unsafe_allow_html=True)
    docs = dict(c.get("docs") or {})
    changed = False
    dcols = st.columns(3)
    for i, key_id in enumerate(D.DOC_ITEMS):
        curv = docs.get(key_id, "pending")
        with dcols[i]:
            v = st.selectbox(D.DOC_LABEL[key_id], D.DOC_STATES,
                             index=D.DOC_STATES.index(curv)
                             if curv in D.DOC_STATES else 0,
                             key=k + "d" + key_id)
        if v != curv:
            docs[key_id] = v
            changed = True
    if changed:
        failed = [D.DOC_LABEL[i2] for i2 in D.DOC_ITEMS
                  if docs.get(i2) == "failed"]
        D.update_client(c["id"], {"docs": docs}, now_str,
                        "Docs updated"
                        + (" - FAILED: " + ", ".join(failed)
                           if failed else ""))
        st.rerun()
    cur_credit = c.get("credit", "pending")
    credit = st.selectbox("Credit team outcome", D.CREDIT_OUTCOMES,
                          index=D.CREDIT_OUTCOMES.index(cur_credit)
                          if cur_credit in D.CREDIT_OUTCOMES else 0,
                          key=k + "cr")
    default_stage = c.get("stage", "")
    if credit == "CASH OFFER - CREDIT":
        cand = D.role_id("cash")
        if cand and cand in ids:
            default_stage = cand
    ri = ids.index(default_stage) if default_stage in ids else 0
    res_stage = st.selectbox("Resulting stage", ids, index=ri,
                             format_func=D.stage_label, key=k + "rs")
    if st.button("Save credit & stage", key=k + "cs"):
        patch = {"credit": credit}
        if credit != "pending":
            patch["stage"] = res_stage
        D.update_client(c["id"], patch, now_str,
                        "Credit -> " + credit
                        + (" / stage -> " + D.stage_label(res_stage)
                           if credit != "pending" else ""))
        st.rerun()
    st.markdown('<div class="tw-lab" style="margin:14px 0 8px">'
                'DELIVERY &amp; RETURN WINDOW</div>',
                unsafe_allow_html=True)
    w = M.window_info(c, today)
    if c.get("delivered_date"):
        pairs = [("Delivered", c["delivered_date"])]
        if w:
            pairs.append(("Window closes", w["close"].isoformat()))
            pairs.append(("Window", "CLOSED" if w["closed"]
                          else (str(w["left"]) + " days left")))
        if c.get("paid_date"):
            pairs.append(("Paid", c["paid_date"]))
        if c.get("returned_date"):
            pairs.append(("Returned", c["returned_date"]))
        st.markdown(UI.kv(pairs), unsafe_allow_html=True)
    e1, e2, e3 = st.columns(3)
    with e1:
        dd = st.date_input("delivered date", value=today, key=k + "dd")
        if st.button("Set delivered", key=k + "ds", disabled=dr is None):
            D.update_client(c["id"],
                            {"delivered_date": dd.isoformat(),
                             "stage": dr}, now_str,
                            "Delivered - 7-day return window OPEN")
            st.rerun()
        if dr is None:
            st.caption("tag a stage 'delivered'")
    with e2:
        if st.button("Mark PAID", key=k + "pd",
                     disabled=(wr is None) or bool(c.get("paid"))):
            D.update_client(c["id"],
                            {"paid": True,
                             "paid_date": today.isoformat(),
                             "stage": wr}, now_str,
                            "Client PAID - deal closed")
            st.rerun()
        if wr is None:
            st.caption("tag a stage 'won'")
    with e3:
        window_open = bool(w) and not w["closed"]
        if st.button("Mark RETURNED", key=k + "rt",
                     disabled=(rr is None) or bool(c.get("returned"))
                     or not window_open):
            D.update_client(c["id"],
                            {"returned": True,
                             "returned_date": today.isoformat(),
                             "stage": rr}, now_str,
                            "Phone RETURNED inside the window")
            st.rerun()
        if rr is None:
            st.caption("tag a stage 'returned'")
    r1, r2 = st.columns(2)
    with r1:
        rem = st.text_input("Remark", value=c.get("remark", ""),
                            key=k + "rm")
    with r2:
        why = st.text_input("Why not today?",
                            value=c.get("why_not", ""), key=k + "wn")
    if st.button("Save remarks", key=k + "rs2"):
        D.update_client(c["id"], {"remark": rem, "why_not": why},
                        now_str)
        st.rerun()


def _memory(c, ctx, k):
    now_str = ctx["now_str"]
    st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                'CLIENT MEMORY</div>', unsafe_allow_html=True)
    note = st.text_input("Log a touch", key=k + "tn",
                         placeholder="called - didn't pick / picked, said Friday...")
    if st.button("Log touch", type="primary",
                 key=k + "tb") and note.strip():
        D.touch_client(c["id"], note.strip(), now_str)
        st.rerun()
    st.markdown(UI.history_html(c.get("history", [])),
                unsafe_allow_html=True)


def _journey_desk(ctx):
    clients = ctx["clients"]
    now_str = ctx["now_str"]
    if not clients:
        st.caption("No clients yet - log a lead above.")
        return
    st.markdown('<div class="tw-lab" style="margin:4px 0 8px">'
                'CLIENT JOURNEY DESK - finish the journey here</div>',
                unsafe_allow_html=True)
    names = [str(c.get("name", "?")) + "  ·  "
             + D.stage_label(c.get("stage", "new"), "?")
             for c in clients]
    sel = st.selectbox("client", range(len(clients)),
                       format_func=lambda i: names[i], key="jd_sel")
    c = clients[sel]
    k = "jd" + c["id"]
    st.markdown(UI.badge(D.stage_label(c.get("stage", "new"), "?"),
                         D.stage_color(c.get("stage", "new"))),
                unsafe_allow_html=True)
    if c.get("ended"):
        if st.button("Reopen journey", key=k + "re"):
            D.update_client(c["id"], {"ended": False, "ended_date": ""},
                            now_str, "Journey reopened")
            st.rerun()
    else:
        sure = st.checkbox("confirm end journey", key=k + "ejc")
        if st.button("End journey", key=k + "ej", disabled=not sure):
            D.update_client(c["id"],
                            {"ended": True,
                             "ended_date": ctx["today_iso"]},
                            now_str, "Journey ended")
            st.rerun()
    d1, d2, d3 = st.columns([5, 4, 3], gap="medium")
    with d1:
        _journey(c, ctx, k)
    with d2:
        _verify(c, ctx, k)
    with d3:
        _memory(c, ctx, k)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
def render(ctx):
    daily, sales = ctx["sales_daily"], ctx["sales"]
    income = ctx["income"]
    vault = ctx["vault"]
    today, t_iso = ctx["today"], ctx["today_iso"]
    now_time = ctx["now_dt"].strftime("%H:%M")
    pnames, pids = _pocket_options(vault)

    _lead_form(ctx)
    _journey_desk(ctx)

    st.markdown("<div style='height:12px'></div>",
                unsafe_allow_html=True)
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
