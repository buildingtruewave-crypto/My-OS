"""The hidden money + security operating system - the ONLY place balances,
pantry, runway and the emergency ring-fence live, behind ARCHIVE_PIN. ONE
writer (move_money) moves real cash. Pantry stock, monthly burn and the
emergency ring-fence are CONFIG / SNAPSHOTS the operator sets by hand - the
system never auto-deducts food or money; it only divides and ages the read.
M-Pesa pockets brand their references green.
"""
from __future__ import annotations

import html

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U

HOURS = [str(i).zfill(2) for i in range(24)]
MINS = [str(i).zfill(2) for i in range(60)]


def _gate():
    st.markdown(UI.panel("Archive", UI.empty_state(
        "Nothing archived on this device.")),
        unsafe_allow_html=True)
    with st.expander("· · ·"):
        pin = st.text_input("code", type="password", key="v_pin",
                            label_visibility="collapsed",
                            placeholder="····")
        if st.button("Open", key="v_open"):
            if pin == D.ARCHIVE_PIN:
                st.session_state["vault_ok"] = True
                st.rerun()
            else:
                st.caption("Nothing here.")


def _pid2name(vault):
    out = {}
    for p in vault.get("positions", []):
        out[p["id"]] = p["name"]
    return out


def _sec_row2(vault, today):
    pan = vault.get("pantry", {})
    bn = M.pantry_bottleneck(pan, today)
    if bn is None:
        food_v, food_d, food_t = "—", "no staples set", "mute"
    else:
        aged = bn[0]
        food_v = format(aged, ".0f") + "d"
        food_d = "bottleneck: " + str(bn[2])
        food_t = ("win" if aged >= 14 else
                  ("accent" if aged >= 7 else
                   ("loss" if aged < 3 else "mute")))
    rm = M.runway_months(vault)
    if rm is None:
        run_v, run_d, run_t = "—", "set monthly burn", "mute"
    else:
        run_v = format(rm, ".1f") + "mo"
        run_d = "cash runway"
        run_t = "win" if rm >= 3 else ("accent" if rm >= 1 else "loss")
    ep = M.emergency_progress(vault)
    em_v = format(ep, ".0f") + "%"
    em_d = ("of " + str(int(vault.get("runway", {}).get(
        "emergency_months", 3))) + "-mo target")
    em_t = "win" if ep >= 100 else ("accent" if ep >= 50 else "mute")
    return [
        UI.tile("Food Security", food_v, food_d, food_t, food_t,
                "grid", "win", 0),
        UI.tile("Cash Runway", run_v, run_d, run_t, run_t,
                "clock", "accent", 40),
        UI.tile("Emergency Fund", em_v, em_d, em_t, em_t,
                "lock", "jewel", 80),
    ]


def _overview(ctx):
    vault, today = ctx["vault"], ctx["today"]
    net = M.net_worth(vault)
    cash = M.cash_on_hand(vault)
    alloc = M.allocated(vault)
    wk_in, wk_out = M.flow_week_inout(vault.get("flow", []), today)
    bills_due = M.bills_due_soon(vault, today)
    bills_late = M.bills_overdue(vault, today)

    row = [
        UI.tile("Net Worth", U.fmt_kes(net), "cash in your pockets",
                "mute", "ink", "star", "jewel", 0),
        UI.tile("Cash On Hand", U.fmt_kes(cash), "wallet + M-Pesa + bank",
                "mute", "ink", "cash", "accent", 40),
        UI.tile("Set Aside", U.fmt_kes(alloc),
                "partitioned (bills/fun/lists/ventures/emergency)",
                "mute", "ink", "target", "win", 80),
        UI.tile("Money In - 7d", U.fmt_kes(wk_in, True), "flow",
                "win" if wk_in else "mute", "win", "trend", "win", 120),
        UI.tile("Money Out - 7d", U.fmt_kes(wk_out), "flow",
                "loss" if wk_out else "mute", "loss", "bolt", "loss",
                160),
    ]
    st.markdown(UI.tiles_grid(row, 5), unsafe_allow_html=True)

    series = M.snapshots_series(vault)
    if len(series) >= 2:
        body = UI.equity_svg(series, "nw_eq", kind="num",
                             xfmt=lambda d: d.strftime("%d %b"))
        right = "real cash, every day"
    else:
        body = UI.empty_state(
            "The climb draws itself from your first money move.")
        right = "net worth"
    st.markdown(UI.panel("Net Worth - The Climb", body, right=right),
                unsafe_allow_html=True)

    st.markdown(UI.tiles_grid(_sec_row2(vault, today), 3),
                unsafe_allow_html=True)

    if bills_late or bills_due:
        pairs = []
        for b in bills_late:
            pairs.append((b["name"] + " - OVERDUE " + b["due"],
                          '<span class="tw-loss">'
                          + U.fmt_kes(float(b["need"]))
                          + " needed</span>"))
        for b in bills_due:
            pairs.append((b["name"] + " - due " + b["due"],
                          U.fmt_kes(float(b["need"])) + " needed"))
        st.markdown(UI.panel("Bills That Need You", UI.kv(pairs),
                             right="don't get caught"),
                    unsafe_allow_html=True)


