"""Sales - lead intake + the connected journey desk + tally + commissions +
income. The journey is a row of clickable magic-tile stage cards; the current
stage card holds that step's actions, always leaves a "continue / miracle"
path forward and an "End journey" option, and ended clients can be reopened.
Every widget is keyed to client + current stage so a refresh never jumps back
to another stage or another client. The client selector uses IDs (not indices)
so adding a lead mid-process never shifts your selection.
"""
from __future__ import annotations
import datetime as dt
import streamlit as st
from .. import data as D
from .. import metrics as M
from .. import ui as UI
from .. import util as U

_CALL_RESULTS = ["Follow-back", "Agreed to proceed", "No answer",
                 "Never started", "Journey ended"]
_RESCHEDULE = [("keep today", 0), ("tomorrow", 1), ("in 2 days", 2),
               ("in 3 days", 3), ("next week", 7)]

SALES_TILE_CSS = """
<style>
@keyframes stGlow{0%,100%{box-shadow:0 0 6px 0 var(--stc)}
50%{box-shadow:0 0 18px 2px var(--stc)}}
@keyframes stRise{from{opacity:0;transform:translateY(8px)}
to{opacity:1;transform:none}}
.st-tiles{display:flex;gap:8px;overflow-x:auto;padding:6px 0 10px;
-webkit-overflow-scrolling:touch;}
.st-tile{position:relative;flex:0 0 auto;min-width:110px;max-width:150px;
padding:10px 12px;border-radius:11px;cursor:pointer;
border:1.5px solid var(--hair);background:linear-gradient(180deg,
var(--panel),var(--panel-2));transition:transform .18s,border-color .18s,
box-shadow .18s;animation:stRise .4s ease both;}
.st-tile:hover{transform:translateY(-3px);border-color:var(--stc);}
.st-tile.st-cur{border-color:var(--stc);
box-shadow:0 0 12px 0 var(--stc);animation:stGlow 2.2s ease-in-out infinite;}
.st-tile.st-done{opacity:.72;}
.st-tile.st-done::after{content:'✓';position:absolute;top:5px;right:7px;
font:700 10px var(--mono);color:var(--win);}
.st-tile.st-future{opacity:.45;}
.st-tile-name{font:700 10.5px/1.25 var(--disp);color:var(--ink);
letter-spacing:.02em;margin-bottom:4px;word-break:break-word;}
.st-tile-bar{height:3px;border-radius:2px;background:var(--stc);
margin-top:6px;opacity:.85;}
.st-tile-idx{font:600 8px var(--mono);color:var(--mute);
letter-spacing:.06em;}
</style>
"""


def _pocket_options(vault):
    positions = vault.get("positions", [])
    names = ["— none —"] + [p["name"] for p in positions]
    ids = [""] + [p["id"] for p in positions]
    return names, ids


def _plan_options():
    return [""] + [p["label"] for p in D.get_plans()]


def _lead_form(ctx):
    with st.expander("+  Log a new lead  (name · phone · source · "
                     "location · wants · heat · first note)"):
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
                         want.strip(), "", note.strip(),
                         ctx["today_iso"], ctx["now_str"],
                         location=loc.strip())
            st.rerun()


