"""TrueWave - the full client journey, from the first ad-text to the
closed deal. Opens with a live Call Sheet so you always know who to
phone next. Every stage is timestamped; the memory of each client is
total, so you talk like you remember everything - because you do.
"""
from __future__ import annotations

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI


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


def _journey(c, ctx, k):
    today, now_str = ctx["today"], ctx["now_str"]
    st.markdown(UI.stepper_html(c), unsafe_allow_html=True)
    j1, j2 = st.columns([2, 1])
    with j1:
        cur_idx = D.STAGE_IDS.index(c["stage"]) \
            if c["stage"] in D.STAGE_IDS else 0
        ns = st.selectbox("Move to stage", D.STAGE_IDS,
                          format_func=lambda s: D.STAGE_LABEL[s],
                          index=cur_idx, key=k + "st")
    with j2:
        st.markdown("<div style='height:26px'></div>",
                    unsafe_allow_html=True)
        if st.button("Move stage", type="primary", key=k + "mv"):
            if ns != c["stage"]:
                D.set_stage(c["id"], ns, now_str)
                st.rerun()

    plan_opts = [""] + list(D.PLANS.keys())
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
        st.caption(D.PLANS[plan])

    q1, q2 = st.columns(2)
    with q1:
        qual = st.text_input("Qualified phones (M-Pesa review)",
                             value=c.get("qualified", ""),
                             key=k + "qf")
        dep = st.number_input("Deposit (KSh)", 0.0, 1000000.0,
                              float(c.get("deposit", 0) or 0),
                              step=500.0, key=k + "dp")
    with q2:
        wkly = st.number_input("Weekly (KSh)", 0.0, 100000.0,
                               float(c.get("weekly", 0) or 0),
                               step=100.0, key=k + "wk")
        na = st.text_input("Next action",
                           value=c.get("next_action", ""),
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
    st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                'DOCS &amp; VERIFICATION</div>',
                unsafe_allow_html=True)
    docs = dict(c.get("docs") or {})
    changed = False
    dcols = st.columns(3)
    for i, key_id in enumerate(D.DOC_ITEMS):
        curv = docs.get(key_id, "pending")
        with dcols[i]:
            v = st.selectbox(
                D.DOC_LABEL[key_id], D.DOC_STATES,
                index=D.DOC_STATES.index(curv)
                if curv in D.DOC_STATES else 0,
                key=k + "d" + key_id)
        if v != curv:
            docs[key_id] = v
            changed = True
    if changed:
        failed = [D.DOC_LABEL[i2] for i2 in D.DOC_ITEMS
                  if docs.get(i2) == "failed"]
        D.update_client(
            c["id"], {"docs": docs}, now_str,
            "Docs updated" + (" - FAILED: " + ", ".join(failed)
                              if failed else ""))
        st.rerun()

    cur_credit = c.get("credit", "pending")
    credit = st.selectbox(
        "Credit team outcome", D.CREDIT_OUTCOMES,
        index=D.CREDIT_OUTCOMES.index(cur_credit)
        if cur_credit in D.CREDIT_OUTCOMES else 0, key=k + "cr")
    if credit != cur_credit:
        patch = {"credit": credit}
        if credit == "CASH OFFER - CREDIT":
            patch["stage"] = "cash_offer"
        D.update_client(c["id"], patch, now_str,
                        "Credit -> " + credit)
        st.rerun()

    st.markdown('<div class="tw-lab" style="margin:14px 0 8px">'
                'DELIVERY &amp; RETURN WINDOW</div>',
                unsafe_allow_html=True)
    w = M.window_info(c, today)
    if c.get("delivered_date"):
        pairs = [("Delivered", c["delivered_date"])]
        if w:
            pairs.append(("Window closes", w["close"].isoformat()))
            pairs.append(("Window",
                          "CLOSED" if w["closed"]
                          else (str(w["left"]) + " days left")))
        if c.get("paid_date"):
            pairs.append(("Paid", c["paid_date"]))
        if c.get("returned_date"):
            pairs.append(("Returned", c["returned_date"]))
        st.markdown(UI.kv(pairs), unsafe_allow_html=True)
    e1, e2, e3 = st.columns(3)
    with e1:
        dd = st.date_input("delivered date", value=today, key=k + "dd")
        if st.button("Set delivered", key=k + "ds"):
            D.update_client(
                c["id"],
                {"delivered_date": dd.isoformat(),
                 "stage": "delivered"},
                now_str, "Phone delivered - 7-day return window OPEN")
            st.rerun()
    with e2:
        if st.button("Mark PAID", key=k + "pd",
                     disabled=bool(c.get("paid"))):
            D.update_client(
                c["id"],
                {"paid": True, "paid_date": today.isoformat(),
                 "stage": "paid"},
                now_str, "Client PAID - deal closed")
            st.rerun()
    with e3:
        window_open = bool(w) and not w["closed"]
        if st.button("Mark RETURNED", key=k + "rt",
                     disabled=bool(c.get("returned"))
                     or not window_open):
            D.update_client(
                c["id"],
                {"returned": True,
                 "returned_date": today.isoformat(),
                 "stage": "returned"},
                now_str, "Phone RETURNED inside the window")
            st.rerun()

    r1, r2 = st.columns(2)
    with r1:
        rem = st.text_input("Remark", value=c.get("remark", ""),
                            key=k + "rm")
    with r2:
        why = st.text_input("Why not today?",
                            value=c.get("why_not", ""), key=k + "wn")
    if st.button("Save remarks", key=k + "rs"):
        D.update_client(c["id"], {"remark": rem, "why_not": why},
                        now_str)
        st.rerun()