def _tab_cash(vault):
    st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                'WHERE THE CASH LIVES - READ ONLY. EVERY MOVE IS A '
                'REAL, TIMED ENTRY ON THE DAILY FLOW TAB</div>',
                unsafe_allow_html=True)
    cols = st.columns(max(len(vault["positions"]), 1), gap="medium")
    for i, p in enumerate(vault["positions"]):
        bal = float(p.get("balance", 0))
        with cols[i % len(cols)]:
            body = UI.kv([
                ("Balance", U.fmt_kes(bal)),
                ("Moves", str(len(p.get("tx", [])))),
            ])
            st.markdown(UI.panel(p["name"], body),
                        unsafe_allow_html=True)
            st.markdown(
                UI.tx_log_rows(p.get("tx", []), 4,
                               mpesa=UI.is_mpesa(p["id"], p["name"])),
                unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    a, b = st.columns([3, 1])
    with a:
        nm = st.text_input("New pocket name", key="np_n",
                           placeholder="e.g. Equity Bank, Chama box...")
    with b:
        st.markdown("<div style='height:26px'></div>",
                    unsafe_allow_html=True)
        if st.button("Add pocket", key="np_add") and nm.strip():
            D.add_position(nm.strip())
            st.rerun()


def _tab_flow(vault, today):
    positions = vault.get("positions", [])
    pnames = [p["name"] for p in positions]
    pids = [p["id"] for p in positions]
    pmap = _pid2name(vault)
    st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                'EVERY SHILLING, EVERY DAY - LIVE, EXACT MINUTE '
                '(MOVES THE POCKET)</div>',
                unsafe_allow_html=True)
    if not positions:
        st.markdown(UI.empty_state("Add a pocket on the Cash tab first."))
    else:
        now_local = U.now_local()
        a, b, c = st.columns(3)
        with a:
            fd = st.date_input("date", value=today, key="fl_d")
        with b:
            fp = st.selectbox("pocket", pnames, key="fl_p")
        with c:
            fk = st.selectbox("flow", ["in", "out"], key="fl_k")
        r2a, r2b, r2c = st.columns(3)
        with r2a:
            fh = st.selectbox("hour", HOURS, index=now_local.hour,
                              key="fl_h")
        with r2b:
            fm = st.selectbox("minute", MINS, index=now_local.minute,
                              key="fl_m")
        with r2c:
            fa = st.number_input("amount (KSh)", 0.0, 100000000.0,
                                 0.0, step=50.0, key="fl_a")
        r3a, r3b = st.columns(2)
        with r3a:
            ftx = st.text_input("transaction id (online)", key="fl_x")
        with r3b:
            fn = st.text_input("from where / what for", key="fl_n")
        if st.button("Log it", type="primary",
                     key="fl_add") and fa > 0:
            pid = pids[pnames.index(fp)]
            eff = float(fa) if fk == "in" else -float(fa)
            time_str = str(fh) + ":" + str(fm)
            D.move_money(pid, eff, fk, note=fn.strip(),
                         time_str=time_str, txid=ftx.strip())
            st.rerun()

    flow = vault.get("flow", [])
    net = sum(M.flow_effect(f) for f in flow)
    st.markdown(UI.panel("Ledger", UI.kv([
        ("Net since Aug 1", U.fmt_kes(net)),
        ("Entries", str(len(flow))),
    ])), unsafe_allow_html=True)
    st.markdown(UI.flow_log_rows(flow, pmap, 40),
                unsafe_allow_html=True)


