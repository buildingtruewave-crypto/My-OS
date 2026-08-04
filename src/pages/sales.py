"""Sales - the single data-entry point. Log leads (with location), log calls
with the exact follow-back date+time a client asks for, mark followed, move
stages, set plans / credit / delivery / returns / exchanges, hold reasons for
never-started clients, phone-issue logs, plus tally / sale / commissions /
income and the pipeline editor. TrueWave stays read-only.
"""
from __future__ import annotations

import csv
import datetime as dt
import html
import io

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U

_CALL_RESULTS = ["Reached - good talk", "Reached - callback asked",
                 "No answer", "Postponed", "Declined / cooling",
                 "Ended journey after call"]
_HOLD_REASONS = ["", "Cash offer given", "Under another partner",
                 "Name mismatch", "No details", "Needs name change",
                 "Not reached", "Not ready"]
_PRE_CREDIT = ["pending", "PRE-APPROVED LOAN",
               "PRE-APPROVED NOT REACHED / NOT READY",
               "CASH OFFER - CREDIT"]
_CREDIT = ["pending", "APPROVED - DEPOSIT & DELIVERY",
           "CASH OFFER - CREDIT", "PLAN CHANGE - HIGHER DEPOSIT",
           "PLAN CHANGE - SAVER PLAN", "DECLINED"]
_RETURNS = ["RETURNED", "RETURNED & EXCHANGED"]


def _pocket_options(vault):
    positions = vault.get("positions", [])
    names = ["— none —"] + [p["name"] for p in positions]
    ids = [""] + [p["id"] for p in positions]
    return names, ids


def _plan_options():
    return [""] + [p["label"] for p in D.get_plans()]


def _add_lead(ctx):
    with st.expander("+  Log a new lead (a client texted / called)"):
        a, b, c3 = st.columns(3)
        with a:
            name = st.text_input("Client name", key="cl_n")
            phone = st.text_input("Phone number", key="cl_p")
            source = st.selectbox("Source", D.SOURCES, key="cl_s")
        with b:
            loc = st.text_input("Location", key="cl_loc",
                                placeholder="e.g. Kasarani, Nairobi")
            want = st.text_input("Wants (phone / model)", key="cl_w")
            budget = st.text_input("Budget (KSh)", key="cl_b")
        with c3:
            heat = st.selectbox("Heat", D.HEATS, key="cl_h")
            note = st.text_input(
                "First note", key="cl_note",
                placeholder="texted from the ad, wants an iPhone...")
        if st.button("Add lead", type="primary",
                     key="cl_add") and name.strip():
            D.add_client(name.strip(), phone.strip(), source, heat,
                         want.strip(), budget.strip(), note.strip(),
                         ctx["today_iso"], ctx["now_str"])
            newc = st.session_state["clients"][0]
            if loc.strip():
                D.update_client(newc["id"], {"location": loc.strip()},
                                ctx["now_str"])
            st.rerun()


