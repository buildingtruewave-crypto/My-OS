"""TrueWave - the full client journey, wired to the Connection Engine.
The ACTIVE PIPELINE holds only in-progress clients. The CASH-OFFER QUEUE is a
separate bucket of rejected clients that a journey-end never empties. Every
client on the Call Sheet and in the Cash-Offer Queue has a one-tap "Called"
tick that logs the touch and auto-reschedules the next call.
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

_RESCHEDULE = [("tomorrow", 1), ("in 2 days", 2), ("in 3 days", 3),
               ("next week", 7)]


def _plan_options():
    return [""] + [p["label"] for p in D.get_plans()]


def _called_controls(c, ctx, key):
    """One-tap 'Called' tick: logs the touch and auto-reschedules."""
    today, now_str = ctx["today"], ctx["now_str"]
    labels = [r[0] for r in _RESCHEDULE]
    days = dict(_RESCHEDULE)
    st.markdown('<div class="tw-lab" style="margin:2px 0 6px">'
                'MARK CALLED</div>', unsafe_allow_html=True)
    choice = st.selectbox("next call", labels, key=key + "rs")
    if st.button("Called ✓", type="primary", key=key + "cb"):
        nd = (today + dt.timedelta(days=days[choice])).isoformat()
        D.mark_called(c["id"], now_str, nd)
        st.rerun()
    st.caption("Logs the touch & moves them off today's sheet.")


def _call_sheet_row(c, ctx, key):
    c1, c2 = st.columns([4, 1.6], gap="medium")
    with c1:
        st.markdown(UI.client_card(c, ctx["today"]),
                    unsafe_allow_html=True)
    with c2:
        _called_controls(c, ctx, key)


def _add_lead(ctx):
    with st.expander("+  Log a new lead"):
        a, b, c3 = st.columns(3)
        with a:
            name = st.text_input("Client name", key="cl_n")
            phone = st.text_input("Phone number", key="cl_p")
            source = st.selectbox("Source", D.SOURCES, key="cl_s")
        with b:
            want = st.text_input("Wants (phone / model)", key="cl_w")
            budget = st.text_input("Budget (KSh)", key="cl_b")
            heat = st.selectbox("Heat", D.HEATS, key="cl_h")
        with c3:
            note = st.text_input(
                "First note", key="cl_note",
                placeholder="texted from the ad, wants an iPhone...")
        if st.button("Add lead", type="primary",
                     key="cl_add") and name.strip():
            D.add_client(name.strip(), phone.strip(), source, heat,
                         want.strip(), budget.strip(), note.strip(),
                         ctx["today_iso"], ctx["now_str"])
            st.rerun()


def _bulk_import(ctx):
    with st.expander("⤓  Bulk import clients from CSV"):
        st.caption(
            "Drop a CSV with headers: name, phone, source, want, budget, "
            "heat, note (missing columns are fine). Every row enters at the "
            "first stage with a 'bulk CSV import' note.")
        up = st.file_uploader("CSV file", type=["csv"], key="ci_csv")
        if up is not None:
            if st.button("Import rows", type="primary", key="ci_go"):
                txt = up.getvalue().decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(txt))
                n = 0
                for r in reader:
                    nm = (r.get("name") or "").strip()
                    if not nm:
                        continue
                    D.add_client(
                        nm, (r.get("phone") or "").strip(),
                        (r.get("source") or "Walk-in").strip(),
                        (r.get("heat") or "Warm").strip(),
                        (r.get("want") or "").strip(),
                        (r.get("budget") or "").strip(),
                        (r.get("note") or "bulk CSV import").strip(),
                        ctx["today_iso"], ctx["now_str"])
                    n += 1
                st.success("Imported " + str(n) + " clients.")
                st.rerun()


def _journey(c, ctx, k):
    today, now_str = ctx["today"], ctx["now_str"]
    ids = D.all_stage_ids()
    st.markdown(UI.stepper_html(c), unsafe_allow_html=True)

    if c.get("ended"):
        st.markdown(
            '<div style="display:flex;align-items:center;gap:8px;'
            'flex-wrap:wrap;margin:-4px 0 10px">'
            + UI.badge("JOURNEY ENDED", "#7C8AA5")
            + '<span class="tw-sub">out of the pipeline'
            + (("  ·  " + html.escape(str(c.get("ended_date", ""))))
               if c.get("ended_date") else "") + '</span></div>',
            unsafe_allow_html=True)
        if st.button("Reopen journey", key=k + "rj"):
            D.reopen_journey(c["id"], now_str)
            st.rerun()
    else:
        ec1, ec2 = st.columns([0.8, 3.2])
        with ec1:
            sure = st.checkbox("sure?", key=k + "ejc")
        with ec2:
            if st.button("Journey ended - out of pipeline",
                         key=k + "ej", disabled=not sure):
                D.end_journey(c["id"], now_str)
                st.rerun()
        if D.is_cash_offer(c):
            st.caption("This client is a cash-offer (rejected) client. "
                       "Ending the journey removes them from the active "
                       "pipeline but they stay in the Cash-Offer Queue. "
                       "To clear them fully, mark them Paid or Lost.")

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
        wkly = st.number_input("Weekly (KSh)", 0.0, 100000.0,
                               float(c.get("weekly", 0) or 0),
                               step=100.0, key=k + "wk")
        na = st.text_input("Next action", value=c.get("next_action", ""),
                           key=k + "na")
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
                        "Docs updated" + (" - FAILED: " + ", ".join(failed)
                                          if failed else ""))
        st.rerun()
    cur_credit = c.get("credit", "pending")
    credit = st.selectbox("Credit team outcome", D.CREDIT_OUTCOMES,
                          index=D.CREDIT_OUTCOMES.index(cur_credit)
                          if cur_credit in D.CREDIT_OUTCOMES else 0,
                          key=k + "cr")
    default_stage = c.get("stage", "")
    if credit == D.CASH_CREDIT:
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
    if D.is_cash_offer(c):
        st.markdown('<div style="margin:10px 0;padding:9px 12px;'
                    'border-radius:10px;background:rgba(245,181,68,.1);'
                    'border:1px solid rgba(245,181,68,.3);font:600 12px '
                    'var(--body);color:#F5B544">'
                    + '⚡ Rejected to cash - sitting in the Cash-Offer '
                      'Queue with a follow-up task.</div>',
                    unsafe_allow_html=True)
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
                            {"delivered_date": dd.isoformat(), "stage": dr},
                            now_str, "Delivered - 7-day return window OPEN")
            st.rerun()
        if dr is None:
            st.caption("tag a stage 'delivered'")
    with e2:
        if st.button("Mark PAID", key=k + "pd",
                     disabled=(wr is None) or bool(c.get("paid"))):
            D.update_client(c["id"],
                            {"paid": True, "paid_date": today.isoformat(),
                             "stage": wr},
                            now_str, "Client PAID - deal closed")
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
                             "stage": rr},
                            now_str, "Phone RETURNED inside the window")
            st.rerun()
        if rr is None:
            st.caption("tag a stage 'returned'")
    r1, r2 = st.columns(2)
    with r1:
        rem = st.text_input("Remark", value=c.get("remark", ""),
                            key=k + "rm")
    with r2:
        why = st.text_input("Why not today?", value=c.get("why_not", ""),
                            key=k + "wn")
    if st.button("Save remarks", key=k + "rs2"):
        D.update_client(c["id"], {"remark": rem, "why_not": why}, now_str)
        st.rerun()


def _memory(c, ctx, k):
    now_str = ctx["now_str"]
    st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                'CLIENT MEMORY</div>', unsafe_allow_html=True)
    note = st.text_input("Log a touch", key=k + "tn",
                         placeholder="called - didn't pick / picked, said Friday...")
    if st.button("Log touch", type="primary", key=k + "tb") and note.strip():
        D.touch_client(c["id"], note.strip(), now_str)
        st.rerun()
    st.markdown(UI.history_html(c.get("history", [])),
                unsafe_allow_html=True)


def _client_block(c, ctx):
    k = "c" + c["id"]
    ended_bit = "  ·  ENDED" if c.get("ended") else ""
    cash_bit = "  ·  CASH-OFFER" if D.is_cash_offer(c) else ""
    label = (str(c.get("name", "?")) + "  ·  "
             + D.stage_label(c.get("stage", "new"), "?") + ended_bit
             + cash_bit + "  ·  " + str(c.get("phone", "")))
    with st.expander(label):
        d1, d2, d3 = st.columns([5, 4, 3], gap="medium")
        with d1:
            _journey(c, ctx, k)
        with d2:
            _verify(c, ctx, k)
        with d3:
            _memory(c, ctx, k)


def _pipeline_editor():
    obj = D.get_pipeline_obj()
    stages = list(obj.get("stages", []))
    plans = list(obj.get("plans", []))
    counts = M.stage_counts(st.session_state["clients"])
    with st.expander("⚙  Configure my conversion pipeline & plans"):
        st.caption(
            "Change businesses without touching code. Rename, recolor, "
            "reorder or add stages; mark which sit on the linear path; tag "
            "the five roles the engine needs (won / lost / cash / delivered / "
            "returned) - one stage each. The dashboard, call sheet, search, "
            "funnel and the Cash-Offer Queue all follow.")
        st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                    'STAGES - IN ORDER</div>', unsafe_allow_html=True)
        for i, s in enumerate(stages):
            cnt = counts.get(s["id"], 0)
            c1, c2, c3, c4, c5, c6 = st.columns([2.6, 1.3, 1.5, 0.6, 0.6, 0.6])
            with c1:
                st.markdown(
                    '<div style="padding-top:8px;font:600 13px var(--body);'
                    'color:var(--ink-2)">'
                    + html.escape(s.get("label", "?")) + '</div>',
                    unsafe_allow_html=True)
            with c2:
                st.markdown('<div style="padding-top:8px">'
                            + UI.badge(D.ROLE_LABEL.get(s.get("role", ""), "—"),
                                       s.get("color", "#7C8AA5")) + '</div>',
                            unsafe_allow_html=True)
            with c3:
                st.markdown('<div style="padding-top:8px" class="tw-sub">'
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
        a1, a2, a3 = st.columns([3, 1.4, 1])
        with a1:
            nl = st.text_input("new stage label", key="ns_l")
        with a2:
            nc = st.color_picker("color", value="#4C8DFF", key="ns_c")
        with a3:
            st.markdown("<div style='height:26px'></div>",
                        unsafe_allow_html=True)
            if st.button("Add stage", key="ns_add") and nl.strip():
                nid = U.slug(nl)
                base = nid
                kk = 2
                while any(x["id"] == nid for x in stages):
                    nid = base + str(kk)
                    kk += 1
                stages.append({"id": nid, "label": nl.strip(), "color": nc,
                               "track": False, "role": ""})
                obj["stages"] = stages
                D.save_pipeline_obj(obj)
                st.rerun()
        with st.form("pf"):
            st.markdown('<div class="tw-lab" style="margin:8px 0 8px">'
                        'EDIT LABELS / COLOR / PATH / ROLE</div>',
                        unsafe_allow_html=True)
            new_labels, new_colors, new_tracks, new_roles = {}, {}, {}, {}
            for s in stages:
                r1, r2, r3, r4 = st.columns([2.4, 1.2, 1.2, 1.8])
                cur_role = s.get("role", "")
                role_idx = D.ROLES.index(cur_role) if cur_role in D.ROLES else 0
                with r1:
                    new_labels[s["id"]] = st.text_input(
                        "label", value=s.get("label", ""), key="fl_" + s["id"])
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
            st.markdown('<div class="tw-lab" style="margin:12px 0 8px">'
                        'PAYMENT PLANS</div>', unsafe_allow_html=True)
            plan_labels, plan_notes = {}, {}
            for p in plans:
                q1, q2 = st.columns([2, 3])
                with q1:
                    plan_labels[p["id"]] = st.text_input(
                        "plan", value=p.get("label", ""), key="pl_" + p["id"])
                with q2:
                    plan_notes[p["id"]] = st.text_input(
                        "note", value=p.get("note", ""), key="pn_" + p["id"])
            na2, nb2 = st.columns([3, 2])
            with na2:
                new_plan = st.text_input("new plan label", key="np_l")
            with nb2:
                new_plan_note = st.text_input("new plan note", key="np_n")
            submitted = st.form_submit_button("Save labels / roles / plans")
            add_plan = st.form_submit_button("Add plan")
            if add_plan and new_plan.strip():
                pid = U.slug(new_plan)
                base = pid
                kk = 2
                while any(x["id"] == pid for x in plans):
                    pid = base + str(kk)
                    kk += 1
                plans.append({"id": pid, "label": new_plan.strip(),
                              "note": new_plan_note.strip()})
                obj["plans"] = plans
                D.save_pipeline_obj(obj)
                st.rerun()
            if submitted:
                seen = {}
                dup = None
                for sid, role in new_roles.items():
                    if role:
                        if role in seen:
                            dup = role
                            break
                        seen[role] = sid
                if dup:
                    st.error("Role '" + D.ROLE_LABEL.get(dup, dup)
                             + "' is on two stages - each role belongs to one "
                               "stage only.")
                else:
                    for s in stages:
                        lab = new_labels[s["id"]].strip()
                        s["label"] = lab or s["label"]
                        s["color"] = new_colors[s["id"]]
                        s["track"] = bool(new_tracks[s["id"]])
                        s["role"] = new_roles[s["id"]]
                    for p in plans:
                        lab = plan_labels[p["id"]].strip()
                        p["label"] = lab or p["label"]
                        p["note"] = plan_notes[p["id"]]
                    obj["stages"] = stages
                    obj["plans"] = plans
                    D.save_pipeline_obj(obj)
                    st.success("Pipeline saved.")
                    st.rerun()
        if st.button("Reset to phone-sales default", key="pf_reset"):
            D.save_pipeline_obj(D._seed_pipeline())
            st.rerun()


def _outcome_text(c):
    if c.get("ended"):
        ed = c.get("ended_date", "")
        return "ENDED" + (("  ·  " + str(ed)) if ed else "")
    term = D.terminal_ids()
    stg = c.get("stage", "new")
    if stg not in term:
        return "—"
    odate = (c.get("paid_date") or c.get("returned_date")
             or c.get("created", ""))
    return D.stage_label(stg, stg) + (("  " + str(odate)) if odate else "")


def _cash_offer_panel(clients, ctx):
    cq = M.cash_queue(clients)
    st.markdown('<div class="tw-lab" style="margin:14px 0 8px">'
                'CASH-OFFER QUEUE - REJECTED TO CASH</div>',
                unsafe_allow_html=True)
    if not cq:
        st.markdown(UI.panel(
            "Cash-Offer Queue",
            UI.empty_state(
                "When a client's credit outcome is CASH OFFER - CREDIT, they "
                "load here automatically. This is a holding queue of rejected "
                "clients, separate from the active pipeline."),
            right="auto-aligned"), unsafe_allow_html=True)
        return
    st.caption("These clients were declined for financing and offered cash. "
               "They stay here until marked Paid or Lost - ending a journey "
               "does not remove them. Tick Called to log and reschedule.")
    for c in cq:
        _call_sheet_row(c, ctx, "cq" + c["id"])


def render(ctx):
    clients, today = ctx["clients"], ctx["today"]
    cc = M.client_counts(clients, today)
    window = M.clients_in_window(clients, today)
    sheet = M.call_sheet(clients, today)
    row = [
        UI.tile("Call Sheet", str(len(sheet)), "in-progress, due today",
                "win" if sheet else "mute",
                "win" if sheet else "ink", "phone", "win", 0),
        UI.tile("New This Week", str(cc["new7"]), "ads + live",
                "mute", "ink", "bolt", "accent", 40),
        UI.tile("Active Pipeline", str(cc["active"]), "in-progress only",
                "mute", "ink", "users", "accent", 80),
        UI.tile("Return Windows", str(len(window)), "7-day open",
                "mute", "ink", "cal", "jewel", 120),
        UI.tile("Cash-Offer Queue", str(cc["cashq"]), "rejected → cash",
                "win" if cc["cashq"] else "mute",
                "win" if cc["cashq"] else "ink", "cash", "jewel", 160),
        UI.tile("Paid & Closed", str(cc["sold"]), "since Aug 1",
                "win", "win", "check", "win", 200),
    ]
    st.markdown(UI.tiles_grid(row, 6), unsafe_allow_html=True)

    if sheet:
        st.markdown('<div class="tw-lab" style="margin:14px 0 8px">'
                    "TODAY'S CALL SHEET - IN-PROGRESS - HOTTEST FIRST</div>",
                    unsafe_allow_html=True)
        st.caption("Tick Called to log the touch and auto-reschedule the "
                   "next call - they drop off this list instantly.")
        for c in sheet[:8]:
            _call_sheet_row(c, ctx, "cs" + c["id"])

    _cash_offer_panel(clients, ctx)
    _add_lead(ctx)
    _bulk_import(ctx)
    _pipeline_editor()

    sc = M.stage_counts(clients)
    items = [(D.stage_label(sid, sid), sc.get(sid, 0),
              D.stage_color(sid)) for sid in D.all_stage_ids()
             if sc.get(sid, 0) > 0]
    st.markdown(UI.panel("Pipeline by Stage", UI.hbars(items),
                         right=str(len(clients)) + " total"),
                unsafe_allow_html=True)
    s1, s2 = st.columns([3, 2])
    with s1:
        q = st.text_input("Search", key="cw_q",
                          placeholder="name, number, model, remark, next action...")
    with s2:
        sf = st.selectbox("Stage filter",
                          ["All stages"] + D.all_stage_ids(),
                          format_func=lambda s: "All stages"
                          if s == "All stages" else D.stage_label(s, s),
                          key="cw_s")
    ql = q.strip().lower()
    shown = []
    for c in clients:
        if sf != "All stages" and c.get("stage") != sf:
            continue
        if ql:
            hay = " ".join([
                str(c.get("name", "")), str(c.get("phone", "")),
                str(c.get("want", "")), str(c.get("remark", "")),
                str(c.get("next_action", "")),
                str(c.get("qualified", "")), str(c.get("why_not", "")),
            ]).lower()
            if ql not in hay:
                continue
        shown.append(c)
    term = M.terminal_ids()
    shown.sort(key=lambda c: (
        1 if (c.get("stage") in term or c.get("ended")) else 0,
        c.get("next_date") or c.get("created") or "9999"))
    if not shown:
        st.markdown(UI.panel("Clients", UI.empty_state(
            "No clients match - log your first lead above.")),
            unsafe_allow_html=True)
    if len(shown) > 60:
        st.caption("Showing the 60 most urgent of " + str(len(shown))
                   + " - narrow with search or the stage filter.")
    for c in shown[:60]:
        _client_block(c, ctx)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    rows = []
    for c in clients:
        st_chip = {"open": ("OPEN", "#4C8DFF"),
                   "won": ("WON", "#34D399"),
                   "lost": ("LOST", "#7C8AA5"),
                   "returned": ("RETURNED", "#F0556B"),
                   "cash": ("CASH", "#F5B544")}.get(
                       D.stage_role(c.get("stage", "")),
                       ("LIVE", D.stage_color(c.get("stage", ""))))
        if c.get("ended"):
            st_chip = ("ENDED", "#7C8AA5")
        rows.append([
            (c.get("created", ""), "num"),
            (str(c.get("name", "")), ""),
            (str(c.get("phone", "")), "num"),
            (str(c.get("want", "")), ""),
            (str(c.get("source", "")), ""),
            (c.get("next_date", "") or "--", "num"),
            (UI.badge(st_chip[0], st_chip[1]), ""),
            (_outcome_text(c), "num"),
        ])
    st.markdown(UI.panel("All inquiries",
                         UI.table(["Logged", "Name", "Phone", "Wants",
                                   "Source", "Next", "Status", "Outcome"],
                                  rows)),
                unsafe_allow_html=True)