def _tab_bills(vault, today):
    st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                'BILLS - COVERED BEFORE THEY BITE</div>',
                unsafe_allow_html=True)
    cols = st.columns(2, gap="medium")
    for i, b in enumerate(vault["bills"]):
        need = float(b.get("need", 0) or 0)
        saved = float(b.get("saved", 0) or 0)
        pct = max(0.0, min(100.0, saved / need * 100)) if need else 0.0
        with cols[i % 2]:
            if b.get("paid"):
                chip = UI.badge("PAID " + str(b.get("paid_date", "")),
                                "#34D399")
            elif b.get("due") and b["due"] < today.isoformat():
                chip = UI.badge("OVERDUE", "#F0556B")
            else:
                chip = UI.badge("DUE " + (b.get("due") or "--"),
                                "#F5B544")
            body = (UI.progress(pct, "var(--win)")
                    + UI.kv([("Saved", U.fmt_kes(saved)),
                             ("Needed", U.fmt_kes(need)),
                             ("Status", chip)]))
            st.markdown(UI.panel(b["name"], body),
                        unsafe_allow_html=True)
            x1, x2, x3 = st.columns([1.2, 1.2, 1.4])
            with x1:
                amt = st.number_input("KSh", 0.0, 100000000.0, 0.0,
                                      step=50.0, key="ba" + b["id"])
                act = st.selectbox("action", ["save", "withdraw"],
                                   key="bk" + b["id"])
            with x2:
                need_in = st.number_input("needed", 0.0, 100000000.0,
                                          need, step=100.0,
                                          key="bn" + b["id"])
                due_in = st.date_input("due", value=today,
                                       key="bd" + b["id"])
            with x3:
                if st.button("Update", type="primary",
                             key="bs" + b["id"]):
                    if need_in != need:
                        D.set_bill(b["id"], need=need_in)
                    D.set_bill(b["id"], due=due_in.isoformat())
                    if amt > 0:
                        D.bill_tx(b["id"], act, amt)
                    st.rerun()
                if b.get("paid"):
                    if st.button("Reopen", key="br" + b["id"]):
                        D.bill_reopen(b["id"])
                        st.rerun()
                else:
                    if st.button("Mark paid", key="bp" + b["id"]):
                        D.bill_paid(b["id"], today.isoformat())
                        st.rerun()
    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    a, b, c, d = st.columns([2.4, 1.2, 1.2, 1])
    with a:
        nm = st.text_input("Bill name", key="nb_n")
    with b:
        nd = st.number_input("amount", 0.0, 100000000.0, 0.0,
                             step=100.0, key="nb_a")
    with c:
        dd = st.date_input("due", value=today, key="nb_d")
    with d:
        st.markdown("<div style='height:26px'></div>",
                    unsafe_allow_html=True)
        if st.button("Add bill", key="nb_add") and nm.strip():
            D.add_bill(nm.strip(), nd, dd.isoformat())
            st.rerun()


def _tab_fun(vault):
    f = vault.get("fun", {})
    budget = float(f.get("budget", 0) or 0)
    used = float(f.get("used", 0) or 0)
    left = max(0.0, budget - used)
    pct = max(0.0, min(100.0, used / budget * 100)) if budget else 0.0
    st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                'FUN - ENJOY WITHOUT GUILT</div>',
                unsafe_allow_html=True)
    body = (UI.progress(pct, "var(--jewel)")
            + UI.kv([("Set for fun", U.fmt_kes(budget)),
                     ("Used", U.fmt_kes(used)),
                     ("Still free", U.fmt_kes(left))]))
    st.markdown(UI.panel("Play Money", body), unsafe_allow_html=True)
    a, b, c = st.columns(3)
    with a:
        add = st.number_input("add to fun (KSh)", 0.0, 100000000.0,
                              0.0, step=100.0, key="fu_a")
        if st.button("Top up fun", key="fu_add") and add > 0:
            D.fun_tx("add", add)
            st.rerun()
    with b:
        spend = st.number_input("spent (KSh)", 0.0, 100000000.0, 0.0,
                                step=100.0, key="fu_s")
        snote = st.text_input("on what", key="fu_n")
        if st.button("Log spending", type="primary",
                     key="fu_sp") and spend > 0:
            D.fun_tx("spend", spend, snote.strip())
            st.rerun()
    with c:
        recent = f.get("tx", [])[:6]
        if recent:
            out = []
            for i, t in enumerate(recent):
                is_add = t.get("kind") == "add"
                tone = "win" if is_add else "loss"
                shown = float(t.get("amount", 0))
                if not is_add:
                    shown = -shown
                main = html.escape(str(t.get("note", "")
                                       or t.get("kind", "")))
                out.append(UI.log_row(t.get("date", ""), "",
                                      t.get("kind", ""), shown, main,
                                      tone=tone, delay=i * 25))
            inner = ('<div class="tw-loglist tw-loglist-mini">'
                     + "".join(out) + '</div>')
        else:
            inner = UI.empty_state("Nothing spent yet - go live a "
                                   "little.")
        st.markdown(UI.panel("Recent fun", inner),
                    unsafe_allow_html=True)