def _client_desk(ctx):
    clients = ctx["clients"]
    today, now_str = ctx["today"], ctx["now_str"]
    if not clients:
        st.caption("No clients yet - log a lead above.")
        return
    st.markdown('<div class="tw-lab" style="margin:4px 0 8px">'
                'CLIENT DESK - log calls / follow-backs / stages / '
                'verification</div>', unsafe_allow_html=True)
    names = [str(c.get("name", "?")) + "  ·  "
             + D.stage_label(c.get("stage", "new"), "?")
             for c in clients]
    sel = st.selectbox("client", range(len(clients)),
                       format_func=lambda i: names[i], key="cfg_sel")
    c = clients[sel]
    ids = D.all_stage_ids()

    st.markdown('<div class="tw-lab" style="margin:8px 0 6px">'
                'LOG A CALL / SCHEDULE FOLLOW-BACK</div>',
                unsafe_allow_html=True)
    r1, r2, r3 = st.columns([1.3, 1.2, 1.8])
    with r1:
        result = st.selectbox("call result", _CALL_RESULTS,
                              key="cfg_res")
    with r2:
        fb_on = st.checkbox("client wants a follow-back",
                            key="cfg_fbon")
        fb_date = st.date_input("follow-back date", value=today,
                                key="cfg_fbd")
    with r3:
        fb_time = st.time_input("follow-back time",
                                value=dt.time(14, 0), key="cfg_fbt")
        note = st.text_input("what was said", key="cfg_note")
    a1, a2 = st.columns([1, 4])
    with a1:
        if st.button("Log call", type="primary", key="cfg_log"):
            patch = {}
            if fb_on:
                fa = dt.datetime.combine(fb_date, fb_time)
                patch["follow_at"] = fa.isoformat(timespec="minutes")
                patch["follow_done"] = False
            else:
                patch["follow_at"] = ""
            if result == "Ended journey after call":
                D.update_client(c["id"], patch, now_str,
                                log_note=("Call logged - " + note.strip())
                                if note.strip() else
                                "Ended journey after call")
                D.end_journey if hasattr(D, "end_journey") else None
                c2 = next((x for x in st.session_state["clients"]
                           if x["id"] == c["id"]), None)
                if c2 is not None:
                    c2["ended"] = True
                    c2["ended_date"] = today.isoformat()
                    D.save_clients(st.session_state["clients"])
            else:
                D.update_client(c["id"], patch, now_str,
                                log_note=(result + (" - " + note.strip())
                                          if note.strip() else result))
            st.rerun()
    with a2:
        if c.get("follow_at") and not c.get("follow_done"):
            st.caption("Follow-back scheduled: "
                       + str(c["follow_at"]).replace("T", " · "))
            if st.button("Mark followed", key="cfg_done"):
                D.update_client(c["id"],
                                {"follow_done": True, "follow_at": ""},
                                now_str, log_note="Followed back")
                st.rerun()
        else:
            tnote = st.text_input("quick note (no reschedule)",
                                  key="cfg_tn")
            if st.button("Add note", key="cfg_tnb") and tnote.strip():
                D.touch_client(c["id"], tnote.strip(), now_str)
                st.rerun()

    if c.get("ended"):
        e1, e2 = st.columns([1.4, 2])
        with e1:
            rd = st.date_input("reschedule call to", value=today,
                               key="cfg_rd")
        with e2:
            st.markdown("<div style='height:26px'></div>",
                        unsafe_allow_html=True)
            if st.button("Reopen & reschedule (they reached out)",
                         type="primary", key="cfg_reopen"):
                c["ended"] = False
                c["ended_date"] = ""
                c["next_date"] = rd.isoformat()
                c["next_action"] = "Follow-up call"
                c.setdefault("history", []).append(
                    {"ts": now_str,
                     "note": "Reached out - reopened, call "
                     + rd.isoformat(),
                     "stage": c.get("stage", "")})
                D.save_clients(st.session_state["clients"])
                st.rerun()

    g1, g2 = st.columns(2, gap="medium")
    with g1:
        cur_idx = ids.index(c["stage"]) if c["stage"] in ids else 0
        ns = st.selectbox("Stage", ids, format_func=D.stage_label,
                          index=cur_idx, key="cfg_st")
        if st.button("Set stage", key="cfg_stgo"):
            if ns != c["stage"]:
                D.set_stage(c["id"], ns, now_str)
                st.rerun()
        plan_opts = _plan_options()
        cur_p = c.get("plan", "") or ""
        pi = plan_opts.index(cur_p) if cur_p in plan_opts else 0
        plan = st.radio("Payment plan", plan_opts, index=pi,
                        horizontal=True,
                        format_func=lambda p: p or "Not chosen",
                        key="cfg_pl")
        if plan != cur_p:
            D.update_client(c["id"], {"plan": plan}, now_str,
                            "Plan -> " + (plan or "none"))
            st.rerun()
        hold = st.selectbox(
            "Never started - reason (if applicable)", _HOLD_REASONS,
            index=_HOLD_REASONS.index(c.get("hold_reason", ""))
            if c.get("hold_reason", "") in _HOLD_REASONS else 0,
            key="cfg_hold")
        if hold != (c.get("hold_reason") or ""):
            D.update_client(c["id"], {"hold_reason": hold}, now_str,
                            "Hold reason -> " + (hold or "none"))
            st.rerun()
        q1, q2 = st.columns(2)
        with q1:
            dep = st.number_input("Deposit (KSh)", 0.0, 1000000.0,
                                  float(c.get("deposit", 0) or 0),
                                  step=500.0, key="cfg_dp")
        with q2:
            wkly = st.number_input("Weekly (KSh)", 0.0, 1000000.0,
                                   float(c.get("weekly", 0) or 0),
                                   step=100.0, key="cfg_wk")
        if st.button("Save numbers", key="cfg_sv"):
            D.update_client(c["id"], {"deposit": float(dep),
                                      "weekly": float(wkly)},
                            now_str, "Numbers updated")
            st.rerun()
    with g2:
        pc = st.selectbox("Pre-approval (before credit call)",
                          _PRE_CREDIT,
                          index=_PRE_CREDIT.index(
                              c.get("pre_credit", "pending"))
                          if c.get("pre_credit", "pending")
                          in _PRE_CREDIT else 0, key="cfg_pc")
        cr = st.selectbox("Credit outcome (after credit call)", _CREDIT,
                          index=_CREDIT.index(c.get("credit", "pending"))
                          if c.get("credit", "pending") in _CREDIT
                          else 0, key="cfg_cr")
        if st.button("Save credit", key="cfg_cs"):
            patch = {"pre_credit": pc, "credit": cr}
            if cr == "PLAN CHANGE - SAVER PLAN":
                saver = next((p["label"] for p in D.get_plans()
                              if p["id"] == "saver"), "")
                if saver:
                    patch["plan"] = saver
            if cr == "CASH OFFER - CREDIT":
                cand = D.role_id("cash")
                if cand:
                    patch["stage"] = cand
            D.update_client(c["id"], patch, now_str,
                            "Credit -> " + cr)
            st.rerun()
        b1, b2, b3 = st.columns(3)
        dr = D.role_id("delivered")
        wr = D.role_id("won")
        rr = D.role_id("returned")
        with b1:
            dd = st.date_input("delivered", value=today, key="cfg_dd")
            if st.button("Set delivered", key="cfg_ds",
                         disabled=dr is None):
                D.update_client(c["id"],
                                {"delivered_date": dd.isoformat(),
                                 "stage": dr}, now_str,
                                "Delivered - window OPEN")
                st.rerun()
        with b2:
            if st.button("Mark PAID", key="cfg_pd",
                         disabled=(wr is None)
                         or bool(c.get("paid"))):
                D.update_client(c["id"],
                                {"paid": True,
                                 "paid_date": today.isoformat(),
                                 "stage": wr}, now_str,
                                "Client PAID - deal closed")
                st.rerun()
        with b3:
            w = M.window_info(c, today)
            open_w = bool(w) and not w["closed"]
            ro = st.selectbox("return outcome", _RETURNS, key="cfg_ro")
            if st.button("Mark returned", key="cfg_rt",
                         disabled=(rr is None)
                         or bool(c.get("returned")) or not open_w):
                D.update_client(c["id"],
                                {"returned": True,
                                 "returned_date": today.isoformat(),
                                 "return_outcome": ro,
                                 "stage": "exchanged"
                                 if ro == "RETURNED & EXCHANGED"
                                 else rr}, now_str,
                                "Outcome: " + ro)
                st.rerun()

    st.markdown('<div class="tw-lab" style="margin:10px 0 6px">'
                'PHONE ISSUE LOG</div>', unsafe_allow_html=True)
    p1, p2, p3, p4 = st.columns([1.4, 1.2, 1.4, 0.8])
    with p1:
        issue = st.text_input("issue", key="cfg_pi",
                              placeholder="e.g. screen faulty")
    with p2:
        action = st.text_input("action", key="cfg_pa",
                               placeholder="repair / exchange")
    with p3:
        pnote = st.text_input("details", key="cfg_pn")
    with p4:
        st.markdown("<div style='height:26px'></div>",
                    unsafe_allow_html=True)
        if st.button("Add", key="cfg_padd") and issue.strip():
            c.setdefault("service", []).append(
                {"ts": now_str, "issue": issue.strip(),
                 "action": action.strip(), "note": pnote.strip()})
            c.setdefault("history", []).append(
                {"ts": now_str, "note": "Phone issue: " + issue.strip(),
                 "stage": c.get("stage", "")})
            D.save_clients(st.session_state["clients"])
            st.rerun()


