"""The hidden money manager. Sits behind the innocent 'Archive' nav
item and a PIN (default 2580 - change it in Settings). Holds the HHO
Carbon Cleaning fund, the savings buckets, the wishlist and the daily
flow book - amounts never appear on the public pages."""
from __future__ import annotations

import datetime as dt

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
            if pin == str(st.session_state.get("pin", D.DEFAULT_PIN)):
                st.session_state["vault_ok"] = True
                st.rerun()
            else:
                st.caption("Nothing here.")


def render(ctx):
    if not st.session_state.get("vault_ok", False):
        _gate()
        return

    vault, today = ctx["vault"], ctx["today"]
    fund = vault["fund"]
    flow = vault.get("flow", [])

    if st.button("Lock vault", key="v_lock"):
        st.session_state["vault_ok"] = False
        st.rerun()

    bal = M.fund_balance(fund)
    tgt_lo = float(fund.get("target_lo", 150000) or 150000)
    tgt_hi = float(fund.get("target_hi", 200000) or 200000)
    pct_lo = max(0.0, min(100.0, bal / tgt_lo * 100)) if tgt_lo else 0
    week_net = M.fund_week_net(fund, today)
    try:
        deadline = dt.date.fromisoformat(fund.get("deadline",
                                                  "2027-01-31"))
        days_left = max(0, (deadline - today).days)
    except Exception:
        days_left = 0

    row = [
        UI.tile("Fund Balance", U.fmt_kes(bal), "HHO carbon cleaning",
                "mute", "ink", "cash", "accent", 0),
        UI.tile("Target", "KSh " + U.fmt_k(tgt_lo) + "-"
                + U.fmt_k(tgt_hi), "Nairobi launch",
                "mute", "ink", "target", "jewel", 40),
        UI.tile("To Launch", format(pct_lo, ".0f") + "%",
                "of the " + U.fmt_k(tgt_lo) + " floor",
                "win" if pct_lo >= 60 else "mute", "ink",
                "flag", "win", 80),
        UI.tile("Days Left", str(days_left), "to Jan 2027",
                "mute", "ink", "clock", "accent", 120),
        UI.tile("This Week", U.fmt_kes(week_net, True), "net flow",
                "win" if week_net >= 0 else "loss",
                "win" if week_net >= 0 else "loss", "trend", "win",
                160),
    ]
    st.markdown(UI.tiles_grid(row, 5), unsafe_allow_html=True)

    st.markdown(UI.panel(
        fund.get("name", "Business Fund"),
        UI.progress(pct_lo, "var(--accent)")
        + UI.kv([("To " + U.fmt_kes(tgt_lo),
                  format(pct_lo, ".1f") + "%"),
                 ("To " + U.fmt_kes(tgt_hi),
                  format(max(0.0, min(100.0, bal / tgt_hi * 100)),
                         ".1f") + "%"),
                 ("Starting capital",
                  U.fmt_kes(fund.get("start_capital", 0)))]),
        right="money in / out daily"), unsafe_allow_html=True)

    f1, f2 = st.columns(2, gap="medium")
    with f1:
        cap = st.number_input("Starting capital (KSh)", 0.0,
                              100000000.0,
                              float(fund.get("start_capital", 0)),
                              step=500.0, key="f_cap")
        if st.button("Set starting capital", key="f_capb"):
            D.set_fund_capital(cap)
            st.rerun()
    with f2:
        a, b, c = st.columns([1.2, 1.2, 2])
        with a:
            fd = st.date_input("date", value=today, key="f_d")
            fk = st.selectbox("kind", ["in", "out"], key="f_k")
        with b:
            fa = st.number_input("amount (KSh)", 0.0, 100000000.0,
                                 0.0, step=100.0, key="f_a")
        with c:
            fs = st.text_input("source / where it went", key="f_s")
        if st.button("Record", type="primary",
                     key="f_add") and fa > 0:
            D.fund_tx(fd.isoformat(), fk, fa, fs.strip())
            st.rerun()

    rows = []
    for t in fund.get("tx", [])[:15]:
        tone = "tw-win" if t["kind"] == "in" else "tw-loss"
        rows.append([
            (t["date"], "num"),
            (UI.badge(t["kind"].upper(),
                      "#34D399" if t["kind"] == "in" else "#F0556B"),
             ""),
            (str(t.get("source", "")), ""),
            ('<span class="' + tone + '">'
             + U.fmt_kes(float(t["amount"]), True) + "</span>",
             "num"),
        ])
    st.markdown(UI.panel("Fund Ledger",
                         UI.table(["Date", "Flow", "Source",
                                   "Amount"], rows)),
                unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>",
                unsafe_allow_html=True)
    st.markdown('<div class="tw-lab" style="margin:4px 0 8px">'
                'DAILY FLOW - MONEY IN &amp; OUT, EVERY DAY</div>',
                unsafe_allow_html=True)
    fl1, fl2 = st.columns([3, 2], gap="medium")
    with fl1:
        a, b, c = st.columns([1.1, 1.1, 1.2])
        with a:
            fld = st.date_input("date", value=today, key="fl_d")
            flk = st.selectbox("flow", ["in", "out"], key="fl_k")
            fla = st.number_input("amount (KSh)", 0.0, 100000000.0,
                                  0.0, step=50.0, key="fl_a")
        with b:
            fls = st.text_input("from where", key="fl_s",
                                placeholder="salary, client, gift...")
        with c:
            flg = st.text_input("where it went / what I got",
                                key="fl_g",
                                placeholder="rent, stock, lunch...")
        if st.button("Log flow", type="primary",
                     key="fl_add") and fla > 0:
            D.add_flow(fld.isoformat(), flk, fla, fls.strip(),
                       flg.strip())
            st.rerun()
    with fl2:
        st.markdown(UI.panel("Flow Position", UI.kv([
            ("Net since Aug 1",
             U.fmt_kes(M.flow_balance(flow))),
            ("This week",
             U.fmt_kes(M.flow_week_net(flow, today), True)),
            ("Entries", str(len(flow))),
        ])), unsafe_allow_html=True)
    rows = []
    for f in flow[:20]:
        tone = "tw-win" if f["kind"] == "in" else "tw-loss"
        rows.append([
            (f["date"], "num"),
            (UI.badge(f["kind"].upper(),
                      "#34D399" if f["kind"] == "in" else "#F0556B"),
             ""),
            (str(f.get("src", "")), ""),
            (str(f.get("got", "")), ""),
            ('<span class="' + tone + '">'
             + U.fmt_kes(float(f["amount"]), True) + "</span>",
             "num"),
        ])
    st.markdown(UI.panel("Ledger",
                         UI.table(["Date", "Flow", "From",
                                   "Got / Paid", "Amount"], rows)),
                unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>",
                unsafe_allow_html=True)
    st.markdown('<div class="tw-lab" style="margin:4px 0 8px">'
                'SAVINGS BUCKETS - UPDATE DAILY</div>',
                unsafe_allow_html=True)
    bcols = st.columns(len(vault["buckets"]), gap="medium")
    for i, b in enumerate(vault["buckets"]):
        bb = M.bucket_balance(b)
        tgt = float(b.get("target", 0) or 0)
        pct = max(0.0, min(100.0, bb / tgt * 100)) if tgt else 0.0
        with bcols[i]:
            body = (UI.progress(pct, "var(--win)") if tgt else "") \
                + UI.kv([("Balance", U.fmt_kes(bb)),
                         ("Target", U.fmt_kes(tgt) if tgt else "--"),
                         ("Entries", str(len(b.get("tx", []))))])
            st.markdown(UI.panel(b["name"], body),
                        unsafe_allow_html=True)
            x1, x2 = st.columns(2)
            with x1:
                bk = st.selectbox("flow", ["in", "out"],
                                  key="bk" + b["id"])
                ba = st.number_input("KSh", 0.0, 100000000.0, 0.0,
                                     step=50.0, key="ba" + b["id"])
            with x2:
                bn = st.text_input("note", key="bn" + b["id"])
                bt = st.number_input("new target", 0.0, 100000000.0,
                                     tgt, step=500.0,
                                     key="bt" + b["id"])
            if st.button("Update bucket", type="primary",
                         key="bs" + b["id"]):
                if bt != tgt:
                    D.set_bucket_target(b["id"], bt)
                if ba > 0:
                    D.bucket_tx(b["id"], today.isoformat(), bk, ba,
                                bn.strip())
                st.rerun()
            for t in b.get("tx", [])[:4]:
                st.caption(t["date"] + "  " + t["kind"] + " "
                           + U.fmt_kes(t["amount"], True)
                           + ("  - " + t["note"] if t.get("note")
                              else ""))

    st.markdown("<div style='height:12px'></div>",
                unsafe_allow_html=True)
    st.markdown('<div class="tw-lab" style="margin:4px 0 8px">'
                'ITEMS I AM SAVING TO BUY</div>',
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
        c1, c2, c3 = st.columns([3, 1.4, 1.2])
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
            amt = st.number_input("add KSh", 0.0, 100000000.0, 0.0,
                                  step=100.0, key="ia" + it["id"])
            if st.button("Add money", key="ib" + it["id"]) and amt > 0:
                D.item_tx(it["id"], today.isoformat(), amt)
                st.rerun()
        with c3:
            if not it.get("bought"):
                if st.button("Mark bought", key="im" + it["id"]):
                    D.buy_item(it["id"], today.isoformat())
                    st.rerun()