def _tab_items(vault, today):
    st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                'THINGS I AM SAVING TO BUY</div>',
                unsafe_allow_html=True)
    a, b, c = st.columns([3, 1.4, 1])
    with a:
        iname = st.text_input("item", key="it_n")
    with b:
        iprice = st.number_input("price (KSh)", 0.0, 100000000.0, 0.0,
                                 step=500.0, key="it_p")
    with c:
        st.markdown("<div style='height:26px'></div>",
                    unsafe_allow_html=True)
        if st.button("Add item", type="primary",
                     key="it_add") and iname.strip() and iprice > 0:
            D.add_item(iname.strip(), iprice)
            st.rerun()
    for it in vault.get("items", []):
        saved = M.item_saved(it)
        price = float(it.get("price", 0) or 0)
        pct = max(0.0, min(100.0, saved / price * 100)) if price else 0
        c1, c2, c3 = st.columns([3, 1.6, 1.2])
        with c1:
            tag = UI.badge("BOUGHT " + str(it.get("bought_date", "")),
                           "#34D399") if it.get("bought") else ""
            st.markdown(
                '<div class="tw-card-premium" style="--card-accent:'
                'var(--jewel);padding:12px 14px;margin:0">'
                '<div style="font:700 14px var(--disp);color:var(--ink)">'
                + html.escape(str(it["name"])) + " " + tag + '</div>'
                + UI.progress(pct, "var(--jewel)")
                + '<div class="tw-sub" style="margin-top:0">'
                + U.fmt_kes(saved) + " of " + U.fmt_kes(price) + " - "
                + format(pct, ".0f") + "%</div></div>",
                unsafe_allow_html=True)
        with c2:
            amt = st.number_input("KSh (+save / -pull out)",
                                  -100000000.0, 100000000.0, 0.0,
                                  step=100.0, key="ia" + it["id"])
            if st.button("Move", key="ib" + it["id"]) and amt != 0:
                D.item_tx(it["id"], amt)
                st.rerun()
        with c3:
            if not it.get("bought"):
                if st.button("Mark bought", key="im" + it["id"]):
                    D.buy_item(it["id"], today.isoformat())
                    st.rerun()


