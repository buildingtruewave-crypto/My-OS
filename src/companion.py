"""PULSE companion - a presence that has read your life.

Three layers, one context packet:
  * build_packet() reads your recent journal / spirit / sales / mood / clients /
    tasks / habits / weight, and - ONLY when allow_money is True (i.e. inside
    the locked Archive) - your pantry / runway / emergency / bills / commissions.
  * A deterministic voice per page composes 2-4 sentences grounded in that
    packet (never empty, never invented, notices absence).
  * If an OpenAI-compatible key is present in st.secrets, a strictly-grounded
    LLM writes the message and answers free questions; otherwise the
    deterministic voice carries the day. LLM results are cached 10 minutes.

Privacy: money facts enter the packet only on the Archive page, so the
companion can never leak balances on a public page. The whole panel is
wrapped so a failure never breaks the host page.
"""
from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

import streamlit as st

from . import data as D
from . import util as U

_MEM = Path(__file__).resolve().parent.parent / "data" / "companion.json"
LOW = {"drained", "flat"}
_MOOD_SCORE = {"drained": 0, "flat": 1, "steady": 2, "sharp": 3, "on fire": 4}

VOICE_META = {
    "morning": ("Morning", "#4C8DFF"),
    "sales": ("TrueWave", "#2DD4BF"),
    "spirit": ("Spirit", "#D946EF"),
    "journal": ("Journal", "#8B7CFF"),
    "body": ("Body", "#34D399"),
    "focus": ("Focus", "#8B7CFF"),
    "review": ("Review", "#F5B544"),
    "money": ("Vault", "#34D399"),
    "quiet": ("Companion", "#8893AB"),
}

_STYLE = (
    "<style>"
    "@keyframes pl_breathe{0%,100%{transform:scale(1);opacity:1}"
    "50%{transform:scale(1.4);opacity:.5}}"
    ".plc{position:relative;overflow:hidden;margin:14px 0 4px;"
    "padding:15px 18px 16px 20px;border:1px solid var(--hair,#1C2740);"
    "border-radius:14px;background:linear-gradient(180deg,"
    "rgba(18,26,43,.9),rgba(14,20,34,.92));"
    "box-shadow:0 10px 30px -22px rgba(0,0,0,.9);"
    "transition:transform .2s,border-color .2s,box-shadow .2s;"
    "animation:tw-rise .5s cubic-bezier(.2,.7,.2,1) both;}"
    ".plc:hover{transform:translateY(-2px);border-color:var(--plc);"
    "box-shadow:0 16px 36px -20px rgba(0,0,0,.95);}"
    ".plc-rail{position:absolute;left:0;top:0;bottom:0;width:3px;"
    "background:linear-gradient(180deg,var(--plc),transparent 85%);}"
    ".plc-head{display:flex;align-items:center;gap:9px;margin-bottom:9px;}"
    ".plc-dot{width:8px;height:8px;border-radius:50%;background:var(--plc);"
    "box-shadow:0 0 8px var(--plc);animation:pl_breathe 2.4s ease-in-out infinite;}"
    ".plc-name{font:700 11px/1 var(--mono,'JetBrains Mono',monospace);"
    "letter-spacing:.2em;text-transform:uppercase;color:var(--ink-2,#B6C0D4);}"
    ".plc-voice{font:700 10px/1 var(--mono,'JetBrains Mono',monospace);"
    "letter-spacing:.12em;text-transform:uppercase;color:var(--plc);}"
    ".plc-ai{font:700 8px/1 var(--mono,'JetBrains Mono',monospace);"
    "letter-spacing:.12em;text-transform:uppercase;color:#D946EF;"
    "border:1px solid rgba(217,70,239,.4);background:rgba(217,70,239,.12);"
    "border-radius:999px;padding:3px 7px;}"
    ".plc-msg{font:500 15px/1.62 var(--body,'Manrope',sans-serif);"
    "color:var(--ink,#E8EDF7);font-style:italic;letter-spacing:-.005em;}"
    ".plc-facts{display:flex;flex-wrap:wrap;gap:6px;margin-top:11px;}"
    ".plc-chip{font:600 9px/1 var(--mono,'JetBrains Mono',monospace);"
    "letter-spacing:.06em;color:var(--mute-2,#8893AB);"
    "background:rgba(255,255,255,.035);border:1px solid var(--hair,#1C2740);"
    "border-radius:999px;padding:4px 9px;}"
    ".plc-ans{margin-top:8px;padding:11px 13px;border-radius:10px;"
    "border:1px solid var(--hair,#1C2740);background:rgba(255,255,255,.02);"
    "font:500 13.5px/1.55 var(--body,'Manrope',sans-serif);"
    "color:var(--ink-2,#B6C0D4);font-style:italic;}"
    "</style>"
)