def _journey_map(c, ctx, k):
    """Magic-tile journey map. Each stage is a glowing card. Clicking a
    non-current tile moves the client there."""
    cur = c.get("stage", "new")
    stages = D.get_stages()
    journey = D.journey_ids()
    cur_idx = journey.index(cur) if cur in journey else -1

    st.markdown(SALES_TILE_CSS, unsafe_allow_html=True)
    tiles_html = '<div class="st-tiles">'
    for i, s in enumerate(stages):
        sid = s["id"]
        col = s.get("color", "#7C8AA5")
        is_cur = (sid == cur)
        if cur_idx >= 0 and sid in journey:
            sidx = journey.index(sid)
            if sidx < cur_idx:
                cls = "st-done"
            elif sidx == cur_idx:
                cls = "st-cur"
            else:
                cls = "st-future"
        elif is_cur:
            cls = "st-cur"
        else:
            cls = "st-future"
        tiles_html += (
            '<div class="st-tile ' + cls + '" style="--stc:' + col + '">'
            '<div class="st-tile-idx">' + str(i + 1) + '</div>'
            '<div class="st-tile-name">'
            + str(s.get("label", sid)) + '</div>'
            '<div class="st-tile-bar"></div>'
            '</div>')
    tiles_html += '</div>'
    st.markdown(tiles_html, unsafe_allow_html=True)

    cols = st.columns(min(len(stages), 7))
    for i, s in enumerate(stages):
        sid = s["id"]
        is_cur = (sid == cur)
        with cols[i % len(cols)]:
            if st.button(
                    ("● " if is_cur else "○ ")
                    + s.get("label", sid)[:18],
                    key=k + "mv" + sid,
                    help=("current stage" if is_cur
                          else "move client here")):
                if sid != cur:
                    D.set_stage(c["id"], sid, ctx["now_str"])
                    st.rerun()


def _end_reopen(c, ctx, k):
    if c.get("ended"):
        if st.button("Reopen journey", key=k + "re"):
            D.reopen_journey(c["id"], ctx["now_str"])
            st.rerun()
    else:
        sure = st.checkbox("confirm end journey", key=k + "ejc")
        if st.button("End journey", key=k + "ej", disabled=not sure):
            D.end_journey(c["id"], ctx["now_str"])
            st.rerun()


