"""Sales - the single filling point: lead intake in the exact order
(name, phone, source, location, wants, heat, first note), then the connected
journey desk - call result (follow-back date+time+what was said), agreed to
proceed (ID number + plan), pre-screen (M-Pesa), docs (ID front/back, selfie,
next of kin), credit briefing + convert, credit outcomes, deposit & delivery
/ pick-up, ready/assigned/out/delivered, failed with reason, paid / declined
/ returned / exchanged. Plus tally / commissions / income.
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
            want = st.text_input("Wants (phone model)", key="cl_w")
            heat = st.selectbox("Heat", D.HEATS, key="cl_h")
        with c3:
            note = st.text_input(
                "First note", key="cl_note",
                placeholder="texted from the ad, wants an iPhone...")
        if st.button("Add lead", type="primary",
                     key="cl_add") and name.strip():
            D.add_client(name.strip(), phone.strip(), source, heat,
                         want.strip(), note.strip(),
                         ctx["today_iso"], ctx["now_str"],
                         location=loc.strip())
            st.rerun()


def _call_result(c, ctx, k):
    today, now_str = ctx["today"], ctx["now_str"]
    st.markdown('<div class="tw-lab" style="margin:8px 0 6px">'
                'CALL RESULT</div>', unsafe_allow_html=True)
    r1, r2 = st.columns([2, 1])
    with r1:
        result = st.selectbox("result", D.CALL_RESULTS, key=k + "res")
    with r2:
        fb_on = st.checkbox("follow-back", key=k + "fb")
    if fb_on:
        f1, f2, f3 = st.columns(3)
        with f1:
            fbd = st.date_input("follow-back date", value=today,
                                key=k + "fbd")
        with f2:
            fbt = st.time_input("time", key=k + "fbt")
        with f3:
            fbs = st.text_input("what was said", key=k + "fbs")
    if st.button("Save call result", type="primary", key=k + "save"):
        if result == "Agreed to proceed":
            D.update_client(c["id"], {"stage": "agreed",
                                      "follow_done": True},
                            now_str, "Agreed to proceed - "
                            "application started")
        elif result == "Follow-back":
            fa = dt.datetime.combine(fbd, fbt)
            D.update_client(c["id"], {
                "follow_at": fa.isoformat(timespec="minutes"),
                "follow_done": False, "follow_note": fbs.strip(),
                "stage": "followup"},
                now_str, "Follow-back: " + (fbs or "call back"))
        elif result == "Never started":
            D.update_client(c["id"], {"stage": "followup",
                                      "follow_done": False},
                            now_str, "Never started - back to "
                            "follow-ups")
        elif result == "Journey ended":
            D.end_journey(c["id"], now_str, "Journey ended")
        else:
            D.update_client(c["id"], {"follow_done": True},
                            now_str, "Call: " + result)
        st.rerun()


def _application(c, ctx, k):
    now_str = ctx["now_str"]
    st.markdown('<div class="tw-lab" style="margin:8px 0 6px">'
                'APPLICATION - ID NUMBER + PAYMENT PLAN</div>',
                unsafe_allow_html=True)
    po = _plan_options()
    a1, a2 = st.columns(2)
    with a1:
        idn = st.text_input("ID number", value=c.get("id_number", ""),
                            key=k + "id")
    with a2:
        cur_p = c.get("plan", "") or ""
        plan = st.selectbox("Payment plan", po,
                            index=po.index(cur_p) if cur_p in po else 0,
                            key=k + "pl")
    if st.button("Save ID + plan", type="primary", key=k + "idp"):
        D.update_client(c["id"], {"id_number": idn.strip(),
                                  "plan": plan, "stage": "prescreen"},
                        now_str, "ID + plan saved - to pre-screen")
        st.rerun()


def _prescreen(c, ctx, k):
    now_str = ctx["now_str"]
    st.markdown('<div class="tw-lab" style="margin:8px 0 6px">'
                'PRE-SCREENING (M-PESA STATEMENT)</div>',
                unsafe_allow_html=True)
    mp = st.text_input("M-Pesa statement ref / note",
                       value=c.get("mpesa_statement", ""), key=k + "mp")
    pr = st.selectbox("pre-screen result", D.PRESCREEN_RESULTS,
                      index=D.PRESCREEN_RESULTS.index(
                          c.get("prescreen", ""))
                      if c.get("prescreen", "") in D.PRESCREEN_RESULTS
                      else 0, key=k + "pr")
    if pr == "Change payment plan":
        agreed = st.selectbox("client agreed to new plan?",
                              ["", "Agreed", "Undecided"], key=k + "ag")
    if st.button("Apply pre-screen", type="primary", key=k + "go"):
        if pr == "Qualifies":
            D.update_client(c["id"], {"mpesa_statement": mp,
                                      "prescreen": pr,
                                      "stage": "docs"},
                            now_str, "Pre-screened - qualifies")
        elif pr == "Cash offer only":
            D.update_client(c["id"], {"mpesa_statement": mp,
                                      "prescreen": pr,
                                      "stage": "cash_offer",
                                      "ended": True,
                                      "ended_date":
                                      ctx["today_iso"]},
                            now_str, "Cash offer only - journey "
                            "ended")
        elif pr == "Change payment plan":
            if agreed == "Agreed":
                D.update_client(c["id"], {"mpesa_statement": mp,
                                          "prescreen": pr,
                                          "plan_agreed": "yes",
                                          "stage": "docs"},
                                now_str, "Plan changed - agreed")
            else:
                D.update_client(c["id"], {"mpesa_statement": mp,
                                          "prescreen": pr,
                                          "plan_agreed": "no",
                                          "stage": "undecided"},
                                now_str, "Plan changed - undecided, "
                                "back to calls")
        else:
            D.update_client(c["id"], {"mpesa_statement": mp},
                            now_str, "M-Pesa statement logged")
        st.rerun()


def _docs(c, ctx, k):
    now_str = ctx["now_str"]
    st.markdown('<div class="tw-lab" style="margin:8px 0 6px">'
                'DOCS - ID FRONT/BACK + SELFIE + NEXT OF KIN</div>',
                unsafe_allow_html=True)
    docs = dict(c.get("docs") or {})
    d1, d2 = st.columns(2)
    with d1:
        idf = st.text_input("ID front (ref)", value=docs.get(
            "id_front", "") if docs.get("id_front") not in (
            "pending",) else "", key=k + "idf")
        idb = st.text_input("ID back (ref)", value=docs.get(
            "id_back", "") if docs.get("id_back") not in (
            "pending",) else "", key=k + "idb")
    with d2:
        slf = st.text_input("Clear selfie (ref)", value=docs.get(
            "selfie", "") if docs.get("selfie") not in (
            "pending",) else "", key=k + "sf")
        nok = st.text_input("Next of kin", value=docs.get(
            "next_of_kin", "") if docs.get("next_of_kin") not in (
            "pending",) else "", key=k + "nok")
    done_docs = idf and idb and slf and nok
    if st.button("Save docs", type="primary", key=k + "docs",
                 disabled=not done_docs):
        D.update_client(c["id"], {"docs": {
            "id_front": "received", "id_back": "received",
            "selfie": "received", "next_of_kin": "received"},
            "stage": "briefing"},
            now_str, "Docs complete - to credit briefing")
        st.rerun()
    if not done_docs:
        st.caption("Fill all four to move to the credit briefing.")


def _briefing(c, ctx, k):
    now_str = ctx["now_str"]
    st.markdown('<div class="tw-lab" style="margin:8px 0 6px">'
                'CREDIT BRIEFING</div>', unsafe_allow_html=True)
    st.caption("Brief the client so they don't mess the credit call. "
               "Only convert once they agree.")
    agreed = st.checkbox("client agreed to the credit call",
                         value=bool(c.get("brief_agreed")),
                         key=k + "ba")
    if st.button("Convert process", type="primary", key=k + "conv",
                 disabled=not agreed):
        D.update_client(c["id"], {"brief_agreed": True,
                                  "stage": "preapproved"},
                        now_str, "Converted - PRE-APPROVED LOAN")
        st.rerun()


def _credit(c, ctx, k):
    now_str = ctx["now_str"]
    st.markdown('<div class="tw-lab" style="margin:8px 0 6px">'
                'CREDIT TEAM CALL OUTCOME</div>',
                unsafe_allow_html=True)
    co = st.selectbox("outcome", D.CREDIT_OUTCOMES,
                      index=D.CREDIT_OUTCOMES.index(c.get("credit", ""))
                      if c.get("credit", "") in D.CREDIT_OUTCOMES else 0,
                      key=k + "co")
    if st.button("Apply credit outcome", type="primary", key=k + "coa"):
        if co == "PRE-APPROVED LOAN":
            D.update_client(c["id"], {"credit": co, "stage": "deposit"},
                            now_str, "Approved - deposit & delivery")
        elif co == "CASH OFFER - CREDIT":
            D.update_client(c["id"], {"credit": co,
                                      "stage": "cash_offer",
                                      "ended": True,
                                      "ended_date": ctx["today_iso"]},
                            now_str, "CASH OFFER - CREDIT - journey "
                            "ended")
        elif co == "PRE-APPROVED NOT ANSWERED":
            D.update_client(c["id"], {"credit": co,
                                      "stage": "pre_not_answered"},
                            now_str, co)
        elif co == "PRE-APPROVED NOT READY":
            D.update_client(c["id"], {"credit": co,
                                      "stage": "pre_not_ready"},
                            now_str, co)
        else:
            D.update_client(c["id"], {"credit": co}, now_str,
                            "Credit outcome logged")
        st.rerun()


def _delivery(c, ctx, k):
    today, now_str = ctx["today"], ctx["now_str"]
    st.markdown('<div class="tw-lab" style="margin:8px 0 6px">'
                'DEPOSIT &amp; DELIVERY / PICK-UP</div>',
                unsafe_allow_html=True)
    mode = st.selectbox("mode", D.DELIVERY_MODES,
                        index=D.DELIVERY_MODES.index(
                            c.get("delivery_mode", ""))
                        if c.get("delivery_mode", "") in D.DELIVERY_MODES
                        else 0, key=k + "mode")
    status = st.selectbox("delivery status", D.DELIVERY_STATUSES,
                          index=D.DELIVERY_STATUSES.index(
                              c.get("delivery_status", ""))
                          if c.get("delivery_status", "")
                          in D.DELIVERY_STATUSES else 0, key=k + "st")
    if status == "failed":
        freason = st.text_input("failure reason", key=k + "fr")
    if st.button("Save delivery", type="primary", key=k + "dv"):
        patch = {"delivery_mode": mode, "delivery_status": status}
        if status == "failed":
            patch["failed_reason"] = freason
            patch["stage"] = "failed_delivery"
        elif status == "delivered":
            patch["stage"] = "delivered"
            patch["delivered_date"] = today.isoformat()
        elif status in ("ready", "assigned", "out"):
            patch["stage"] = status
        D.update_client(c["id"], patch, now_str,
                        "Delivery: " + (status or mode or "updated"))
        st.rerun()
    if c.get("stage") in ("deposit", "ready", "assigned", "out",
                          "failed_delivery"):
        st.caption("Client can reschedule / switch delivery vs pick-up; "
                   "the system logs when and brings them back to calls.")
        rd = st.date_input("bring back to calls on", value=today,
                           key=k + "rd")
        if st.button("Reschedule to calls", key=k + "rs"):
            D.update_client(c["id"], {"next_date": rd.isoformat(),
                                      "next_action": "Delivery follow-up",
                                      "stage": "deposit"},
                            now_str, "Rescheduled to calls on "
                            + rd.isoformat())
            st.rerun()


def _outcomes(c, ctx, k):
    today, now_str = ctx["today"], ctx["now_str"]
    t1, t2, t3 = st.columns(3)
    with t1:
        if st.button("Mark PAID", key=k + "paid",
                     disabled=bool(c.get("paid"))):
            D.update_client(c["id"], {"paid": True,
                                      "paid_date": today.isoformat(),
                                      "stage": "paid"},
                            now_str, "Client PAID - deal closed")
            st.rerun()
    with t2:
        if st.button("Declined", key=k + "dec"):
            D.update_client(c["id"], {"stage": "declined"},
                            now_str, "Declined at delivery")
            st.rerun()
    with t3:
        if c.get("stage") == "delivered":
            ro = st.selectbox("return outcome",
                              ["RETURNED", "RETURNED & EXCHANGED"],
                              key=k + "ro")
            if st.button("Return", key=k + "ret"):
                D.update_client(c["id"], {"returned": True,
                                          "returned_date":
                                          today.isoformat(),
                                          "return_outcome": ro,
                                          "stage": "returned"
                                          if ro == "RETURNED"
                                          else "exchanged"},
                                now_str, ro)
                st.rerun()


def _journey_desk(ctx):
    clients = ctx["clients"]
    if not clients:
        st.caption("No clients yet - log a lead above.")
        return
    st.markdown('<div class="tw-lab" style="margin:4px 0 8px">'
                'CLIENT JOURNEY DESK</div>', unsafe_allow_html=True)
    names = [str(c.get("name", "?")) + "  ·  "
             + D.stage_label(c.get("stage", "new"), "?")
             for c in clients]
    sel = st.selectbox("client", range(len(clients)),
                       format_func=lambda i: names[i], key="jd_sel")
    c = clients[sel]
    stg = c.get("stage", "new")
    st.markdown(UI.badge(D.stage_label(stg, stg),
                         D.stage_color(stg)),
                unsafe_allow_html=True)
    kk = "jd" + c["id"]
    if c.get("ended"):
        if st.button("Reopen journey", key=kk + "re"):
            D.reopen_journey(c["id"], ctx["now_str"])
            st.rerun()
    if stg in ("new", "followup", "undecided"):
        _call_result(c, ctx, kk)
    elif stg == "agreed":
        _application(c, ctx, kk)
    elif stg == "prescreen":
        _prescreen(c, ctx, kk)
    elif stg == "docs":
        _docs(c, ctx, kk)
    elif stg == "briefing":
        _briefing(c, ctx, kk)
    elif stg in ("preapproved", "pre_not_answered", "pre_not_ready"):
        _credit(c, ctx, kk)
    elif stg in ("deposit", "ready", "assigned", "out",
                 "failed_delivery"):
        _delivery(c, ctx, kk)
    elif stg in ("delivered",):
        _outcomes(c, ctx, kk)


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
                "mute", "ink", "cash", "out", 80),
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
                                       key="cr" + i["id"])
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
                            D.move_money(pid,
                                         float(i.get("amount", 0)),
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
        st.markdown(UI.panel("By Source - since Aug 1",
                             UI.hbars(items),
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