_SYS = (
    "You are PULSE, a grounded companion for one person. You receive a "
    "CONTEXT block of verified facts about their recent life. Rules: "
    "(1) Use ONLY facts present in CONTEXT; never invent sales, feelings, "
    "verses, dates, clients or events. (2) Speak in second person, warmly "
    "and specifically, in 2 to 4 short sentences. (3) When you cite a "
    "number, quote or feeling, use the exact one from CONTEXT. (4) Match "
    "their current mood. (5) If the question touches money, balances, "
    "pantry or the emergency fund but CONTEXT has no money facts, reply "
    "that you keep finances private and they should ask you inside the "
    "Archive. (6) Do not ask a question back unless it is a single gentle "
    "offer. (7) No lists, no headers, no emojis."
)


def _e(s):
    return html.escape(str(s if s is not None else ""))


def _trim(s, n):
    s = (s or "").strip()
    return s[:n] + ("…" if len(s) > n else "")


def _g(k, d=None):
    try:
        v = st.session_state.get(k, d)
        return v if v is not None else d
    except Exception:
        return d


# ---- companion memory (anchor line) ----

def _mem():
    try:
        if _MEM.exists() and _MEM.stat().st_size > 0:
            return json.loads(_MEM.read_text())
    except Exception:
        pass
    return {}


def _save_mem(d):
    try:
        _MEM.parent.mkdir(parents=True, exist_ok=True)
        _MEM.write_text(json.dumps(d, default=str))
    except Exception:
        pass


def get_anchor():
    return (_mem().get("anchor") or "").strip()


def set_anchor(text):
    d = _mem()
    d["anchor"] = (text or "").strip()
    _save_mem(d)


# ---- small derived helpers ----

def _energy(e):
    if not e:
        return 0
    mins = float(e.get("minutes", 0) or 0)
    depth = int(e.get("depth", 0) or 0)
    acts = e.get("acts") or []
    felt = (e.get("felt") or "").strip()
    pres = 25.0 if (mins > 0 or felt or e.get("word") or acts) else 0.0
    m = min(mins / 60.0, 1.0) * 25.0
    d = (max(0, min(depth, 5)) / 5.0) * 25.0
    a = min(len(acts) / 3.0, 1.0) * 15.0
    r = min(len(felt) / 20.0, 1.0) * 10.0
    return int(max(0, min(100, round(pres + m + d + a + r))))


def _spirit_present(e):
    return bool(e) and bool(
        e.get("minutes") or e.get("word") or e.get("felt") or e.get("acts"))


def _streak_j(journal):
    today = U.today_local()
    s = 0
    for o in range(0, 400):
        if (today - dt.timedelta(days=o)).isoformat() in journal:
            s += 1
        else:
            break
    return s


def _streak_spirit(spirit):
    today = U.today_local()
    s = 0
    for o in range(0, 400):
        if _spirit_present(spirit.get((today - dt.timedelta(days=o)).isoformat())):
            s += 1
        else:
            break
    return s


def _spirit_health(spirit):
    today = U.today_local()
    tot = n = 0
    for o in range(29, -1, -1):
        e = spirit.get((today - dt.timedelta(days=o)).isoformat())
        if e is not None:
            tot += _energy(e)
            n += 1
    return int(round(tot / n)) if n else 0


def _trend_word(moods):
    vals = [_MOOD_SCORE.get(m, 2) for m in (moods or []) if m]
    if len(vals) < 2:
        return None
    d = vals[-1] - vals[0]
    return "lifting" if d >= 1 else ("heavy" if d <= -1 else "steady")


def _consistency(habits, log, n):
    if not habits:
        return 0
    today = U.today_local()
    tot = 0.0
    for h in habits:
        s = log.get(h["id"], {})
        done = sum(1 for o in range(n)
                   if s.get((today - dt.timedelta(days=o)).isoformat()))
        tot += done / n * 100
    return int(round(tot / len(habits)))


# ---- the context packet ----