def _stage_actions(c, ctx, k):
    stg = c.get("stage", "new")
    now_str = ctx["now_str"]
    today = ctx["today"]

    if stg in ("new", "followup", "undecided"):
        st.markdown('<div class="tw-lab" style="margin:6px 0 6px">'
                    'CALL RESULT</div>', unsafe_allow_html=True)
        r1, r2 = st.columns([2, 1])
        with r1:
            result = st.selectbox("result", _CALL_RESULTS,
                                  key=k + "res" + stg)
        with r2:
            fb_on = st.checkbox("follow-back", key=k + "fb" + stg)
        if fb_on:
            f1, f2, f3 = st.columns(3)
            with f1:
                fbd = st.date_input("follow-back date", value=today,
                                    key=k + "fbd" + stg)
            with f2:
                fbt = st.time_input("time", key=k + "fbt" + stg)
            with f3:
                fbs = st.text_input("what was said", key=k + "fbs" + stg)
        if st.button("Save call result", type="primary",
                     key=k + "save" + stg):
            if result == "Agreed to proceed":
                D.update_client(c["id"], {"stage": "agreed",
                                          "follow_done": True},
                                now_str, "Agreed to proceed - "
                                "application started")
            elif result == "Follow-back":
                fa = dt.datetime.combine(fbd, fbt)
                D.update_client(c["id"], {
                    "follow_at": fa.isoformat(timespec="minutes"),
                    "follow_done": False,
                    "follow_note": fbs.strip() if fb_on else "",
                    "stage": "followup"},
                    now_str, "Follow-back: "
                    + (fbs if fb_on else "call back"))
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

    elif stg == "agreed":
        st.markdown('<div class="tw-lab" style="margin:6px 0 6px">'
                    'APPLICATION - ID NUMBER + PAYMENT PLAN + DEVICE'
                    '</div>', unsafe_allow_html=True)
        a1, a2, a3 = st.columns(3)
        with a1:
            idn = st.text_input("ID number",
                                value=c.get("id_number", ""),
                                key=k + "id" + stg)
        with a2:
            po = _plan_options()
            cur_p = c.get("plan", "") or ""
            plan = st.selectbox("Payment plan", po,
                                index=po.index(cur_p)
                                if cur_p in po else 0,
                                key=k + "pl" + stg)
        with a3:
            dev = st.text_input("Device / model",
                                value=c.get("device", "")
                                or c.get("want", ""),
                                key=k + "dv" + stg)
        if st.button("Save application → pre-screen",
                     type="primary", key=k + "app" + stg):
            D.update_client(c["id"], {"id_number": idn.strip(),
                                      "plan": plan,
                                      "device": dev.strip(),
                                      "want": dev.strip(),
                                      "stage": "prescreen"},
                            now_str, "Application saved - to pre-screen")
            st.rerun()

    elif stg == "prescreen":
        st.markdown('<div class="tw-lab" style="margin:6px 0 6px">'
                    'PRE-SCREENING (M-PESA STATEMENT)</div>',
                    unsafe_allow_html=True)
        mp = st.text_input("M-Pesa statement ref / note",
                           value=c.get("mpesa_statement", ""),
                           key=k + "mp" + stg)
        pr = st.selectbox("pre-screen result", D.PRESCREEN_RESULTS,
                          index=D.PRESCREEN_RESULTS.index(
                              c.get("prescreen", ""))
                          if c.get("prescreen", "")
                          in D.PRESCREEN_RESULTS else 0,
                          key=k + "pr" + stg)
        agreed = ""
        if pr == "Change payment plan":
            agreed = st.selectbox("client agreed to new plan?",
                                  ["", "Agreed", "Undecided"],
                                  key=k + "ag" + stg)
        if st.button("Apply pre-screen", type="primary",
                     key=k + "go" + stg):
            if pr == "Qualifies":
                D.update_client(c["id"], {"mpesa_statement": mp,
                                          "prescreen": pr,
                                          "stage": "docs"},
                                now_str, "Pre-screened - qualifies")
            elif pr == "Cash offer only":
                D.update_client(c["id"], {"mpesa_statement": mp,
                                          "prescreen": pr,
                                          "stage": "cash_offer"},
                                now_str, "Cash offer only")
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
                                    now_str, "Plan changed - undecided")
            else:
                D.update_client(c["id"], {"mpesa_statement": mp},
                                now_str, "M-Pesa statement logged")
            st.rerun()

    elif stg == "docs":
        st.markdown('<div class="tw-lab" style="margin:6px 0 6px">'
                    'DOCS - ID FRONT/BACK + SELFIE + NEXT OF KIN</div>',
                    unsafe_allow_html=True)
        d1, d2 = st.columns(2)
        with d1:
            idf = st.text_input("ID front (ref)",
                                value="" if c.get("docs", {}).get(
                                    "id_front") in (None, "pending")
                                else c.get("docs", {}).get("id_front"),
                                key=k + "idf" + stg)
            idb = st.text_input("ID back (ref)",
                                value="" if c.get("docs", {}).get(
                                    "id_back") in (None, "pending")
                                else c.get("docs", {}).get("id_back"),
                                key=k + "idb" + stg)
        with d2:
            slf = st.text_input("Clear selfie (ref)",
                                value="" if c.get("docs", {}).get(
                                    "selfie") in (None, "pending")
                                else c.get("docs", {}).get("selfie"),
                                key=k + "sf" + stg)
            nok = st.text_input("Next of kin",
                                value="" if c.get("docs", {}).get(
                                    "next_of_kin") in (None, "pending")
                                else c.get("docs", {}).get("next_of_kin"),
                                key=k + "nok" + stg)
        done_docs = idf and idb and slf and nok
        if st.button("Save docs → convert prospect",
                     type="primary", key=k + "docs" + stg,
                     disabled=not done_docs):
            D.update_client(c["id"], {"docs": {
                "id_front": "received", "id_back": "received",
                "selfie": "received", "next_of_kin": "received"},
                "stage": "briefing"},
                now_str, "Docs complete - to Convert Prospect")
            st.rerun()
        if not done_docs:
            st.caption("Fill all four to continue.")

    elif stg == "briefing":
        st.markdown('<div class="tw-lab" style="margin:6px 0 6px">'
                    'CONVERT PROSPECT - brief them for the credit call'
                    '</div>', unsafe_allow_html=True)
        agreed = st.checkbox("client agreed to the credit call",
                             value=bool(c.get("brief_agreed")),
                             key=k + "ba" + stg)
        if st.button("Convert Prospect", type="primary",
                     key=k + "conv" + stg, disabled=not agreed):
            D.update_client(c["id"], {"brief_agreed": True,
                                      "stage": "sys_decision"},
                            now_str, "Converted prospect - to System "
                            "Decision")
            st.rerun()

    elif stg == "sys_decision":
        st.markdown('<div class="tw-lab" style="margin:6px 0 6px">'
                    'SYSTEM DECISION (before the credit call)</div>',
                    unsafe_allow_html=True)
        sd = st.selectbox("system decision", D.SYS_DECISIONS,
                          index=D.SYS_DECISIONS.index(
                              c.get("sys_decision", ""))
                          if c.get("sys_decision", "")
                          in D.SYS_DECISIONS else 0,
                          key=k + "sd" + stg)
        if st.button("Apply system decision", type="primary",
                     key=k + "sda" + stg):
            if sd == "PRE-APPROVED LOAN":
                D.update_client(c["id"], {"sys_decision": sd,
                                          "stage": "credit_call"},
                                now_str, sd + " - to Credit Team Call")
            elif sd == "ID FAIL":
                D.update_client(c["id"], {"sys_decision": sd,
                                          "stage": "docs"},
                                now_str, "ID FAIL - back to docs")
            elif sd in ("NEXT OF KIN - CASH OFFER",
                        "CASH OFFER - CREDIT"):
                D.update_client(c["id"], {"sys_decision": sd,
                                          "stage": "cash_offer"},
                                now_str, sd)
            else:
                D.update_client(c["id"], {"sys_decision": sd},
                                now_str, "System decision logged")
            st.rerun()

    elif stg == "credit_call":
        st.markdown('<div class="tw-lab" style="margin:6px 0 6px">'
                    'CREDIT TEAM CALL (human review)</div>',
                    unsafe_allow_html=True)
        cr = st.selectbox("credit team review", D.CREDIT_REVIEWS,
                          index=D.CREDIT_REVIEWS.index(
                              c.get("credit_review", ""))
                          if c.get("credit_review", "")
                          in D.CREDIT_REVIEWS else 0,
                          key=k + "cr" + stg)
        if st.button("Apply credit review", type="primary",
                     key=k + "cra" + stg):
            if cr == "DEPOSIT AND DELIVERY LOCATION":
                D.update_client(c["id"], {"credit_review": cr,
                                          "stage": "deposit"},
                                now_str, cr)
            elif cr == "CASH OFFER - CREDIT":
                D.update_client(c["id"], {"credit_review": cr,
                                          "stage": "cash_offer"},
                                now_str, cr)
            elif cr in ("PRE-APPROVED NOT READY",
                        "PRE-APPROVED NOT REACHED"):
                D.update_client(c["id"], {"credit_review": cr,
                                          "stage": "followup"},
                                now_str, cr + " - back to follow-ups")
            else:
                D.update_client(c["id"], {"credit_review": cr},
                                now_str, "Credit review logged")
            st.rerun()

    elif stg in ("deposit", "ready", "assigned", "out",
                 "failed_delivery"):
        st.markdown('<div class="tw-lab" style="margin:6px 0 6px">'
                    'DEPOSIT &amp; DELIVERY / PICK-UP</div>',
                    unsafe_allow_html=True)
        mode = st.selectbox("mode", D.DELIVERY_MODES,
                            index=D.DELIVERY_MODES.index(
                                c.get("delivery_mode", ""))
                            if c.get("delivery_mode", "")
                            in D.DELIVERY_MODES else 0,
                            key=k + "mode" + stg)
        status = st.selectbox("delivery status", D.DELIVERY_STATUSES,
                              index=D.DELIVERY_STATUSES.index(
                                  c.get("delivery_status", ""))
                              if c.get("delivery_status", "")
                              in D.DELIVERY_STATUSES else 0,
                              key=k + "st" + stg)
        freason = ""
        if status == "failed":
            freason = st.text_input("failure reason",
                                    key=k + "fr" + stg)
        if st.button("Save delivery", type="primary",
                     key=k + "dv" + stg):
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
        rd = st.date_input("bring back to calls on", value=today,
                           key=k + "rd" + stg)
        if st.button("Reschedule to calls", key=k + "rs" + stg):
            D.update_client(c["id"], {"next_date": rd.isoformat(),
                                      "next_action": "Delivery follow-up",
                                      "stage": "deposit"},
                            now_str, "Rescheduled to calls on "
                            + rd.isoformat())
            st.rerun()

    elif stg == "delivered":
        st.markdown('<div class="tw-lab" style="margin:6px 0 6px">'
                    'OUTCOME</div>', unsafe_allow_html=True)
        t1, t2, t3 = st.columns(3)
        with t1:
            if st.button("Mark PAID", key=k + "paid" + stg,
                         disabled=bool(c.get("paid"))):
                D.update_client(c["id"], {"paid": True,
                                          "paid_date": today.isoformat(),
                                          "stage": "paid"},
                                now_str, "Client PAID - deal closed")
                st.rerun()
        with t2:
            if st.button("Declined", key=k + "dec" + stg):
                D.update_client(c["id"], {"stage": "declined"},
                                now_str, "Declined at delivery")
                st.rerun()
        with t3:
            ro = st.selectbox("return outcome",
                              ["RETURNED", "RETURNED & EXCHANGED"],
                              key=k + "ro" + stg)
            if st.button("Return", key=k + "ret" + stg):
                D.update_client(c["id"], {"returned": True,
                                          "returned_date":
                                          today.isoformat(),
                                          "return_outcome": ro,
                                          "stage": "returned"
                                          if ro == "RETURNED"
                                          else "exchanged"},
                                now_str, ro)
                st.rerun()

    elif stg == "cash_offer":
        st.markdown('<div class="tw-lab" style="margin:6px 0 6px">'
                    'CASH OFFER - rejected to cash</div>',
                    unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Bring back to pipeline", key=k + "bb" + stg):
                D.update_client(c["id"], {"stage": "followup"},
                                now_str, "Brought back from cash offer")
                st.rerun()
        with b2:
            if st.button("Mark PAID (cash)", key=k + "cp" + stg,
                         disabled=bool(c.get("paid"))):
                D.update_client(c["id"], {"paid": True,
                                          "paid_date": today.isoformat(),
                                          "stage": "paid"},
                                now_str, "Paid cash - deal closed")
                st.rerun()


def _journey_desk(ctx):
    clients = ctx["clients"]
    if not clients:
        st.caption("No clients yet - log a lead above.")
        return
    st.markdown('<div class="tw-lab" style="margin:4px 0 8px">'
                'CLIENT JOURNEY DESK - click a stage tile to move the '
                'client; every step saves and you can continue later'
                '</div>',
                unsafe_allow_html=True)

    # ID-based selectbox: adding a lead never shifts your selection
    id_map = {c["id"]: c for c in clients}
    id_list = [c["id"] for c in clients]
    name_map = {}
    for c in clients:
        name_map[c["id"]] = (str(c.get("name", "?")) + "  ·  "
                             + D.stage_label(c.get("stage", "new"), "?"))

    if "jd_sel_id" not in st.session_state:
        st.session_state["jd_sel_id"] = id_list[0] if id_list else ""
    sel_id = st.session_state["jd_sel_id"]
    if sel_id not in id_map and id_list:
        sel_id = id_list[0]
        st.session_state["jd_sel_id"] = sel_id

    chosen = st.selectbox("client", id_list,
                          format_func=lambda cid: name_map.get(cid, cid),
                          index=id_list.index(sel_id)
                          if sel_id in id_list else 0,
                          key="jd_sel_id")
    c = id_map.get(chosen)
    if c is None:
        st.caption("Select a client above.")
        return

    k = "jd" + c["id"]
    st.markdown(UI.badge(D.stage_label(c.get("stage", "new"), "?"),
                         D.stage_color(c.get("stage", "new")))
                + "   " + UI.badge(c.get("heat", "Warm"), "#F5B544"),
                unsafe_allow_html=True)
    _journey_map(c, ctx, k)
    _stage_actions(c, ctx, k)
    st.markdown("<div style='height:8px'></div>",
                unsafe_allow_html=True)
    _end_reopen(c, ctx, k)


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
