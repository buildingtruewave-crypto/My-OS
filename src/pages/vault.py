"""The hidden money operating system - the ONLY place balances live, behind
ARCHIVE_PIN. ONE writer (move_money) moves cash, so the Daily Flow, the Cash
balances and the climb line can never drift apart. The Daily Flow is the live
ledger: pick a pocket, in/out, amount, TIME, TRANSACTION ID and note - the
pocket balance changes on save and 'out' shows as a negative. The Cash tab is
a balance dashboard + Reconcile (writes an ADJ line). Net worth is computed,
never typed, and shown nowhere else.
"""
from __future__ import annotations

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U


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


def _kind_badge(kind):
    if kind == "in":
        return UI.badge("IN", "#34D399")
    if kind == "out":
        return UI.badge("OUT", "#F0556B")
    return UI.badge("ADJ", "#F5B544")


def _overview(ctx):
    vault, today = ctx["vault"], ctx["today"]
    net = M.net_worth(vault)
    cash = M.cash_on_hand(vault)
    alloc = M.allocated(vault)
    wk_in, wk_out = M.flow_week_inout(vault.get("flow", []), today)
    bills_due = M.bills_due_soon(vault, today)
    bills_late = M.bills_overdue(vault, today)

    row = [
        UI.tile("Net Worth", U.fmt_kes(net), "everything, everywhere",
                "mute", "ink", "star", "jewel", 0),
        UI.tile("Cash On Hand", U.fmt_kes(cash), "wallet + M-Pesa + bank",
                "mute", "ink", "cash", "accent", 40),
        UI.tile("Set Aside", U.fmt_kes(alloc),
                "bills + fun + wishlist + ventures",
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
        right = "grows every day you look"
    else:
        body = UI.empty_state(
            "The growth line draws itself from your first money move.")
        right = "net worth"
    st.markdown(UI.panel("Net Worth - The Climb", body, right=right),
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


def _tab_cash(vault, now_time):
    pmap = _pid2name(vault)
    st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                'WHERE THE CASH LIVES - LOG EVERY MOVE ON THE DAILY '
                'FLOW TAB; USE RECONCILE TO FIX DRIFT</div>',
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
            target = st.number_input("reconcile to (KSh)",
                                     -100000000.0, 100000000.0,
                                     bal, step=50.0,
                                     key="rc" + p["id"])
            if st.button("Reconcile", key="rb" + p["id"]):
                if abs(target - bal) > 0.001:
                    D.move_money(p["id"], target - bal, "adjust",
                                 note="reconcile",
                                 time_str=now_time, txid="")
                    st.rerun()
            for t in p.get("tx", [])[:4]:
                eff = M.flow_effect(t)
                tone = "tw-win" if eff >= 0 else "tw-loss"
                tx = ("  #" + t["txid"]) if t.get("txid") else ""
                tm = ("  " + t["time"]) if t.get("time") else ""
                st.caption(t["date"] + tm + tx + "  " + t.get("kind", "")
                           + " " + '<span class="' + tone + '">'
                           + U.fmt_kes(eff, True) + '</span>'
                           + ("  - " + t["note"] if t.get("note")
                              else ""))
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


def _tab_flow(vault, today, now_time):
    positions = vault.get("positions", [])
    pnames = [p["name"] for p in positions]
    pids = [p["id"] for p in positions]
    pmap = _pid2name(vault)
    st.markdown('<div class="tw-lab" style="margin:2px 0 8px">'
                'EVERY SHILLING, EVERY DAY - LIVE (MOVES THE POCKET)</div>',
                unsafe_allow_html=True)
    if not positions:
        st.markdown(UI.empty_state("Add a pocket on the Cash tab first."))
    else:
        a, b, c = st.columns([1.1, 1.1, 1.2])
        with a:
            fd = st.date_input("date", value=today, key="fl_d")
            ft = st.time_input("time",
                               value=U.now_local().time(),
                               key="fl_t")
            fp = st.selectbox("pocket", pnames, key="fl_p")
        with b:
            fk = st.selectbox("flow", ["in", "out"], key="fl_k")
            fa = st.number_input("amount (KSh)", 0.0, 100000000.0,
                                 0.0, step=50.0, key="fl_a")
        with c:
            ftx = st.text_input("transaction id (online)", key="fl_x")
            fn = st.text_input("from where / what for", key="fl_n")
        if st.button("Log it", type="primary",
                     key="fl_add") and fa > 0:
            pid = pids[pnames.index(fp)]
            eff = float(fa) if fk == "in" else -float(fa)
            D.move_money(pid, eff, fk, note=fn.strip(),
                         time_str=ft.strftime("%H:%M"), txid=ftx.strip())
            st.rerun()

    flow = vault.get("flow", [])
    net = sum(M.flow_effect(f) for f in flow)
    st.markdown(UI.panel("Ledger", UI.kv([
        ("Net since Aug 1", U.fmt_kes(net)),
        ("Entries", str(len(flow))),
    ])), unsafe_allow_html=True)
    rows = []
    for f in flow[:40]:
        amt = M.flow_effect(f)
        tone = "tw-win" if amt >= 0 else "tw-loss"
        pname = pmap.get(f.get("pocket", ""),
                         f.get("pocket", "") or "—") or "—"
        rows.append([
            (f.get("date", ""), "num"),
            (f.get("time", "") or "--", "num"),
            (f.get("txid", "") or "--", ""),
            (pname, ""),
            (_kind_badge(f.get("kind", "")), ""),
            (str(f.get("note", "")), ""),
            ('<span class="' + tone + '">'
             + U.fmt_kes(amt, True) + "</span>", "num"),
        ])
    st.markdown(UI.table(["Date", "Time", "TxID", "Pocket", "Kind",
                          "Note", "Amount"], rows),
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
            inner = "".join(
                '<div class="tw-stat"><span class="k">'
                + t["date"] + (" - " + t["note"] if t.get("note")
                               else "") + '</span>'
                + '<span class="v tw-jewel">'
                + U.fmt_kes(t["amount"]) + '</span></div>'
                for t in recent)
        else:
            inner = UI.empty_state("Nothing spent yet - go live a little.")
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
            st.markdown('<div style="padding-top:6px">'
                        '<div style="font:700 14px var(--disp);'
                        'color:var(--ink)">' + str(it["name"])
                        + " " + tag + '</div>'
                        + UI.progress(pct, "var(--jewel)")
                        + '<div class="tw-sub">' + U.fmt_kes(saved)
                        + " of " + U.fmt_kes(price) + " - "
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
            for t in f.get("tx", [])[:4]:
                tone = "tw-win" if t["kind"] == "in" else "tw-loss"
                st.caption(t["date"] + "  " + t["kind"] + " "
                           + U.fmt_kes(t["amount"], True)
                           + ("  - " + t["note"] if t.get("note")
                              else ""))
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


def render(ctx):
    if not st.session_state.get("vault_ok", False):
        _gate()
        return

    vault, today = ctx["vault"], ctx["today"]
    now_time = ctx["now_dt"].strftime("%H:%M")

    if st.button("Lock vault", key="v_lock"):
        st.session_state["vault_ok"] = False
        st.rerun()

    _overview(ctx)

    st.markdown("<div style='height:12px'></div>",
                unsafe_allow_html=True)
    tabs = st.tabs(["Cash", "Daily Flow", "Bills", "Fun",
                    "Wishlist", "Ventures"])
    with tabs[0]:
        _tab_cash(vault, now_time)
    with tabs[1]:
        _tab_flow(vault, today, now_time)
    with tabs[2]:
        _tab_bills(vault, today)
    with tabs[3]:
        _tab_fun(vault)
    with tabs[4]:
        _tab_items(vault, today)
    with tabs[5]:
        _tab_funds(vault, today)