def _money_fields(vault, today):
    cash = sum(float(p.get("balance", 0)) for p in vault.get("positions", []))
    pan = vault.get("pantry") or {}
    bn = None
    for it in pan.get("items", []):
        if it.get("hidden"):
            continue
        daily = float(it.get("daily", 0) or 0)
        stock = float(it.get("stock", 0) or 0)
        if daily <= 0:
            continue
        raw = stock / daily
        age = 0
        chk = it.get("checked", "")
        if chk:
            try:
                age = max(0, (today - dt.date.fromisoformat(chk)).days)
            except Exception:
                age = 0
        aged = max(0.0, raw - age)
        if bn is None or aged < bn[0]:
            bn = (aged, it.get("name", "?"))
    pantry = ({"days": int(round(bn[0])), "name": bn[1]} if bn else None)
    r = vault.get("runway") or {}
    burn = float(r.get("monthly_burn", 0) or 0)
    runway = (cash / burn) if burn > 0 else None
    ebal = float((vault.get("emergency") or {}).get("balance", 0) or 0)
    months = int(r.get("emergency_months", 3) or 3)
    etarget = burn * months
    epct = int(max(0, min(100, ebal / etarget * 100))) if etarget > 0 else 0
    ti = today.isoformat()
    bo = sum(1 for b in vault.get("bills", [])
             if not b.get("paid") and b.get("due") and b["due"] < ti)
    f = vault.get("fun") or {}
    fr = max(0.0, float(f.get("budget", 0) or 0) - float(f.get("used", 0) or 0))
    sales = _g("sales", []) or []
    cdue = 0
    cpend = 0.0
    for s in sales:
        for i in s.get("inst", []):
            if i.get("paid"):
                continue
            cpend += float(i.get("amount", 0) or 0)
            if i.get("due") == ti:
                cdue += 1
    sealed = sum(1 for x in vault.get("funds", []) if x.get("sealed"))
    return dict(cash=cash, pantry_bottleneck=pantry, runway_months=runway,
                emergency_pct=epct, bills_overdue_n=bo, fun_remaining=fr,
                commissions_due=cdue, commissions_pending=cpend,
                sealed_n=sealed)


