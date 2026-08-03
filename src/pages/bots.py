"""Deriv + Alpaca bots and any other venture, plus the Deriv CONNECTED
INTELLIGENCE panel: the trading app's AI council verdict (from
deriv_venture_advice) as the primary read, its research patterns, and
PULSE's own deterministic math as a cross-check.
"""
from __future__ import annotations

import html

import streamlit as st

from .. import data as D
from .. import metrics as M
from .. import ui as UI

try:
    from .. import trade_intel as TI
    _HAS_TI = True
except Exception:
    TI = None
    _HAS_TI = False

_STATUS = {"testing": ("TESTING", "#F5B544"),
           "demo": ("DEMO", "#7C8AA5"),
           "live": ("LIVE", "#34D399")}

_ACT_COLOR = {"ENTER": "#34D399", "ENTER SMALL": "#2DD4BF",
              "WAIT": "#F5B544", "AVOID": "#F0556B",
              "WATCH": "#7C8AA5"}


def _window_tile(label, s, delay):
    if not s or s.get("n", 0) == 0:
        return UI.tile(label, "—", "no trades", "mute", "ink",
                       "pulse", "accent", delay)
    net = s["net"]
    tone = "win" if net > 0 else ("loss" if net < 0 else "mute")
    vt = "win" if net > 0 else ("loss" if net < 0 else "ink")
    return UI.tile(label, "%+.2f" % net,
                   "%.0f%% WR · %d trades" % (s["win_rate"] * 100,
                                              s["n"]),
                   tone, vt, "trend", "accent", delay)


def _stance_badge(stance):
    color = {"bullish": "#34D399", "cautious": "#F5B544",
             "bearish": "#F0556B"}.get(stance, "#7C8AA5")
    return UI.badge(stance.upper(), color)


def _json_brief(obj, maxlen=500):
    try:
        if isinstance(obj, dict):
            s = " · ".join(str(k) + ": " + str(v)
                           for k, v in obj.items())
        elif isinstance(obj, list):
            s = " · ".join(str(x) for x in obj)
        else:
            s = str(obj)
    except Exception:
        s = ""
    return s[:maxlen]