def _pipeline_editor():
    obj = D.get_pipeline_obj()
    stages = list(obj.get("stages", []))
    plans = list(obj.get("plans", []))
    counts = M.stage_counts(st.session_state["clients"])
    with st.expander("⚙  Configure my conversion pipeline & plans"):
        st.caption("Rename, recolor, reorder or add stages; tag the "
                   "roles the engine needs (won / lost / cash / "
                   "delivered / returned). Edit plans too.")
        for i, s in enumerate(stages):
            cnt = counts.get(s["id"], 0)
            c1, c2, c3, c4, c5, c6 = st.columns(
                [2.6, 1.3, 1.5, 0.6, 0.6, 0.6])
            with c1:
                st.markdown(
                    '<div style="padding-top:8px;font:600 13px '
                    'var(--body);color:var(--ink-2)">'
                    + html.escape(s.get("label", "?")) + '</div>',
                    unsafe_allow_html=True)
            with c2:
                st.markdown(
                    '<div style="padding-top:8px">'
                    + UI.badge(D.ROLE_LABEL.get(s.get("role", ""), "—"),
                               s.get("color", "#7C8AA5")) + '</div>',
                    unsafe_allow_html=True)
            with c3:
                st.markdown(
                    '<div style="padding-top:8px" class="tw-sub">'
                    + ("on path" if s.get("track") else "branch")
                    + " · " + str(cnt) + " here</div>",
                    unsafe_allow_html=True)
            with c4:
                if st.button("▲", key="pu" + s["id"], disabled=i == 0):
                    stages[i - 1], stages[i] = stages[i], stages[i - 1]
                    obj["stages"] = stages
                    D.save_pipeline_obj(obj)
                    st.rerun()
            with c5:
                if st.button("▼", key="pd" + s["id"],
                             disabled=i == len(stages) - 1):
                    stages[i + 1], stages[i] = stages[i], stages[i + 1]
                    obj["stages"] = stages
                    D.save_pipeline_obj(obj)
                    st.rerun()
            with c6:
                if st.button("✕", key="px" + s["id"],
                             disabled=cnt > 0 or len(stages) <= 1):
                    stages.pop(i)
                    obj["stages"] = stages
                    D.save_pipeline_obj(obj)
                    st.rerun()
        with st.form("pf"):
            new_labels, new_colors, new_tracks, new_roles = {}, {}, {}, {}
            for s in stages:
                r1, r2, r3, r4 = st.columns([2.4, 1.2, 1.2, 1.8])
                cur_role = s.get("role", "")
                role_idx = D.ROLES.index(cur_role) \
                    if cur_role in D.ROLES else 0
                with r1:
                    new_labels[s["id"]] = st.text_input(
                        "label", value=s.get("label", ""),
                        key="fl_" + s["id"])
                with r2:
                    new_colors[s["id"]] = st.color_picker(
                        "color", value=s.get("color", "#7C8AA5"),
                        key="fc_" + s["id"])
                with r3:
                    new_tracks[s["id"]] = st.checkbox(
                        "on path", value=bool(s.get("track")),
                        key="ft_" + s["id"])
                with r4:
                    new_roles[s["id"]] = st.selectbox(
                        "role", D.ROLES, index=role_idx,
                        format_func=lambda r: D.ROLE_LABEL.get(r, r),
                        key="fr_" + s["id"])
            submitted = st.form_submit_button("Save labels / roles")
            if submitted:
                seen, dup = {}, None
                for sid, role in new_roles.items():
                    if role:
                        if role in seen:
                            dup = role
                            break
                        seen[role] = sid
                if dup:
                    st.error("Role '" + D.ROLE_LABEL.get(dup, dup)
                             + "' is on two stages.")
                else:
                    for s in stages:
                        lab = new_labels[s["id"]].strip()
                        s["label"] = lab or s["label"]
                        s["color"] = new_colors[s["id"]]
                        s["track"] = bool(new_tracks[s["id"]])
                        s["role"] = new_roles[s["id"]]
                    obj["stages"] = stages
                    D.save_pipeline_obj(obj)
                    st.success("Pipeline saved.")
                    st.rerun()


def render(ctx):
    daily, sales = ctx["sales_daily"], ctx["sales"]
    income = ctx["income"]
    vault = ctx["vault"]
    today, t_iso = ctx["today"], ctx["today_iso"]
    now_time = ctx["now_dt"].strftime("%H:%M")
    pnames, pids = _pocket_options(vault)

    _add_lead(ctx)
    _client_desk(ctx)
    _pipeline_editor()

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
            '<div style="height:2px"></div>'),
            unsafe_allow_html=True)
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