def build_packet(ctx, voice, allow_money):
    today = ctx["today"]
    ti = today.isoformat()
    hour = ctx["now_dt"].hour
    journal = _g("journal", {}) or {}
    spirit = _g("spiritual", {}) or {}
    sd = _g("sales_daily", {}) or {}
    clients = _g("clients", []) or []
    tasks = _g("tasks", []) or []
    habits = _g("habits", []) or []
    log = _g("habit_log", {}) or {}

    mood_today = (journal.get(ti) or {}).get("mood", "")
    moods = []
    for o in range(6, -1, -1):
        m = (journal.get((today - dt.timedelta(days=o)).isoformat())
             or {}).get("mood", "")
        if m:
            moods.append(m)

    rj = []
    for o in range(1, 8):
        e = journal.get((today - dt.timedelta(days=o)).isoformat())
        if e:
            rj.append(dict(e, date=(today - dt.timedelta(days=o)).isoformat()))
    last_journal = rj[0] if rj else None
    prev_journal = rj[2] if len(rj) > 2 else (rj[-1] if rj else None)

    rs = []
    for o in range(0, 8):
        e = spirit.get((today - dt.timedelta(days=o)).isoformat())
        if e:
            rs.append(dict(e, date=(today - dt.timedelta(days=o)).isoformat()))
    last_verse = None
    for e in rs:
        if (e.get("word") or "").strip():
            last_verse = {"date": e["date"],
                          "word": _trim(e.get("word"), 70),
                          "felt": _trim(e.get("felt"), 40)}
            break
    st_today = spirit.get(ti) or {}
    st_has = bool(st_today and (st_today.get("minutes") or st_today.get("word")
                                or st_today.get("felt")))

    yest = (today - dt.timedelta(days=1)).isoformat()
    sales_yest = int((sd.get(yest) or {}).get("sold", 0) or 0)
    best = None
    for o in range(0, 15):
        n = int((sd.get((today - dt.timedelta(days=o)).isoformat())
                 or {}).get("sold", 0) or 0)
        if best is None or n > best["n"]:
            best = {"date": (today - dt.timedelta(days=o)).isoformat(), "n": n}
    if best and best["n"] <= 0:
        best = None
    sales_week = sum(int((sd.get((today - dt.timedelta(days=o)).isoformat())
                          or {}).get("sold", 0) or 0) for o in range(7))

    term = set(D.terminal_ids())
    due = [c for c in clients if c.get("stage") not in term
           and c.get("next_date") == ti]
    over = [c for c in clients if c.get("stage") not in term
            and c.get("next_date") and c["next_date"] < ti]

    t_over = sum(1 for t in tasks if not t.get("done") and t.get("due")
                 and t["due"] < ti)
    t_due = sum(1 for t in tasks if not t.get("done") and t.get("due") == ti)

    hdone = sum(1 for h in habits if (log.get(h["id"]) or {}).get(ti))
    wid = None
    for h in habits:
        if h["name"].lower().startswith("workout"):
            wid = h["id"]
            break
    wstreak = 0
    if wid:
        s = log.get(wid, {})
        for o in range(0, 400):
            if s.get((today - dt.timedelta(days=o)).isoformat()):
                wstreak += 1
            else:
                break

    weights = _g("weights", []) or []
    wdelta = None
    if len(weights) >= 2:
        ws = sorted(weights, key=lambda w: w["date"])
        d = float(ws[-1]["kg"]) - float(ws[0]["kg"])
        wdelta = ("+" if d >= 0 else "") + format(d, ".1f") + " kg since first weigh-in"

    pkt = dict(
        today=ti, hour=hour, dow=today.weekday(),
        day_type=ctx.get("day_type", ""),
        mood_today=mood_today, mood_trend=moods,
        recent_journal=rj[:3], last_journal=last_journal,
        prev_journal=prev_journal,
        journal_today_has=bool(journal.get(ti)),
        journal_streak=_streak_j(journal),
        last_verse=last_verse,
        spirit_today_has=st_has,
        spirit_today_depth=int(st_today.get("depth", 0) or 0),
        spirit_today_word=_trim(st_today.get("word"), 70),
        spirit_streak=_streak_spirit(spirit),
        spirit_health=_spirit_health(spirit),
        sales_yesterday=sales_yest, sales_best=best, sales_week=sales_week,
        clients_due_n=len(due), clients_overdue_n=len(over),
        tasks_overdue=t_over, tasks_due=t_due,
        habits_done=hdone, habits_total=len(habits),
        workout_streak=wstreak, consistency7=_consistency(habits, log, 7),
        weight_delta_word=wdelta, anchor=get_anchor(),
    )
    if allow_money:
        pkt.update(_money_fields(_g("vault", {}) or {}, today))
    return pkt


# ---- deterministic voices ----

def _cap(s, f, ns, nf):
    return s[:ns], f[:nf]


def _v_morning(p):
    s, f = [], []
    h = p["hour"]
    g = "Morning" if h < 12 else ("Afternoon" if h < 17 else "Evening")
    m = p["mood_today"]
    if m in LOW:
        s.append(g + ", and the mood reads " + m + ". I'd keep the first hour small and kind.")
    elif m:
        s.append(g + " at " + m + " - let that lead the day.")
    else:
        s.append(g + ". The page is blank; one true move makes it real.")
    lv = p["last_verse"]
    if lv and (m in LOW or p["dow"] % 2 == 0):
        s.append("Carry this from " + lv["date"] + ": “" + lv["word"]
                 + "”. It held you when you wrote it.")
        f.append("verse " + lv["date"])
    if p["sales_yesterday"] > 0:
        s.append("Yesterday you closed " + str(p["sales_yesterday"])
                 + " - momentum you can't feel is still momentum.")
        f.append(str(p["sales_yesterday"]) + " sales yesterday")
    if p["clients_due_n"] > 0:
        n = p["clients_due_n"]
        s.append(str(n) + " " + ("person waits" if n == 1 else "people wait")
                 + " on a call today; open with the hottest.")
        f.append(str(n) + " due today")
    if p["habits_total"] and p["habits_done"] > 0:
        s.append(str(p["habits_done"]) + "/" + str(p["habits_total"])
                 + " habits already ticked - the wall is listening.")
        f.append("habits " + str(p["habits_done"]) + "/" + str(p["habits_total"]))
    tw = _trend_word(p["mood_trend"])
    if tw == "lifting":
        f.append("mood lifting")
    elif tw == "heavy":
        f.append("mood heavy - be gentle")
    s, f = _cap(s, f, 3, 4)
    if not s:
        s = ["A clean start. One honest thing today is the whole win."]
    return s, f