def _memory(c, ctx, k):
    now_str = ctx["now_str"]
    st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                'CLIENT MEMORY</div>', unsafe_allow_html=True)
    note = st.text_input(
        "Log a touch", key=k + "tn",
        placeholder="called - didn't pick / picked, said Friday...")
    if st.button("Log touch", type="primary",
                 key=k + "tb") and note.strip():
        D.touch_client(c["id"], note.strip(), now_str)
        st.rerun()
    st.markdown(UI.history_html(c.get("history", [])),
                unsafe_allow_html=True)


def _client_block(c, ctx):
    k = "c" + c["id"]
    label = (str(c.get("name", "?")) + "  ·  "
             + D.STAGE_LABEL.get(c.get("stage", "new"), "?") + "  ·  "
             + str(c.get("phone", "")))
    with st.expander(label):
        d1, d2, d3 = st.columns([5, 4, 3], gap="medium")
        with d1:
            _journey(c, ctx, k)
        with d2:
            _verify(c, ctx, k)
        with d3:
            _memory(c, ctx, k)


def render(ctx):
    clients, today = ctx["clients"], ctx["today"]
    cc = M.client_counts(clients, today)
    window = M.clients_in_window(clients, today)
    sheet = M.call_sheet(clients, today)

    row = [
        UI.tile("Call Sheet", str(len(sheet)), "phone them now",
                "win" if sheet else "mute",
                "win" if sheet else "ink", "phone", "win", 0),
        UI.tile("New This Week", str(cc["new7"]), "ads + live",
                "mute", "ink", "bolt", "accent", 40),
        UI.tile("Active Pipeline", str(cc["active"]), "in journey",
                "mute", "ink", "users", "accent", 80),
        UI.tile("Return Windows", str(len(window)), "7-day open",
                "mute", "ink", "cal", "jewel", 120),
        UI.tile("CASH OFFER Queue", str(cc["cashq"]), "credit refs",
                "mute", "ink", "cash", "jewel", 160),
        UI.tile("Paid & Closed", str(cc["sold"]), "since Aug 1",
                "win", "win", "check", "win", 200),
    ]
    st.markdown(UI.tiles_grid(row, 6), unsafe_allow_html=True)

    if sheet:
        st.markdown(UI.panel(
            "Today's Call Sheet - hottest first",
            "".join(UI.client_card(c, today) for c in sheet[:8]),
            right="tap a number to dial"), unsafe_allow_html=True)

    _add_lead(ctx)

    sc = M.stage_counts(clients)
    items = [(D.STAGE_LABEL[sid], sc.get(sid, 0), D.STAGE_COLOR[sid])
             for sid in D.STAGE_IDS if sc.get(sid, 0) > 0]
    st.markdown(UI.panel("Pipeline by Stage", UI.hbars(items),
                         right=str(len(clients)) + " total"),
                unsafe_allow_html=True)

    s1, s2 = st.columns([3, 2])
    with s1:
        q = st.text_input(
            "Search", key="cw_q",
            placeholder="name, number, model, remark, next action...")
    with s2:
        sf = st.selectbox("Stage filter", ["All stages"] + D.STAGE_IDS,
                          format_func=lambda s: "All stages"
                          if s == "All stages" else D.STAGE_LABEL[s],
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
                str(c.get("qualified", "")),
                str(c.get("why_not", "")),
            ]).lower()
            if ql not in hay:
                continue
        shown.append(c)
    shown.sort(key=lambda c: (
        1 if c.get("stage") in M.TERMINAL else 0,
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