def _deriv_intelligence():
    st.markdown('<div class="tw-lab" style="margin:14px 0 8px">'
                'DERIV · CONNECTED INTELLIGENCE</div>',
                unsafe_allow_html=True)
    if not _HAS_TI:
        st.markdown(UI.panel("Signal Feed",
                             UI.empty_state("trade_intel not loaded."),
                             right="offline"),
                    unsafe_allow_html=True)
        return
    c1, c2 = st.columns([5, 1])
    with c2:
        force = st.button("⟳ Refresh", key="ti_refresh")
    data = TI.get_signal(force=force)
    remote = data.get("remote") or {}
    with c1:
        chip = (UI.badge("● CONNECTED", "#34D399")
                if data["connected"]
                else UI.badge("● OFFLINE", "#F0556B"))
        bits = [chip]
        if data.get("n_total"):
            bits.append(UI.badge(str(data["n_total"]) + " trades",
                                 "#4C8DFF"))
        if remote.get("research"):
            bits.append(UI.badge(
                str(remote["research"]["n"]) + " researched",
                "#8B7CFF"))
        if data.get("last_sync"):
            bits.append(UI.badge("sync " + data["last_sync"][11:19],
                                 "#7C8AA5"))
        st.markdown('<div style="display:flex;gap:6px;flex-wrap:wrap">'
                    + " ".join(bits) + '</div>',
                    unsafe_allow_html=True)

    if not data["connected"]:
        st.markdown(UI.panel(
            "Signal Feed",
            UI.empty_state("Not connected to Supabase - "
                           + str(data.get("message", ""))),
            right="offline"), unsafe_allow_html=True)
        return

    if not data.get("n_total") and not remote.get("has_trades"):
        st.markdown(UI.panel(
            "Signal Feed",
            UI.empty_state("No trades yet. Once the trading app posts "
                           "results, the council starts scanning across "
                           "days, weeks and months."),
            right="listening"), unsafe_allow_html=True)
        return

    vv = remote.get("verdict_view")
    if vv:
        act_color = vv["color"]
        head = (
            '<div style="display:flex;align-items:center;gap:14px;'
            'flex-wrap:wrap;margin-bottom:10px">'
            '<span style="font:800 30px/1 var(--disp);color:'
            + act_color + ';letter-spacing:-.01em">'
            + html.escape(vv["action"]) + '</span>'
            + UI.badge(vv["raw"] or "council verdict", act_color)
            + (UI.badge("risk %.2f%%/trade" % vv["risk_pct"],
                        "#4C8DFF") if vv["risk_pct"] else "")
            + (UI.badge("×%s multiplier" % vv["multiplier"],
                        "#8B7CFF") if vv["multiplier"] else "")
            + '</div>')
        body = head
        if vv["reasoning"]:
            body += ('<div style="font:500 13.5px/1.55 var(--body);'
                     'color:var(--ink)">'
                     + html.escape(vv["reasoning"]) + '</div>')
        if vv["discussion"]:
            body += ('<div class="tw-sub" style="margin-top:8px">'
                     + html.escape(_json_brief(vv["discussion"]))
                     + '</div>')
        st.markdown(UI.panel("Research Council Verdict (trading app)",
                             body, right="primary read"),
                    unsafe_allow_html=True)
    elif data.get("verdict"):
        v = data["verdict"]
        act_color = _ACT_COLOR.get(v["action"], "#7C8AA5")
        st.markdown(UI.panel(
            "Council Verdict",
            '<div style="display:flex;align-items:center;gap:14px;'
            'flex-wrap:wrap;margin-bottom:10px">'
            '<span style="font:800 30px/1 var(--disp);color:'
            + act_color + '">' + html.escape(v["action"]) + '</span>'
            + UI.badge("score %d/100" % v["score"], act_color)
            + UI.badge("risk %.2f%%/trade" % v["risk_pct"], "#4C8DFF")
            + '</div>'
            '<div style="font:500 13.5px/1.55 var(--body);'
            'color:var(--ink)">' + html.escape(v["summary"]) + '</div>',
            right="primary read"), unsafe_allow_html=True)

    res = remote.get("research")
    if res and res["n"]:
        pats = sorted(res["patterns"].items(), key=lambda kv: kv[1],
                      reverse=True)[:5]
        pat_txt = ", ".join("%s ×%d" % (p, n) for p, n in pats) or "—"
        st.markdown(UI.panel(
            "What The Research Sees",
            UI.kv([
                ("Trades researched", str(res["n"])),
                ("Strengths logged", str(res["strengths"])),
                ("Weaknesses logged", str(res["weaknesses"])),
                ("Mistakes logged", str(res["mistakes"])),
                ("Patterns detected", pat_txt),
            ]), right="from deriv_trade_research"),
            unsafe_allow_html=True)

    kn = remote.get("knowledge") or []
    if kn:
        rows = []
        for k in kn[:8]:
            w = int(k.get("wins", 0))
            l = int(k.get("losses", 0))
            tot = w + l
            wr = (w / tot * 100) if tot else 0.0
            rows.append([
                (html.escape(str(k.get("kind", ""))), ""),
                (html.escape(str(k.get("pattern_key", ""))), ""),
                (str(k.get("occurrences", 0)), "num"),
                ("%.0f%%" % wr, "num"),
                (html.escape(str(k.get("description", ""))[:60]), ""),
            ])
        st.markdown(UI.panel(
            "Accumulated Knowledge",
            UI.table(["Kind", "Pattern", "Seen", "Win%", "Note"],
                     rows), right="from deriv_research_knowledge"),
            unsafe_allow_html=True)

    w = data.get("windows") or {}
    if w:
        row = [_window_tile("Last 7 days", w.get("7d"), 0),
               _window_tile("Last 30 days", w.get("30d"), 40),
               _window_tile("Last 90 days", w.get("90d"), 80),
               _window_tile("All time", w.get("all"), 120)]
        st.markdown(UI.tiles_grid(row, 4), unsafe_allow_html=True)

    if data.get("council"):
        council_rows = []
        for c in data["council"]:
            council_rows.append(
                '<div style="display:flex;gap:10px;'
                'align-items:flex-start;padding:9px 0;'
                'border-bottom:1px solid var(--hair)">'
                + _stance_badge(c["stance"])
                + '<div><div class="tw-sub" style="margin-top:0">'
                + html.escape(c["name"]) + '</div>'
                '<div style="font:500 12.5px/1.45 var(--body);'
                'color:var(--ink-2)">' + html.escape(c["point"])
                + '</div></div></div>')
        st.markdown(UI.panel("PULSE Cross-Check",
                             "".join(council_rows),
                             right="deterministic math"),
                    unsafe_allow_html=True)

    if data.get("recent"):
        feed = []
        for i, t in enumerate(data["recent"]):
            ts = t.get("ts")
            d = ts.strftime("%b %d") if ts else "—"
            tm = ts.strftime("%H:%M") if ts else ""
            pnl = t["pnl"]
            kind = "in" if pnl >= 0 else "out"
            market = html.escape(t.get("market") or "Deriv")
            main = '<b>' + market + '</b>'
            feed.append(UI.log_row(d, tm, kind, pnl, main,
                                   tone="win" if pnl >= 0 else "loss",
                                   delay=min(i * 30, 300)))
        st.markdown(UI.panel("Received Trades",
                             '<div class="tw-loglist">'
                             + " ".join(feed) + '</div>',
                             right="newest first"),
                    unsafe_allow_html=True)