def _v_sales(p):
    s, f = [], []
    m = p["mood_today"]
    if m in LOW:
        s.append("I know it feels thin right now. Feelings lie; your log doesn't.")
        if p["sales_yesterday"] > 0:
            s.append("Yesterday you closed " + str(p["sales_yesterday"])
                     + ". That version of you showed up even when you didn't feel like it.")
        elif p["sales_best"]:
            s.append("Remember " + p["sales_best"]["date"] + " - "
                     + str(p["sales_best"]["n"]) + " in a day. You've carried harder days.")
        if p["last_verse"]:
            s.append("And hold this: “" + p["last_verse"]["word"] + "”.")
        f.append("mood " + m)
    else:
        s.append("You're in it. Keep the rhythm: post, call, log.")
        if p["sales_yesterday"] > 0:
            s.append("Yesterday: " + str(p["sales_yesterday"])
                     + " closed. Stack today on top of it.")
        if p["clients_due_n"] > 0:
            s.append(str(p["clients_due_n"]) + " follow-up"
                     + ("" if p["clients_due_n"] == 1 else "s")
                     + " due - that's revenue sitting in your phone.")
            f.append(str(p["sales_yesterday"]) + " yesterday")
    if p["clients_overdue_n"] > 0:
        s.append(str(p["clients_overdue_n"]) + " overdue call"
                 + ("" if p["clients_overdue_n"] == 1 else "s")
                 + " - clear the oldest first.")
        f.append(str(p["clients_overdue_n"]) + " overdue")
    if p["sales_best"]:
        f.append("best day " + str(p["sales_best"]["n"]))
    s, f = _cap(s, f, 3, 4)
    if not s:
        s = ["Log the next call the moment it ends. The pipeline feeds on speed."]
    return s, f


def _v_spirit(p):
    s, f = [], []
    if not p["spirit_today_has"]:
        s.append("You haven't sat with Him yet today.")
        if p["last_verse"]:
            s.append("A few days ago this landed: “" + p["last_verse"]["word"]
                     + "” - maybe that's the thread to pick up.")
        elif p["anchor"]:
            s.append("Come back to your anchor: “" + p["anchor"] + "”.")
        else:
            s.append("Even five silent minutes counts as showing up.")
    else:
        s.append("You're holding “" + (p["spirit_today_word"] or "the quiet")
                 + "” today at depth " + str(p["spirit_today_depth"]) + "/5.")
        if p["last_verse"] and p["last_verse"]["date"] != p["today"]:
            s.append("Last time you wrote it made you feel "
                     + (p["last_verse"]["felt"] or "held")
                     + ". Notice if that's true again.")
        if p["spirit_streak"] > 1:
            s.append(str(p["spirit_streak"])
                     + " days of showing up to Him. That's a life being built.")
        f.append("depth " + str(p["spirit_today_depth"]))
    if p["spirit_streak"] > 0:
        f.append("spirit streak " + str(p["spirit_streak"]))
    if p["last_verse"]:
        f.append("verse " + p["last_verse"]["date"])
    s, f = _cap(s, f, 3, 4)
    if not s:
        s = ["Be still a minute. The rest can wait."]
    return s, f


def _v_journal(p):
    s, f = [], []
    if not p["journal_today_has"]:
        s.append("No entry yet today.")
        if p["last_journal"]:
            lj = p["last_journal"]
            s.append("Yesterday you wrote: “"
                     + _trim(lj.get("happened") or lj.get("win"), 60)
                     + "”. Today deserves its own line.")
        else:
            s.append("One sentence is enough: what happened, what you learned, how you feel.")
    else:
        s.append("Today's page is open. When you write it, I'll remember it for the hard days.")
        if p["prev_journal"]:
            pj = p["prev_journal"]
            s.append("A few days ago you noted “"
                     + _trim(pj.get("lesson") or pj.get("win"), 55)
                     + "” - watch if today echoes it.")
    if p["mood_today"]:
        f.append("mood " + p["mood_today"])
    if p["journal_streak"]:
        f.append("journal streak " + str(p["journal_streak"]))
    s, f = _cap(s, f, 3, 3)
    if not s:
        s = ["The journal is where the days stop slipping. Write one true line."]
    return s, f