def _tab_funds(vault, today):
    st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                'VENTURES - MONEY GROWING IN THE BACKGROUND</div>',
                unsafe_allow_html=True)
    cols = st.columns(max(len(vault["funds"]), 1), gap="medium")
    for i, f in enumerate(vault["funds"]):
        bal = float(f.get("balance", 0) or 0)
        lo = float(f.get("target_lo", 0) or 0)
        hi = float(f.get("target_hi", 0) or 0)
        pct = max(0.0, min(100.0, bal / lo * 100)) if lo else 0.0
        with cols[i % len(cols)]:
            body = (
                UI.progress(pct, "var(--accent)")
                + UI.kv([
                    ("Balance", U.fmt_kes(bal)),
                    ("Target", U.fmt_kes(lo) + " - "
                     + U.fmt_kes(hi)),
                    ("To target", format(pct, ".1f") + "%"),
                    ("Deadline",
                     str(f.get("deadline", "--"))),
                ])
            )
            st.markdown(UI.panel(f["name"], body),
                        unsafe_allow_html=True)
            a, b = st.columns(2)
            with a:
                kind = st.selectbox("flow", ["in", "out"],
                                    key="fk" + f["id"])
                amt = st.number_input("KSh", 0.0, 100000000.0, 0.0,
                                      step=500.0, key="fa" + f["id"])
            with b:
                note = st.text_input("note", key="fn" + f["id"])
            if st.button("Move money", type="primary",
                         key="fb" + f["id"]) and amt > 0:
                D.fund_tx(f["id"], kind, amt, note.strip())
                st.rerun()
            st.markdown(UI.tx_log_rows(f.get("tx", []), 4),
                        unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    a, b, c, d = st.columns([2.2, 1.1, 1.1, 1.2])
    with a:
        nm = st.text_input("Venture name", key="nf_n")
    with b:
        lo = st.number_input("target low", 0.0, 1000000000.0, 0.0,
                             step=1000.0, key="nf_lo")
    with c:
        hi = st.number_input("target high", 0.0, 1000000000.0, 0.0,
                             step=1000.0, key="nf_hi")
    with d:
        dl = st.date_input("deadline", value=today, key="nf_d")
    if st.button("Add venture", key="nf_add") and nm.strip():
        D.add_fund(nm.strip(), lo, hi, dl.isoformat())
        st.rerun()


def _pantry_controls(it, key):
    c1, c2, c3, c4 = st.columns([1.6, 1, 1.1, 1.1])
    with c1:
        ns = st.number_input("stock on hand (" + str(it.get("unit", "u"))
                             + ")", 0.0, 100000000.0,
                             float(it.get("stock", 0)), step=1.0,
                             key="ps" + key)
    with c2:
        st.markdown("<div style='height:26px'></div>",
                    unsafe_allow_html=True)
        if st.button("Update stock", type="primary",
                     key="pb" + key):
            D.pantry_set_stock(it["id"], ns)
            st.rerun()
    with c3:
        lab = "Un-hide" if it.get("hidden") else "Hide (optional)"
        if st.button(lab, key="ph" + key):
            D.pantry_toggle_hidden(it["id"])
            st.rerun()
    with c4:
        sure = st.checkbox("confirm delete", key="pc" + key)
        if st.button("Remove", key="pr" + key, disabled=not sure):
            D.pantry_remove(it["id"])
            st.rerun()


def _tab_pantry(vault, today):
    pan = vault.get("pantry", {})
    items = pan.get("items", [])
    staples = [x for x in items if not x.get("hidden")]
    hidden = [x for x in items if x.get("hidden")]
    bn = M.pantry_bottleneck(pan, today)
    cage = M.pantry_checked_age(pan, today)

    if bn is None:
        bv, bd, bt = "—", "add a staple to begin", "mute"
    else:
        bv = format(bn[0], ".0f") + " days"
        bd = "shortest shelf: " + str(bn[2])
        bt = ("win" if bn[0] >= 14 else
              ("accent" if bn[0] >= 7 else
               ("loss" if bn[0] < 3 else "mute")))
    chk_txt = ("checked " + str(cage) + "d ago") if cage else \
        "set a stock to start the clock"
    row = [
        UI.tile("Food Security", bv, bd, bt, bt, "grid", "win", 0),
        UI.tile("Staples Tracked", str(len(staples)),
                "define your sufficiency", "mute", "ink",
                "list", "accent", 40),
        UI.tile("Optional / Hidden", str(len(hidden)),
                "tracked, not in the alarm", "mute", "ink",
                "hash", "jewel", 80),
        UI.tile("Pantry Check", chk_txt,
                "stock is manual - never auto-deducted",
                "mute", "ink", "clock", "accent", 120),
    ]
    st.markdown(UI.tiles_grid(row, 4), unsafe_allow_html=True)

    if staples:
        st.markdown(UI.panel(
            "Your Shelves - days of supply (aged to today)",
            "".join(UI.pantry_row(it, *M.pantry_days_left_item(it, today))
                    for it in staples)),
            unsafe_allow_html=True)
        for it in staples:
            _pantry_controls(it, it["id"])
    else:
        st.markdown(UI.panel("Your Shelves", UI.empty_state(
            "No staples yet - add ugali, omena, eggs below.")),
            unsafe_allow_html=True)

    if hidden:
        with st.expander("Pantry extras (optional - hidden from the "
                         "sufficiency alarm)"):
            st.markdown("".join(
                UI.pantry_row(it, *M.pantry_days_left_item(it, today))
                for it in hidden), unsafe_allow_html=True)
            for it in hidden:
                _pantry_controls(it, "h" + it["id"])

    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    with st.expander("+  Add a pantry item"):
        a, b, c = st.columns(3)
        with a:
            pn = st.text_input("name", key="pa_n",
                               placeholder="e.g. Beans")
            pu = st.text_input("unit", key="pa_u",
                               placeholder="g / pcs / ml")
        with b:
            pd = st.number_input("daily burn (per day)", 0.0,
                                 1000000.0, 0.0, step=1.0, key="pa_d")
            pcat = st.selectbox("category", D.PANTRY_CATS, key="pa_c")
        with c:
            pstock = st.number_input("stock on hand now", 0.0,
                                     100000000.0, 0.0, step=1.0,
                                     key="pa_s")
            phid = st.checkbox("optional / hidden", key="pa_h")
        if st.button("Add item", type="primary",
                     key="pa_add") and pn.strip():
            D.pantry_add(pn.strip(), pu.strip() or "u", pd, pcat,
                         phid, pstock)
            st.rerun()

    with st.expander("Edit an item's details (burn / category / unit)"):
        ids = [x["id"] for x in items]
        if ids:
            sel = st.selectbox("item", ids,
                               format_func=lambda i: next(
                                   (x["name"] for x in items
                                    if x["id"] == i), i),
                               key="pe_sel")
            cur = next((x for x in items if x["id"] == sel), {})
            st.caption("Current: " + str(cur.get("unit", ""))
                       + " · burn " + str(cur.get("daily", 0))
                       + "/day · " + str(cur.get("category", ""))
                       + (" · hidden" if cur.get("hidden") else ""))
            e1, e2, e3 = st.columns(3)
            with e1:
                en = st.text_input("name", value=cur.get("name", ""),
                                   key="pe_n")
                eu = st.text_input("unit", value=cur.get("unit", ""),
                                   key="pe_u")
            with e2:
                ed = st.number_input("daily burn", 0.0, 1000000.0,
                                     float(cur.get("daily", 0)),
                                     step=1.0, key="pe_d")
                ecat = st.selectbox("category", D.PANTRY_CATS,
                                    index=D.PANTRY_CATS.index(
                                        cur.get("category", "other"))
                                    if cur.get("category", "other")
                                    in D.PANTRY_CATS else 0,
                                    key="pe_c")
            with e3:
                ehid = st.checkbox("optional / hidden",
                                   value=bool(cur.get("hidden")),
                                   key="pe_h")
            if st.button("Save details", type="primary", key="pe_save"):
                D.pantry_save_details(sel, en, eu, ed, ecat, ehid)
                st.rerun()
        else:
            st.caption("Add an item first.")


def _tab_runway(vault, today):
    r = vault.get("runway", {})
    burn = float(r.get("monthly_burn", 0) or 0)
    months = int(r.get("emergency_months", 3) or 3)
    cash = M.cash_on_hand(vault)
    e = vault.get("emergency", {})
    ebal = float(e.get("balance", 0) or 0)
    target = burn * months
    rm = M.runway_months(vault)
    ep = M.emergency_progress(vault)

    row = [
        UI.tile("Monthly Burn", U.fmt_kes(burn),
                "what a normal month costs", "mute", "ink",
                "bolt", "accent", 0),
        UI.tile("Cash Runway",
                (format(rm, ".1f") + " mo") if rm else "—",
                "cash / monthly burn", "mute",
                "win" if (rm or 0) >= 3 else "ink",
                "clock", "win", 40),
        UI.tile("Emergency Target", U.fmt_kes(target),
                str(months) + " months of burn", "mute", "ink",
                "target", "jewel", 80),
        UI.tile("Ring-Fenced", U.fmt_kes(ebal),
                "set aside from your cash", "mute", "ink",
                "lock", "jewel", 120),
        UI.tile("Emergency Progress", format(ep, ".0f") + "%",
                "to the " + str(months) + "-mo target",
                "win" if ep >= 100 else "mute",
                "win" if ep >= 100 else "ink",
                "flag", "win", 160),
    ]
    st.markdown(UI.tiles_grid(row, 5), unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown(UI.panel("Your Monthly Burn",
                             '<div style="height:2px"></div>'),
                    unsafe_allow_html=True)
        nb = st.number_input("KSh / month", 0.0, 100000000.0, burn,
                             step=500.0, key="rw_b")
        if st.button("Save monthly burn", type="primary", key="rw_bs"):
            D.set_runway(monthly_burn=nb)
            st.rerun()
        st.caption("Set what you spend in a normal month. Nothing is "
                   "deducted automatically - this only feeds the runway "
                   "& emergency math below.")
        nm = st.number_input("Emergency target (months)", 1, 24,
                             months, step=1, key="rw_m")
        if st.button("Save target months", key="rw_ms"):
            D.set_runway(emergency_months=nm)
            st.rerun()
        st.caption("3 months keeps you safe without sitting idle. Hit "
                   "the target and the Ratchet button lets you raise it.")
    with c2:
        st.markdown(UI.panel("Emergency Fund - ring-fenced from cash",
                             UI.progress(ep, "var(--jewel)")
                             + UI.kv([
                                 ("Ring-fenced", U.fmt_kes(ebal)),
                                 ("Target", U.fmt_kes(target)),
                                 ("Progress", format(ep, ".1f") + "%"),
                                 ("Covered",
                                  (format(ebal / burn, ".1f") + " mo")
                                  if burn > 0 else "—"),
                             ])),
                    unsafe_allow_html=True)
        a, b, c = st.columns([1.4, 1, 1.4])
        with a:
            ea = st.number_input("KSh", 0.0, 100000000.0, 0.0,
                                 step=500.0, key="em_a")
            ek = st.selectbox("move", ["in", "out"], key="em_k")
        with b:
            en = st.text_input("note", key="em_n")
            if st.button("Move", type="primary",
                         key="em_go") and ea > 0:
                D.emergency_tx(ek, ea, en.strip())
                st.rerun()
        with c:
            funded = ebal >= target and target > 0
            if st.button("Ratchet +1 month", key="em_r",
                         disabled=not funded):
                D.emergency_ratchet()
                st.rerun()
            if not funded:
                st.caption("Funds at target to ratchet.")
        st.caption("A ring-fence is money you *choose* not to touch - "
                   "it is part of your cash, set aside in your head, "
                   "so it is never counted twice.")

    st.markdown("<div style='height:10px'></div>",
                unsafe_allow_html=True)
    st.markdown(UI.panel("Ring-Fence History",
                         UI.flow_log_rows(
                             [{"date": t.get("date", ""),
                               "time": t.get("time", ""),
                               "kind": t.get("kind", ""),
                               "amount": (float(t.get("amount", 0))
                                          if t.get("kind") == "in"
                                          else -float(t.get("amount", 0))),
                               "note": t.get("note", ""),
                               "pocket": "emergency", "txid": ""}
                              for t in e.get("tx", [])],
                             _pid2name(vault), 20)
                         if e.get("tx") else
                         UI.empty_state("No ring-fence moves yet.")),
                unsafe_allow_html=True)


def render(ctx):
    if not st.session_state.get("vault_ok", False):
        _gate()
        return

    vault, today = ctx["vault"], ctx["today"]

    if st.button("Lock vault", key="v_lock"):
        st.session_state["vault_ok"] = False
        st.rerun()

    _overview(ctx)

    st.markdown("<div style='height:12px'></div>",
                unsafe_allow_html=True)
    tabs = st.tabs(["Cash", "Daily Flow", "Bills", "Fun", "Wishlist",
                    "Ventures", "Pantry", "Runway"])
    with tabs[0]:
        _tab_cash(vault)
    with tabs[1]:
        _tab_flow(vault, today)
    with tabs[2]:
        _tab_bills(vault, today)
    with tabs[3]:
        _tab_fun(vault)
    with tabs[4]:
        _tab_items(vault, today)
    with tabs[5]:
        _tab_funds(vault, today)
    with tabs[6]:
        _tab_pantry(vault, today)
    with tabs[7]:
        _tab_runway(vault, today)