def render(ctx):
    bots, today = ctx["bots"], ctx["today"]
    blist, logs = bots["bots"], bots["logs"]
    all_pnl = sum(float(l["pnl"]) for l in logs)
    wins = sum(1 for l in logs if float(l["pnl"]) > 0)
    wr = (wins / len(logs) * 100) if logs else 0.0
    row = [
        UI.tile("Ventures Running", str(len(blist)), "tracked",
                "mute", "ink", "bot", "accent", 0),
        UI.tile("Logs Recorded", str(len(logs)), "since Aug 1",
                "mute", "ink", "list", "accent", 40),
        UI.tile("Net Result", format(all_pnl, "+,.0f"),
                "all ventures", "win" if all_pnl >= 0 else "loss",
                "win" if all_pnl >= 0 else "loss", "trend", "win",
                80),
        UI.tile("Win Rate", format(wr, ".0f") + "%", "all logs",
                "mute", "ink", "target", "jewel", 120),
    ]
    st.markdown(UI.tiles_grid(row, 4), unsafe_allow_html=True)
    cols = st.columns(min(max(len(blist), 1), 2), gap="medium")
    for i, b in enumerate(blist):
        s = M.bot_stats(logs, b["id"])
        st_chip = _STATUS.get(b["status"], ("?", "#7C8AA5"))
        with cols[i % len(cols)]:
            body = UI.kv([
                ("Platform", b.get("platform", "")),
                ("Status", UI.badge(st_chip[0], st_chip[1])
                 + ("  since " + b["live_date"]
                    if b.get("live_date") else "")),
                ("Logs", str(s["n"]) + "  (" + str(s["w"]) + "W / "
                 + str(s["l"]) + "L)"),
                ("Win rate", format(s["wr"], ".0f") + "%"),
                ("Net PnL", '<span class="'
                 + ("tw-win" if s["pnl"] >= 0 else "tw-loss") + '">'
                 + format(s["pnl"], "+,.2f") + "</span>"),
                ("Risk deployed", format(s["risk"], ",.2f")),
                ("Reward : Risk", format(s["rr"], ".2f") + " : 1"),
            ])
            st.markdown(UI.panel(b["name"], body),
                        unsafe_allow_html=True)
            if b["status"] != "live":
                if st.button("Transition to LIVE",
                             key="bl" + b["id"]):
                    D.set_bot_status(b["id"], "live",
                                     ctx["today_iso"])
                    st.rerun()
            recent = [l for l in logs if l["bot"] == b["id"]][:5]
            if recent:
                rows = []
                for l in recent:
                    tone = "tw-win" if float(l["pnl"]) >= 0 else \
                        "tw-loss"
                    rows.append([
                        (l["date"], "num"),
                        (format(float(l["risk"]), ",.2f"), "num"),
                        ('<span class="' + tone + '">'
                         + format(float(l["pnl"]), "+,.2f")
                         + "</span>", "num"),
                        (str(l.get("notes", "")), ""),
                    ])
                st.markdown(UI.table(["Date", "Risk", "PnL", "Notes"],
                                     rows), unsafe_allow_html=True)

    _deriv_intelligence()

    st.markdown("<div style='height:12px'></div>",
                unsafe_allow_html=True)
    e1, e2 = st.columns(2, gap="medium")
    with e1:
        st.markdown(UI.panel("Log Today's Run",
                             '<div style="height:2px"></div>'),
                    unsafe_allow_html=True)
        a, b = st.columns(2)
        with a:
            ld = st.date_input("Date", value=today, key="bg_d")
            bot_id = st.selectbox(
                "Venture", [x["id"] for x in blist],
                format_func=lambda i: next(
                    (x["name"] for x in blist if x["id"] == i), i),
                key="bg_b")
        with b:
            risk = st.number_input("Risk taken", 0.0, 10000000.0,
                                   0.0, step=1.0, key="bg_r")
            pnl = st.number_input("Result (+win / -loss)",
                                  -10000000.0, 10000000.0, 0.0,
                                  step=1.0, key="bg_p")
        notes = st.text_input("Notes (strategy, behaviour, fixes)",
                              key="bg_n")
        if st.button("Add log", type="primary", key="bg_add"):
            D.add_bot_log(ld.isoformat(), bot_id, risk, pnl,
                          notes.strip())
            st.rerun()
    with e2:
        st.markdown(UI.panel("Add a Venture",
                             '<div style="height:2px"></div>'),
                    unsafe_allow_html=True)
        nm = st.text_input("Name (e.g. TrueWave inventory, HHO test)",
                           key="ba_n")
        pf = st.text_input("Platform / area", key="ba_p")
        if st.button("Add venture", type="primary",
                     key="ba_add") and nm.strip():
            D.add_bot(nm.strip(), pf.strip())
            st.rerun()
        st.markdown(UI.panel(
            "This Week - all ventures",
            UI.bars(M.bot_week(logs, today, 7)), right="net per day"),
            unsafe_allow_html=True)