def _v_body(p):
    s, f = [], []
    if p["workout_streak"] > 0:
        s.append(str(p["workout_streak"])
                 + "-day movement streak - your body trusts you right now.")
    else:
        s.append("No movement streak running; 20 minutes tonight resets it.")
    if p["weight_delta_word"]:
        s.append("Scale says " + p["weight_delta_word"] + ". Trend, not a verdict.")
    if p["workout_streak"] > 0:
        f.append("workout streak " + str(p["workout_streak"]))
    if p["weight_delta_word"]:
        f.append("weight " + p["weight_delta_word"])
    s, f = _cap(s, f, 3, 3)
    if not s:
        s = ["Treat the body like the asset it is. Small, daily, unglamorous."]
    return s, f


def _v_focus(p):
    s, f = [], []
    if p["tasks_overdue"] > 0:
        s.append(str(p["tasks_overdue"]) + " task"
                 + ("" if p["tasks_overdue"] == 1 else "s")
                 + " past due - do the smallest one first to break the logjam.")
    elif p["tasks_due"] > 0:
        s.append(str(p["tasks_due"]) + " task"
                 + ("" if p["tasks_due"] == 1 else "s")
                 + " due today; protect one deep block for the hardest.")
    else:
        s.append("Nothing overdue. Use the quiet to build, not just to clear.")
    s.append("Phones down, one tab, 25 minutes. The compounding is invisible until it isn't.")
    if p["tasks_overdue"]:
        f.append(str(p["tasks_overdue"]) + " overdue")
    if p["tasks_due"]:
        f.append(str(p["tasks_due"]) + " due today")
    s, f = _cap(s, f, 3, 3)
    return s, f


def _v_review(p):
    s, f = [], []
    s.append("Week shape: consistency " + str(p["consistency7"]) + "%, "
             + str(p["sales_week"]) + " closed, spirit health "
             + str(p["spirit_health"]) + "%.")
    if p["weight_delta_word"]:
        s.append("Body: " + p["weight_delta_word"] + ".")
    s.append("The score follows the showing-up. Keep feeding the floor.")
    f += ["consistency " + str(p["consistency7"]) + "%",
          "sales wk " + str(p["sales_week"])]
    if p["spirit_health"]:
        f.append("spirit " + str(p["spirit_health"]) + "%")
    s, f = _cap(s, f, 4, 4)
    return s, f


def _v_money(p):
    s, f = [], []
    pb = p.get("pantry_bottleneck")
    if pb:
        s.append("Pantry: " + pb["name"] + " is at " + str(pb["days"])
                 + " days - that's your next shop window.")
        f.append(pb["name"] + " " + str(pb["days"]) + "d")
    if p.get("bills_overdue_n", 0) > 0:
        n = p["bills_overdue_n"]
        s.append(str(n) + " bill" + ("" if n == 1 else "s")
                 + " overdue; cover that before any fun top-up.")
        f.append(str(n) + " bill overdue")
    if p.get("runway_months") is not None:
        s.append("Cash runway " + format(p["runway_months"], ".1f")
                 + " months; emergency at " + str(p.get("emergency_pct", 0))
                 + "% of target.")
        f.append("runway " + format(p["runway_months"], ".1f") + "mo")
    if pb and pb["days"] <= 3 and p.get("bills_overdue_n", 0) > 0:
        s.append("Call: shop staples today, hold the fun top-up 48h, let HHO wait a day.")
    elif p.get("fun_remaining") is not None and p["fun_remaining"] < 500 and p.get("bills_overdue_n", 0) == 0:
        s.append("Fun is low but bills are clear - a small treat is earned, not stolen.")
    if p.get("commissions_due", 0) > 0:
        s.append(str(p["commissions_due"]) + " commission"
                 + ("" if p["commissions_due"] == 1 else "s")
                 + " due today - chase them; "
                 + str(int(p.get("commissions_pending", 0))) + " KSh pending.")
    s, f = _cap(s, f, 4, 4)
    if not s:
        s = ["Money is calm today. Use calm to plan, not to spend."]
    return s, f


def _v_quiet(p):
    s = ["This is where PULSE lives with you. Set an anchor line below; "
         "I'll lean on it whenever a day is heavy."]
    f = []
    if p.get("anchor"):
        f.append("anchor set")
    return s, f


_VOICES = {
    "morning": _v_morning, "sales": _v_sales, "spirit": _v_spirit,
    "journal": _v_journal, "body": _v_body, "focus": _v_focus,
    "review": _v_review, "money": _v_money, "quiet": _v_quiet,
}


def _deterministic(pkt, voice):
    fn = _VOICES.get(voice, _v_morning)
    return fn(pkt)


# ---- optional LLM layer ----

def _keyinfo():
    ak = None
    bu = ""
    model = "gpt-4o-mini"
    try:
        llm = st.secrets["llm"]
        ak = llm.get("api_key")
        bu = llm.get("base_url") or ""
        model = llm.get("model") or model
    except Exception:
        pass
    if not ak:
        try:
            ak = st.secrets["openai_api_key"]
        except Exception:
            ak = None
    if not ak:
        return None
    return ak, bu, (model or "gpt-4o-mini")


def _have_key():
    try:
        return _keyinfo() is not None
    except Exception:
        return False


@st.cache_data(ttl=600, show_spinner=False)
def _llm_call(api_key, base_url, model, system, user):
    try:
        import openai
    except Exception:
        return None
    try:
        kw = {"api_key": api_key}
        if base_url:
            kw["base_url"] = base_url
        client = openai.OpenAI(**kw)
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.7, max_tokens=200)
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return None


def _context_block(p, voice):
    L = []
    L.append("today " + p["today"] + " (" + str(p.get("day_type", "")) + ")")
    if p.get("mood_today"):
        L.append("mood today: " + p["mood_today"])
    tw = _trend_word(p.get("mood_trend"))
    if tw:
        L.append("mood trend 7d: " + tw)
    for e in p.get("recent_journal", []):
        L.append("journal " + e["date"] + ": mood " + str(e.get("mood", ""))
                 + "; happened: " + _trim(e.get("happened"), 80)
                 + "; win: " + _trim(e.get("win"), 60)
                 + "; lesson: " + _trim(e.get("lesson"), 60))
    lv = p.get("last_verse")
    if lv:
        L.append("last verse " + lv["date"] + ": “" + lv["word"]
                 + "” (felt: " + (lv["felt"] or "-") + ")")
    if p.get("spirit_today_has"):
        L.append("spirit today: depth " + str(p["spirit_today_depth"])
                 + "/5; word: " + (p.get("spirit_today_word") or "-"))
    if p.get("spirit_streak"):
        L.append("spirit streak: " + str(p["spirit_streak"]))
    L.append("sales yesterday: " + str(p.get("sales_yesterday", 0)))
    if p.get("sales_best"):
        L.append("best recent day: " + p["sales_best"]["date"] + " = "
                 + str(p["sales_best"]["n"]))
    L.append("sales this week: " + str(p.get("sales_week", 0)))
    L.append("clients due today: " + str(p.get("clients_due_n", 0))
             + "; overdue: " + str(p.get("clients_overdue_n", 0)))
    L.append("tasks due today: " + str(p.get("tasks_due", 0))
             + "; overdue: " + str(p.get("tasks_overdue", 0)))
    L.append("habits today: " + str(p.get("habits_done", 0)) + "/"
             + str(p.get("habits_total", 0))
             + "; consistency 7d: " + str(p.get("consistency7", 0)) + "%")
    if p.get("workout_streak"):
        L.append("workout streak: " + str(p["workout_streak"]))
    if p.get("weight_delta_word"):
        L.append("weight: " + p["weight_delta_word"])
    if p.get("pantry_bottleneck"):
        L.append("pantry bottleneck: " + p["pantry_bottleneck"]["name"]
                 + " = " + str(p["pantry_bottleneck"]["days"]) + " days")
    if p.get("runway_months") is not None:
        L.append("cash runway: " + format(p["runway_months"], ".1f") + " months")
    if "emergency_pct" in p:
        L.append("emergency fund: " + str(p["emergency_pct"]) + "% of target")
    if "bills_overdue_n" in p:
        L.append("bills overdue: " + str(p["bills_overdue_n"]))
    if p.get("fun_remaining") is not None:
        L.append("fun remaining: " + str(int(p["fun_remaining"])) + " KSh")
    if "commissions_due" in p:
        L.append("commissions due today: " + str(p["commissions_due"])
                 + "; pending: " + str(int(p.get("commissions_pending", 0))) + " KSh")
    return "\n".join(L)


def _llm(pkt, voice, user_q):
    ki = _keyinfo()
    if not ki:
        return None
    ak, bu, model = ki
    sysp = _SYS + "\n\nCONTEXT:\n" + _context_block(pkt, voice) + "\n\nMOOD: " \
        + (pkt.get("mood_today") or "-") + "\nPAGE VOICE: " + voice
    if pkt.get("anchor"):
        sysp += "\nANCHOR LINE: " + pkt["anchor"]
    return _llm_call(ak, bu, model, sysp, user_q)


_AUTO = {
    "morning": "Speak to them for this moment of the day, 2-3 sentences, grounded.",
    "sales": "Encourage them about their sales work right now, grounded in their numbers.",
    "spirit": "Speak to them about their time with God right now, grounded.",
    "journal": "Invite reflection on their day, grounded in what they logged.",
    "body": "Speak to them about their body and movement, grounded.",
    "focus": "Help them focus on what matters right now, grounded.",
    "review": "Give a brief grounded review of how the week is shaping.",
    "money": "Give grounded, practical money guidance for right now.",
    "quiet": "Offer a calm, grounded word.",
}


# ---- render ----

def _card_html(voice, message, facts, used_llm):
    label, color = VOICE_META.get(voice, ("Companion", "#8893AB"))
    msg = _e(message).replace("\n", "<br>")
    ai = '<span class="plc-ai">ai</span>' if used_llm else ""
    chips = ""
    if facts:
        chips = ('<div class="plc-facts">'
                 + "".join('<span class="plc-chip">' + _e(x) + '</span>'
                           for x in facts) + '</div>')
    return (_STYLE + '<div class="plc" style="--plc:' + color + '">'
            '<div class="plc-rail"></div>'
            '<div class="plc-head"><span class="plc-dot"></span>'
            '<span class="plc-name">PULSE</span>'
            '<span class="plc-voice">' + _e(label) + '</span>' + ai + '</div>'
            '<div class="plc-msg">' + msg + '</div>' + chips + '</div>')


def _offline_facts(pkt, voice):
    return _deterministic(pkt, voice)[1]


def _ask_widget(pkt, voice):
    with st.expander("Ask PULSE anything"):
        st.caption("Grounded in your logged life. With no API key it answers "
                   "from what it can see.")
        q = st.text_input("Ask", key="plc_ask_" + voice,
                          placeholder="e.g. should I top up fun this week?")
        if st.button("Ask", key="plc_go_" + voice):
            qq = (q or "").strip()
            if qq:
                ans = _llm(pkt, voice, qq)
                if ans:
                    st.markdown('<div class="plc-ans">'
                                + _e(ans).replace("\n", "<br>") + '</div>',
                                unsafe_allow_html=True)
                else:
                    seen = "; ".join(_offline_facts(pkt, voice)) or "your recent log"
                    st.markdown('<div class="plc-ans">I’m running offline, '
                                'so here’s what I can see for you: '
                                + _e(seen) + '.</div>',
                                unsafe_allow_html=True)


def _companion_settings():
    with st.expander("Companion settings"):
        st.caption("An anchor line is a verse or sentence PULSE leans on "
                   "when a day is heavy.")
        cur = get_anchor()
        anc = st.text_input("Your anchor line", value=cur, key="plc_anchor")
        if st.button("Save anchor", key="plc_anchor_save"):
            set_anchor(anc)
            st.success("Anchor saved.")
            st.rerun()
        st.markdown(
            "**Make PULSE speak with a real model (optional).** Add this to "
            "Streamlit Cloud → Settings → Secrets. Without it, PULSE still "
            "talks, grounded in your log:")
        st.code('[llm]\napi_key = "sk-..."\nmodel = "gpt-4o-mini"\n'
                '# base_url = "https://your-compatible-endpoint/v1"',
                language="toml")
        st.caption("The ask-anything box appears on every page once a key "
                   "is present. PULSE never sees your vault on public pages.")


def panel(ctx, voice="morning", allow_money=False, ask_box=True):
    try:
        if voice == "money" and not allow_money:
            voice = "review"
        pkt = build_packet(ctx, voice, allow_money)
        sents, facts = _deterministic(pkt, voice)
        msg = " ".join(sents)
        used = False
        if _have_key():
            lm = _llm(pkt, voice, _AUTO.get(voice, _AUTO["morning"]))
            if lm:
                msg = lm
                used = True
        st.markdown(_card_html(voice, msg, facts, used),
                    unsafe_allow_html=True)
        if voice == "quiet":
            _companion_settings()
        elif ask_box and _have_key():
            _ask_widget(pkt, voice)
    except Exception:
        try:
            st.markdown(_card_html(voice or "morning",
                                   "I’m here. (the companion hit a snag - "
                                   "your data is safe.)", [], False),
                        unsafe_allow_html=True)
        except Exception:
            pass
