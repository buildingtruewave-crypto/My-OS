"""PULSE companion - the voice that has read your life.

Three layers over one context packet:
  * build_packet() reads recent journal / spirit / sales / mood / clients /
    tasks / habits / weight, and - ONLY when allow_money is True (inside the
    locked Archive) - pantry / runway / emergency / bills / commissions.
  * A deterministic voice per page composes grounded sentences, now augmented
    by the brain: a retrieved memory, a longitudinal pattern, and learned
    feedback suppressions. It never invents, never leaks money on a public
    page, and notices absence.
  * If an OpenAI-compatible key is in st.secrets, a strictly-grounded LLM
    writes the message and answers free questions, fed retrieved memories +
    the operator's patterns + their own past complaints as constraints.

Every public function fails open. The whole panel is wrapped so a failure
never breaks the host page. No f-strings are used anywhere in this file.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import streamlit as st

from . import data as D
from . import util as U

try:
    from . import brain as _B
    _HAS_BRAIN = True
except Exception:
    _B = None
    _HAS_BRAIN = False

_MEM = Path(__file__).resolve().parent.parent / "data" / "companion.json"
LOW = set(("drained", "flat"))
_MOOD_SCORE = {"drained": 0, "flat": 1, "steady": 2, "sharp": 3,
               "on fire": 4}

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
    "50%{transform:scale(1.45);opacity:.45}}"
    ".plc{position:relative;overflow:hidden;margin:14px 0 4px;"
    "padding:15px 18px 16px 20px;border:1px solid var(--hair,#1C2740);"
    "border-radius:14px;background:linear-gradient(180deg,"
    "rgba(18,26,43,.92),rgba(14,20,34,.94));"
    "box-shadow:0 10px 30px -22px rgba(0,0,0,.9);"
    "transition:transform .22s,border-color .22s,box-shadow .22s;"
    "animation:tw-rise .5s cubic-bezier(.2,.7,.2,1) both;}"
    ".plc:hover{transform:translateY(-2px);border-color:var(--plc);"
    "box-shadow:0 18px 40px -20px rgba(0,0,0,.95);}"
    ".plc-rail{position:absolute;left:0;top:0;bottom:0;width:3px;"
    "background:linear-gradient(180deg,var(--plc),transparent 85%);}"
    ".plc-head{display:flex;align-items:center;gap:9px;margin-bottom:9px;"
    "flex-wrap:wrap;}"
    ".plc-dot{width:8px;height:8px;border-radius:50%;background:var(--plc);"
    "box-shadow:0 0 8px var(--plc);"
    "animation:pl_breathe 2.4s ease-in-out infinite;}"
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
    ".plc-fb{display:flex;gap:8px;align-items:center;margin-top:10px;}"
    ".plc-fb button{padding:4px 10px;font-size:12px;}"
    ".plc-ans{margin-top:8px;padding:11px 13px;border-radius:10px;"
    "border:1px solid var(--hair,#1C2740);background:rgba(255,255,255,.02);"
    "font:500 13.5px/1.55 var(--body,'Manrope',sans-serif);"
    "color:var(--ink-2,#B6C0D4);font-style:italic;}"
    "</style>"
)

_SYS = (
    "You are PULSE, a grounded companion for one person. You receive a "
    "CONTEXT block of verified facts, a RETRIEVED block of the person's own "
    "past words most relevant to now, a PATTERNS block of what you have "
    "learned about them over time, and a CONSTRAINTS block of how they have "
    "asked you to behave. Rules: (1) Use ONLY facts present in CONTEXT and "
    "RETRIEVED; never invent sales, feelings, verses, dates, clients or "
    "events. (2) Speak in second person, warmly and specifically, in 2 to 4 "
    "short sentences. (3) When you cite a number, quote or feeling, use the "
    "exact one given. (4) Match their current mood. (5) Obey every line in "
    "CONSTRAINTS without mentioning that you were told. (6) If the question "
    "touches money, balances, pantry or the emergency fund but CONTEXT has "
    "no money facts, reply that you keep finances private and they should "
    "ask inside the Archive. (7) Do not ask a question back unless it is a "
    "single gentle offer. (8) No lists, no headers, no emojis."
)

_AUTO = {
    "morning": "Speak to them for this moment of the day, grounded.",
    "sales": "Encourage their sales work right now, grounded in their numbers.",
    "spirit": "Speak to them about their time with God right now, grounded.",
    "journal": "Invite reflection on their day, grounded in what they logged.",
    "body": "Speak to them about their body and movement, grounded.",
    "focus": "Help them focus on what matters right now, grounded.",
    "review": "Give a brief grounded review of how the week is shaping.",
    "money": "Give grounded, practical money guidance for right now.",
    "quiet": "Offer a calm, grounded word.",
}

_DISLIKE_CHIPS = ["too preachy", "too long", "wrong vibe",
                  "not useful", "misread me"]


# ---------------------------------------------------------------------------
# tiny helpers
# ---------------------------------------------------------------------------

def _e(s):
    return html.escape(str(s if s is not None else ""))


def _trim(s, n):
    s = (s or "").strip()
    if len(s) > n:
        return s[:n] + "…"
    return s


def _g(k, d=None):
    try:
        v = st.session_state.get(k, d)
        if v is None:
            return d
        return v
    except Exception:
        return d


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


# ---------------------------------------------------------------------------
# derived helpers
# ---------------------------------------------------------------------------

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
        if (today - __import__("datetime").timedelta(days=o)).isoformat() in journal:
            s += 1
        else:
            break
    return s


def _streak_spirit(spirit):
    today = U.today_local()
    s = 0
    for o in range(0, 400):
        if _spirit_present(spirit.get(
                (today - __import__("datetime").timedelta(days=o)).isoformat())):
            s += 1
        else:
            break
    return s


def _spirit_health(spirit):
    today = U.today_local()
    tot = n = 0
    for o in range(29, -1, -1):
        e = spirit.get((today - __import__("datetime").timedelta(days=o)).isoformat())
        if e is not None:
            tot += _energy(e)
            n += 1
    if n:
        return int(round(tot / n))
    return 0


def _trend_word(moods):
    vals = [_MOOD_SCORE.get(m, 2) for m in (moods or []) if m]
    if len(vals) < 2:
        return None
    d = vals[-1] - vals[0]
    if d >= 1:
        return "lifting"
    if d <= -1:
        return "heavy"
    return "steady"


def _consistency(habits, log, n):
    if not habits:
        return 0
    today = U.today_local()
    tot = 0.0
    for h in habits:
        s = log.get(h["id"], {})
        done = 0
        for o in range(n):
            if s.get((today - __import__("datetime").timedelta(days=o)).isoformat()):
                done += 1
        tot += done / n * 100
    return int(round(tot / len(habits)))


# ---------------------------------------------------------------------------
# brain access (all guarded)
# ---------------------------------------------------------------------------

def _stores(ctx, allow_money):
    s = {
        "journal": _g("journal", {}) or {},
        "spiritual": _g("spiritual", {}) or {},
        "clients": _g("clients", []) or [],
        "income": _g("income", []) or [],
        "sales": _g("sales", []) or [],
    }
    if allow_money:
        s["vault"] = _g("vault", {}) or {}
    return s


def _get_index(ctx, allow_money):
    if not _HAS_BRAIN:
        return None
    try:
        return _B.refresh_index(_stores(ctx, True))
    except Exception:
        return None


def _get_feedback():
    if not _HAS_BRAIN:
        return []
    try:
        return _B.load_feedback()
    except Exception:
        return []


def _get_reflection(ctx):
    if not _HAS_BRAIN:
        return {}
    try:
        return _B.reflect(_stores(ctx, True))
    except Exception:
        return {}


def _search(idx, fb, query, allow_money, mood, k=3):
    if not _HAS_BRAIN or idx is None:
        return []
    try:
        return _B.search(idx, query, k=k, allow_money=allow_money,
                         mood=mood, fb=fb)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# context packet
# ---------------------------------------------------------------------------

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
                age = max(0, (today - __import__("datetime").date.fromisoformat(chk)).days)
            except Exception:
                age = 0
        aged = max(0.0, raw - age)
        if bn is None or aged < bn[0]:
            bn = (aged, it.get("name", "?"))
    pantry = None
    if bn is not None:
        pantry = {"days": int(round(bn[0])), "name": bn[1]}
    r = vault.get("runway") or {}
    burn = float(r.get("monthly_burn", 0) or 0)
    runway = None
    if burn > 0:
        runway = cash / burn
    ebal = float((vault.get("emergency") or {}).get("balance", 0) or 0)
    months = int(r.get("emergency_months", 3) or 3)
    etarget = burn * months
    epct = 0
    if etarget > 0:
        epct = int(max(0, min(100, ebal / etarget * 100)))
    ti = today.isoformat()
    bo = 0
    for b in vault.get("bills", []):
        if not b.get("paid") and b.get("due") and b["due"] < ti:
            bo += 1
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
    sealed = 0
    for x in vault.get("funds", []):
        if x.get("sealed"):
            sealed += 1
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
        m = (journal.get(
            (today - __import__("datetime").timedelta(days=o)).isoformat())
             or {}).get("mood", "")
        if m:
            moods.append(m)

    rj = []
    for o in range(1, 8):
        e = journal.get((today - __import__("datetime").timedelta(days=o)).isoformat())
        if e:
            e2 = dict(e)
            e2["date"] = (today - __import__("datetime").timedelta(days=o)).isoformat()
            rj.append(e2)
    last_journal = rj[0] if rj else None
    prev_journal = None
    if len(rj) > 2:
        prev_journal = rj[2]
    elif rj:
        prev_journal = rj[-1]

    rs = []
    for o in range(0, 8):
        e = spirit.get((today - __import__("datetime").timedelta(days=o)).isoformat())
        if e:
            e2 = dict(e)
            e2["date"] = (today - __import__("datetime").timedelta(days=o)).isoformat()
            rs.append(e2)
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

    yest = (today - __import__("datetime").timedelta(days=1)).isoformat()
    sales_yest = int((sd.get(yest) or {}).get("sold", 0) or 0)
    best = None
    for o in range(0, 15):
        n = int((sd.get((today - __import__("datetime").timedelta(days=o)).isoformat())
                 or {}).get("sold", 0) or 0)
        if best is None or n > best["n"]:
            best = {"date": (today - __import__("datetime").timedelta(days=o)).isoformat(),
                    "n": n}
    if best and best["n"] <= 0:
        best = None
    sales_week = 0
    for o in range(7):
        sales_week += int((sd.get(
            (today - __import__("datetime").timedelta(days=o)).isoformat())
            or {}).get("sold", 0) or 0)

    term = set(D.terminal_ids())
    due = [c for c in clients if c.get("stage") not in term
           and c.get("next_date") == ti]
    over = [c for c in clients if c.get("stage") not in term
            and c.get("next_date") and c["next_date"] < ti]

    t_over = 0
    t_due = 0
    for t in tasks:
        if t.get("done"):
            continue
        if t.get("due") and t["due"] < ti:
            t_over += 1
        if t.get("due") == ti:
            t_due += 1

    hdone = 0
    for h in habits:
        if (log.get(h["id"]) or {}).get(ti):
            hdone += 1
    wid = None
    for h in habits:
        if h["name"].lower().startswith("workout"):
            wid = h["id"]
            break
    wstreak = 0
    if wid:
        s = log.get(wid, {})
        for o in range(0, 400):
            if s.get((today - __import__("datetime").timedelta(days=o)).isoformat()):
                wstreak += 1
            else:
                break

    weights = _g("weights", []) or []
    wdelta = None
    if len(weights) >= 2:
        ws = sorted(weights, key=lambda w: w["date"])
        d = float(ws[-1]["kg"]) - float(ws[0]["kg"])
        wdelta = ("+" if d >= 0 else "") + format(d, ".1f") + " kg since first weigh-in"

    mb = _B.mood_band(mood_today) if _HAS_BRAIN else "none"
    pkt = dict(
        today=ti, hour=hour, dow=today.weekday(),
        day_type=ctx.get("day_type", ""), page=voice, mood_band=mb,
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


# ---------------------------------------------------------------------------
# retrieval weaving + augmentation
# ---------------------------------------------------------------------------

def _weave_memory(mem, voice):
    src = mem.get("src", "")
    date = mem.get("date", "")
    text = _trim(mem.get("text", ""), 70)
    if src == "spirit":
        return ("A few days ago, on " + date + ", you held this close: '"
                + text + "'.", "quoted_verse")
    if src == "journal":
        return ("On " + date + " you wrote '" + text
                + "' - that version of you knew something worth keeping.",
                "quoted_memory")
    if src == "client":
        nm = (mem.get("meta") or {}).get("name", "a client")
        return ("Remember " + nm + " on " + date + ": '" + text
                + "'. That thread is still yours to pull.",
                "quoted_memory")
    if src in ("sale", "income"):
        return ("On " + date + " the log shows '" + text
                + "' - proof the work compounds even on thin days.",
                "quoted_memory")
    return ("On " + date + " you noted '" + text + "'.", "quoted_memory")


def _auto_query(voice, pkt):
    mood = pkt.get("mood_today", "")
    if voice == "sales":
        if mood in LOW:
            return "flat morning sales win comeback"
        return "sales follow up close momentum"
    if voice == "spirit":
        return "verse god held peace feeling"
    if voice == "journal":
        return "lesson win reflection feeling"
    if voice == "money":
        return "money bill pantry runway decision"
    if voice == "body":
        return "workout movement body streak"
    if voice == "focus":
        return "task focus deep work priority"
    if voice == "review":
        return "week pattern progress"
    return "morning start grounded today"


def _augment(pkt, tagged, base_facts, idx, fb, refl, allow_money):
    mb = pkt.get("mood_band", "none")
    page = pkt.get("page", "morning")
    out = []
    feats = set()
    facts = list(base_facts)
    for text, feat in tagged:
        if feat and _HAS_BRAIN and _B.is_suppressed(fb, mb, page, feat):
            continue
        if feat:
            feats.add(feat)
        out.append(text)
    if _HAS_BRAIN and not _B.is_suppressed(fb, mb, page, "quoted_memory"):
        docs = _search(idx, fb, _auto_query(page, pkt), allow_money,
                       pkt.get("mood_today"), k=2)
        if docs:
            sent, mf = _weave_memory(docs[0], page)
            if not _B.is_suppressed(fb, mb, page, mf):
                out.append(sent)
                feats.add(mf)
                facts.append("memory " + str(docs[0].get("date", "")))
    if _HAS_BRAIN and not _B.is_suppressed(fb, mb, page, "pattern_cited"):
        pat = _B.top_pattern(refl, page, mb)
        if pat:
            out.append(pat)
            feats.add("pattern_cited")
            facts.append("pattern")
    return out, facts, feats


# ---------------------------------------------------------------------------
# deterministic voices (each returns tagged sentences + facts)
# ---------------------------------------------------------------------------

def _cap_tagged(tagged, n):
    return tagged[:n]


def _v_morning(p):
    t = []
    f = []
    h = p["hour"]
    if h < 12:
        g = "Morning"
    elif h < 17:
        g = "Afternoon"
    else:
        g = "Evening"
    m = p["mood_today"]
    if m in LOW:
        t.append([g + ", and the mood reads " + m
                  + ". I'd keep the first hour small and kind.", "pep_talk"])
    elif m:
        t.append([g + " at " + m + " - let that lead the day.", None])
    else:
        t.append([g + ". The page is blank; one true move makes it real.", None])
    lv = p["last_verse"]
    if lv and (m in LOW or p["dow"] % 2 == 0):
        t.append(["Carry this from " + lv["date"] + ": “" + lv["word"]
                  + "”. It held you when you wrote it.", "quoted_verse"])
        f.append("verse " + lv["date"])
    if p["sales_yesterday"] > 0:
        t.append(["Yesterday you closed " + str(p["sales_yesterday"])
                  + " - momentum you can't feel is still momentum.", "pep_talk"])
        f.append(str(p["sales_yesterday"]) + " sales yesterday")
    if p["clients_due_n"] > 0:
        n = p["clients_due_n"]
        word = "person waits" if n == 1 else "people wait"
        t.append([str(n) + " " + word
                  + " on a call today; open with the hottest.", None])
        f.append(str(n) + " due today")
    if p["habits_total"] and p["habits_done"] > 0:
        t.append([str(p["habits_done"]) + "/" + str(p["habits_total"])
                  + " habits already ticked - the wall is listening.", None])
        f.append("habits " + str(p["habits_done"]) + "/" + str(p["habits_total"]))
    tw = _trend_word(p["mood_trend"])
    if tw == "lifting":
        f.append("mood lifting")
    elif tw == "heavy":
        f.append("mood heavy - be gentle")
    t = _cap_tagged(t, 3)
    if not t:
        t = [["A clean start. One honest thing today is the whole win.", None]]
    return t, f


def _v_sales(p):
    t = []
    f = []
    m = p["mood_today"]
    if m in LOW:
        t.append(["I know it feels thin right now. Feelings lie; your log doesn't.", "pep_talk"])
        if p["sales_yesterday"] > 0:
            t.append(["Yesterday you closed " + str(p["sales_yesterday"])
                      + ". That version of you showed up even when you didn't feel like it.", "pep_talk"])
        elif p["sales_best"]:
            t.append(["Remember " + p["sales_best"]["date"] + " - "
                      + str(p["sales_best"]["n"])
                      + " in a day. You've carried harder days.", "pep_talk"])
        if p["last_verse"]:
            t.append(["And hold this: “" + p["last_verse"]["word"] + "”.", "quoted_verse"])
        f.append("mood " + m)
    else:
        t.append(["You're in it. Keep the rhythm: post, call, log.", None])
        if p["sales_yesterday"] > 0:
            t.append(["Yesterday: " + str(p["sales_yesterday"])
                      + " closed. Stack today on top of it.", None])
            f.append(str(p["sales_yesterday"]) + " yesterday")
        if p["clients_due_n"] > 0:
            n = p["clients_due_n"]
            suf = "" if n == 1 else "s"
            t.append([str(n) + " follow-up" + suf
                      + " due - that's revenue sitting in your phone.", None])
    if p["clients_overdue_n"] > 0:
        n = p["clients_overdue_n"]
        suf = "" if n == 1 else "s"
        t.append([str(n) + " overdue call" + suf
                  + " - clear the oldest first.", None])
        f.append(str(n) + " overdue")
    if p["sales_best"]:
        f.append("best day " + str(p["sales_best"]["n"]))
    t = _cap_tagged(t, 3)
    if not t:
        t = [["Log the next call the moment it ends. The pipeline feeds on speed.", None]]
    return t, f


def _v_spirit(p):
    t = []
    f = []
    if not p["spirit_today_has"]:
        t.append(["You haven't sat with Him yet today.", None])
        if p["last_verse"]:
            t.append(["A few days ago this landed: “" + p["last_verse"]["word"]
                      + "” - maybe that's the thread to pick up.", "quoted_verse"])
        elif p["anchor"]:
            t.append(["Come back to your anchor: “" + p["anchor"] + "”.", "quoted_verse"])
        else:
            t.append(["Even five silent minutes counts as showing up.", None])
    else:
        word = p["spirit_today_word"] or "the quiet"
        t.append(["You're holding “" + word + "” today at depth "
                  + str(p["spirit_today_depth"]) + "/5.", None])
        if p["last_verse"] and p["last_verse"]["date"] != p["today"]:
            felt = p["last_verse"]["felt"] or "held"
            t.append(["Last time you wrote it made you feel " + felt
                      + ". Notice if that's true again.", "quoted_verse"])
        if p["spirit_streak"] > 1:
            t.append([str(p["spirit_streak"])
                      + " days of showing up to Him. That's a life being built.", None])
        f.append("depth " + str(p["spirit_today_depth"]))
    if p["spirit_streak"] > 0:
        f.append("spirit streak " + str(p["spirit_streak"]))
    if p["last_verse"]:
        f.append("verse " + p["last_verse"]["date"])
    t = _cap_tagged(t, 3)
    if not t:
        t = [["Be still a minute. The rest can wait.", None]]
    return t, f


def _v_journal(p):
    t = []
    f = []
    if not p["journal_today_has"]:
        t.append(["No entry yet today.", None])
        if p["last_journal"]:
            lj = p["last_journal"]
            snip = _trim(lj.get("happened") or lj.get("win"), 60)
            t.append(["Yesterday you wrote: “" + snip
                      + "”. Today deserves its own line.", "quoted_memory"])
        else:
            t.append(["One sentence is enough: what happened, what you learned, how you feel.", None])
    else:
        t.append(["Today's page is open. When you write it, I'll remember it for the hard days.", None])
        if p["prev_journal"]:
            pj = p["prev_journal"]
            snip = _trim(pj.get("lesson") or pj.get("win"), 55)
            t.append(["A few days ago you noted “" + snip
                      + "” - watch if today echoes it.", "quoted_memory"])
    if p["mood_today"]:
        f.append("mood " + p["mood_today"])
    if p["journal_streak"]:
        f.append("journal streak " + str(p["journal_streak"]))
    t = _cap_tagged(t, 3)
    if not t:
        t = [["The journal is where the days stop slipping. Write one true line.", None]]
    return t, f


def _v_body(p):
    t = []
    f = []
    if p["workout_streak"] > 0:
        t.append([str(p["workout_streak"])
                  + "-day movement streak - your body trusts you right now.", None])
    else:
        t.append(["No movement streak running; 20 minutes tonight resets it.", None])
    if p["weight_delta_word"]:
        t.append(["Scale says " + p["weight_delta_word"] + ". Trend, not a verdict.", None])
    if p["workout_streak"] > 0:
        f.append("workout streak " + str(p["workout_streak"]))
    if p["weight_delta_word"]:
        f.append("weight " + p["weight_delta_word"])
    t = _cap_tagged(t, 3)
    if not t:
        t = [["Treat the body like the asset it is. Small, daily, unglamorous.", None]]
    return t, f


def _v_focus(p):
    t = []
    f = []
    if p["tasks_overdue"] > 0:
        n = p["tasks_overdue"]
        suf = "" if n == 1 else "s"
        t.append([str(n) + " task" + suf
                  + " past due - do the smallest one first to break the logjam.", None])
    elif p["tasks_due"] > 0:
        n = p["tasks_due"]
        suf = "" if n == 1 else "s"
        t.append([str(n) + " task" + suf
                  + " due today; protect one deep block for the hardest.", None])
    else:
        t.append(["Nothing overdue. Use the quiet to build, not just to clear.", None])
    t.append(["Phones down, one tab, 25 minutes. The compounding is invisible until it isn't.", None])
    if p["tasks_overdue"]:
        f.append(str(p["tasks_overdue"]) + " overdue")
    if p["tasks_due"]:
        f.append(str(p["tasks_due"]) + " due today")
    t = _cap_tagged(t, 3)
    return t, f


def _v_review(p):
    t = []
    f = []
    t.append(["Week shape: consistency " + str(p["consistency7"])
              + "%, " + str(p["sales_week"]) + " closed, spirit health "
              + str(p["spirit_health"]) + "%.", None])
    if p["weight_delta_word"]:
        t.append(["Body: " + p["weight_delta_word"] + ".", None])
    t.append(["The score follows the showing-up. Keep feeding the floor.", None])
    f.append("consistency " + str(p["consistency7"]) + "%")
    f.append("sales wk " + str(p["sales_week"]))
    if p["spirit_health"]:
        f.append("spirit " + str(p["spirit_health"]) + "%")
    t = _cap_tagged(t, 4)
    return t, f


def _v_money(p):
    t = []
    f = []
    pb = p.get("pantry_bottleneck")
    if pb:
        t.append(["Pantry: " + str(pb["name"]) + " is at " + str(pb["days"])
                  + " days - that's your next shop window.", "money_advice"])
        f.append(str(pb["name"]) + " " + str(pb["days"]) + "d")
    if p.get("bills_overdue_n", 0) > 0:
        n = p["bills_overdue_n"]
        suf = "" if n == 1 else "s"
        t.append([str(n) + " bill" + suf
                  + " overdue; cover that before any fun top-up.", "money_advice"])
        f.append(str(n) + " bill overdue")
    if p.get("runway_months") is not None:
        t.append(["Cash runway " + format(p["runway_months"], ".1f")
                  + " months; emergency at " + str(p.get("emergency_pct", 0))
                  + "% of target.", "money_advice"])
        f.append("runway " + format(p["runway_months"], ".1f") + "mo")
    if pb and pb["days"] <= 3 and p.get("bills_overdue_n", 0) > 0:
        t.append(["Call: shop staples today, hold the fun top-up 48h, let HHO wait a day.", "money_advice"])
    elif p.get("fun_remaining") is not None and p["fun_remaining"] < 500 and p.get("bills_overdue_n", 0) == 0:
        t.append(["Fun is low but bills are clear - a small treat is earned, not stolen.", "money_advice"])
    if p.get("commissions_due", 0) > 0:
        n = p["commissions_due"]
        suf = "" if n == 1 else "s"
        t.append([str(n) + " commission" + suf
                  + " due today - chase them; "
                  + str(int(p.get("commissions_pending", 0)))
                  + " KSh pending.", "money_advice"])
    t = _cap_tagged(t, 4)
    if not t:
        t = [["Money is calm today. Use calm to plan, not to spend.", "money_advice"]]
    return t, f


def _v_quiet(p):
    t = [["This is where PULSE lives with you. Set an anchor line below; "
          "I'll lean on it whenever a day is heavy.", None]]
    f = []
    if p.get("anchor"):
        f.append("anchor set")
    return t, f


_VOICES = {
    "morning": _v_morning, "sales": _v_sales, "spirit": _v_spirit,
    "journal": _v_journal, "body": _v_body, "focus": _v_focus,
    "review": _v_review, "money": _v_money, "quiet": _v_quiet,
}


def _deterministic(pkt, voice, idx, fb, refl, allow_money):
    fn = _VOICES.get(voice, _v_morning)
    tagged, base_facts = fn(pkt)
    sents, facts, feats = _augment(pkt, tagged, base_facts, idx, fb,
                                   refl, allow_money)
    if not sents:
        sents = ["I'm here. (the voice came back empty - your data is safe.)"]
        feats = set()
    return sents, facts, feats


# ---------------------------------------------------------------------------
# optional LLM layer
# ---------------------------------------------------------------------------

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
            temperature=0.7, max_tokens=220)
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return None


def _retrieved_block(idx, fb, pkt, allow_money, k=4):
    if not _HAS_BRAIN or idx is None:
        return ""
    docs = _search(idx, fb, _auto_query(pkt.get("page", "morning"), pkt),
                   allow_money, pkt.get("mood_today"), k=k)
    if not docs:
        return ""
    lines = []
    for d in docs:
        lines.append("- [" + str(d.get("src", "")) + " "
                     + str(d.get("date", "")) + "] "
                     + str(d.get("text", "")))
    return "\n".join(lines)


def _patterns_block(refl, voice, mb):
    if not refl:
        return ""
    out = []
    if refl.get("recurring_lessons"):
        out.append("recurring lesson: " + str(refl["recurring_lessons"][0]))
    if refl.get("top_wins"):
        out.append("what they keep winning at: " + ", ".join(refl["top_wins"]))
    if refl.get("energy_sources"):
        a, e = refl["energy_sources"][0]
        out.append("energy comes from: " + str(a) + " (" + str(e) + "/100)")
    if refl.get("low_streak", 0) >= 2:
        out.append("currently " + str(refl["low_streak"]) + " heavy days in a row")
    if refl.get("promise_rate") is not None:
        out.append("promise-keeping rate: " + str(refl["promise_rate"]) + "%")
    if refl.get("bill_on_time_rate") is not None:
        out.append("bills on time: " + str(refl["bill_on_time_rate"]) + "%")
    return "\n".join(out)


def _constraints_block(fb, mb, page):
    out = []
    if _HAS_BRAIN:
        sups = _B.learned_suppressions(fb, [page], [mb])
        for s in sups:
            out.append("Do not use the move '" + str(s["feature"])
                       + "' in this state; the person disliked it before.")
        for note in _B.complaint_notes(fb, mb, page, limit=2):
            out.append("The person previously said, in a state like this: '"
                       + note + "'.")
    return "\n".join(out)


def _llm_message(pkt, voice, idx, fb, refl, allow_money):
    ki = _keyinfo()
    if not ki:
        return None
    ak, bu, model = ki
    parts = [_SYS, "", "CONTEXT:"]
    parts.append("today " + str(pkt["today"]) + " ("
                 + str(pkt.get("day_type", "")) + ")")
    if pkt.get("mood_today"):
        parts.append("mood today: " + str(pkt["mood_today"]))
    tw = _trend_word(pkt.get("mood_trend"))
    if tw:
        parts.append("mood trend 7d: " + tw)
    for e in pkt.get("recent_journal", []):
        parts.append("journal " + str(e.get("date", "")) + ": mood "
                     + str(e.get("mood", "")) + "; happened: "
                     + _trim(e.get("happened"), 80) + "; win: "
                     + _trim(e.get("win"), 60) + "; lesson: "
                     + _trim(e.get("lesson"), 60))
    lv = pkt.get("last_verse")
    if lv:
        parts.append("last verse " + str(lv["date"]) + ": “"
                     + str(lv["word"]) + "” (felt: "
                     + (lv["felt"] or "-") + ")")
    if pkt.get("spirit_today_has"):
        parts.append("spirit today: depth "
                     + str(pkt["spirit_today_depth"]) + "/5; word: "
                     + (pkt.get("spirit_today_word") or "-"))
    if pkt.get("spirit_streak"):
        parts.append("spirit streak: " + str(pkt["spirit_streak"]))
    parts.append("sales yesterday: " + str(pkt.get("sales_yesterday", 0)))
    if pkt.get("sales_best"):
        parts.append("best recent day: " + str(pkt["sales_best"]["date"])
                     + " = " + str(pkt["sales_best"]["n"]))
    parts.append("sales this week: " + str(pkt.get("sales_week", 0)))
    parts.append("clients due today: " + str(pkt.get("clients_due_n", 0))
                 + "; overdue: " + str(pkt.get("clients_overdue_n", 0)))
    parts.append("tasks due today: " + str(pkt.get("tasks_due", 0))
                 + "; overdue: " + str(pkt.get("tasks_overdue", 0)))
    parts.append("habits today: " + str(pkt.get("habits_done", 0)) + "/"
                 + str(pkt.get("habits_total", 0))
                 + "; consistency 7d: " + str(pkt.get("consistency7", 0)) + "%")
    if pkt.get("workout_streak"):
        parts.append("workout streak: " + str(pkt["workout_streak"]))
    if pkt.get("weight_delta_word"):
        parts.append("weight: " + str(pkt["weight_delta_word"]))
    if allow_money:
        if pkt.get("pantry_bottleneck"):
            parts.append("pantry bottleneck: "
                         + str(pkt["pantry_bottleneck"]["name"]) + " = "
                         + str(pkt["pantry_bottleneck"]["days"]) + " days")
        if pkt.get("runway_months") is not None:
            parts.append("cash runway: "
                         + format(pkt["runway_months"], ".1f") + " months")
        if "emergency_pct" in pkt:
            parts.append("emergency fund: " + str(pkt["emergency_pct"])
                         + "% of target")
        if "bills_overdue_n" in pkt:
            parts.append("bills overdue: " + str(pkt["bills_overdue_n"]))
        if pkt.get("fun_remaining") is not None:
            parts.append("fun remaining: "
                         + str(int(pkt["fun_remaining"])) + " KSh")
        if "commissions_due" in pkt:
            parts.append("commissions due today: "
                         + str(pkt["commissions_due"]) + "; pending: "
                         + str(int(pkt.get("commissions_pending", 0)))
                         + " KSh")
    rb = _retrieved_block(idx, fb, pkt, allow_money)
    if rb:
        parts.append("")
        parts.append("RETRIEVED (the person's own most relevant past words):")
        parts.append(rb)
    pb = _patterns_block(refl, voice, pkt.get("mood_band", "none"))
    if pb:
        parts.append("")
        parts.append("PATTERNS (learned about them over time):")
        parts.append(pb)
    cb = _constraints_block(fb, pkt.get("mood_band", "none"), voice)
    if cb:
        parts.append("")
        parts.append("CONSTRAINTS (how they asked you to behave):")
        parts.append(cb)
    if pkt.get("anchor"):
        parts.append("")
        parts.append("ANCHOR LINE: " + str(pkt["anchor"]))
    parts.append("")
    parts.append("MOOD: " + (pkt.get("mood_today") or "-"))
    parts.append("PAGE VOICE: " + voice)
    system = "\n".join(parts)
    user = _AUTO.get(voice, _AUTO["morning"])
    return _llm_call(ak, bu, model, system, user)


def _llm_answer(pkt, voice, question, idx, fb, refl, allow_money):
    ki = _keyinfo()
    if not ki:
        return None
    ak, bu, model = ki
    parts = [_SYS, "", "CONTEXT (verified facts):"]
    parts.append("today " + str(pkt["today"]) + "; mood "
                 + (pkt.get("mood_today") or "-"))
    rb = _retrieved_block(idx, fb, pkt, allow_money, k=5)
    if rb:
        parts.append("")
        parts.append("RETRIEVED (their own relevant past words):")
        parts.append(rb)
    pb = _patterns_block(refl, voice, pkt.get("mood_band", "none"))
    if pb:
        parts.append("")
        parts.append("PATTERNS:")
        parts.append(pb)
    cb = _constraints_block(fb, pkt.get("mood_band", "none"), voice)
    if cb:
        parts.append("")
        parts.append("CONSTRAINTS:")
        parts.append(cb)
    parts.append("")
    parts.append("Answer the question using only the facts above. "
                 "2 to 4 sentences, second person, no lists.")
    system = "\n".join(parts)
    return _llm_call(ak, bu, model, system, question)


def _offline_answer(pkt, question, idx, fb, allow_money):
    docs = _search(idx, fb, question, allow_money,
                   pkt.get("mood_today"), k=3)
    if not docs:
        return ("I looked through what I can see and found nothing close "
                "to that yet. Tell me more, or log it, and I'll remember "
                "next time.")
    top = docs[0]
    src = top.get("src", "")
    date = top.get("date", "")
    text = _trim(top.get("text", ""), 80)
    if len(docs) >= 2:
        d2 = docs[1].get("date", "")
        base = ("Two moments stand out for me: " + date + " and " + d2
                + ". On the first you wrote '" + text + "'.")
    else:
        base = ("The closest moment I can find is " + date + " (" + src
                + "): '" + text + "'.")
    extra = ""
    if pkt.get("mood_today") in LOW:
        extra = " Given how you're feeling right now, lean on that, don't argue with it."
    return base + extra


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _card_html(voice, message, facts, used_llm):
    label, color = VOICE_META.get(voice, ("Companion", "#8893AB"))
    msg = _e(message).replace("\n", "<br>")
    if used_llm:
        ai = '<span class="plc-ai">ai</span>'
    else:
        ai = ""
    chips = ""
    if facts:
        inner = ""
        for x in facts:
            inner = inner + '<span class="plc-chip">' + _e(x) + '</span>'
        chips = '<div class="plc-facts">' + inner + '</div>'
    return (_STYLE + '<div class="plc" style="--plc:' + color + '">'
            '<div class="plc-rail"></div>'
            '<div class="plc-head"><span class="plc-dot"></span>'
            '<span class="plc-name">PULSE</span>'
            '<span class="plc-voice">' + _e(label) + '</span>' + ai
            + '</div><div class="plc-msg">' + msg + '</div>'
            + chips + '</div>')


def _feedback_widget(voice, feats, pkt):
    k = "plc_fb_" + voice
    c1, c2, _ = st.columns([1, 1, 6])
    with c1:
        if st.button("👍 helped", key=k + "_up"):
            fb = _get_feedback()
            rec = {"ts": U.now_local().isoformat(),
                   "kind": "like", "page": voice,
                   "mood_band": pkt.get("mood_band", "none"),
                   "features": list(feats), "note": "",
                   "rtags": [], "rsrc": ""}
            if _HAS_BRAIN:
                _B.record_feedback(fb, rec)
            st.rerun()
    with c2:
        liked = st.button("👎 didn't land", key=k + "_down")
    if liked:
        with st.form(k + "_form"):
            note = st.text_input("what felt off? (one line)",
                                 key=k + "_note")
            chips = st.multiselect("or pick", _DISLIKE_CHIPS, key=k + "_chips")
            ok = st.form_submit_button("Save feedback")
            if ok:
                fb = _get_feedback()
                txt = (note or "").strip()
                if chips:
                    txt = (txt + " [" + ", ".join(chips) + "]").strip()
                rec = {"ts": U.now_local().isoformat(),
                       "kind": "dislike", "page": voice,
                       "mood_band": pkt.get("mood_band", "none"),
                       "features": list(feats), "note": txt,
                       "rtags": [], "rsrc": ""}
                if _HAS_BRAIN:
                    _B.record_feedback(fb, rec)
                st.success("Noted. PULSE will learn from this.")
                st.rerun()


def _ask_widget(pkt, voice, idx, fb, refl, allow_money):
    with st.expander("Ask PULSE anything"):
        st.caption("Grounded in your logged life and what it has "
                   "retrieved. With no API key it answers from memory.")
        q = st.text_input("Ask", key="plc_ask_" + voice,
                          placeholder="e.g. should I top up fun this week?")
        if st.button("Ask", key="plc_go_" + voice):
            qq = (q or "").strip()
            if qq:
                ans = _llm_answer(pkt, voice, qq, idx, fb, refl, allow_money)
                if ans:
                    st.markdown('<div class="plc-ans">'
                                + _e(ans).replace("\n", "<br>")
                                + '</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="plc-ans">'
                                + _e(_offline_answer(pkt, qq, idx, fb,
                                                     allow_money))
                                + '</div>', unsafe_allow_html=True)


def _companion_settings(ctx):
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
            "talks, grounded in your log and its own memory:")
        st.code('[llm]\napi_key = "sk-..."\nmodel = "gpt-4o-mini"\n'
                '# base_url = "https://your-compatible-endpoint/v1"',
                language="toml")
    with st.expander("Memory & training (the brain)"):
        if not _HAS_BRAIN:
            st.caption("The brain module is not loaded; the companion is "
                       "running on its built-in voice only.")
        else:
            idx = _get_index(ctx, True)
            fb = _get_feedback()
            refl = _get_reflection(ctx)
            summ = _B.feedback_summary(fb)
            st.markdown(UI.kv([
                ("Memories indexed", str(_B.index_size(idx))),
                ("Feedback", str(summ.get("likes", 0)) + " liked · "
                 + str(summ.get("dislikes", 0)) + " didn't land"),
                ("Recurring lesson",
                 (refl.get("recurring_lessons") or ["—"])[0]
                 if refl.get("recurring_lessons") else "—"),
                ("Energy source",
                 (refl.get("energy_sources") or [("—", 0)])[0][0]),
                ("Mood slope 7d",
                 ("lifting" if (refl.get("mood_slope_7", 0) or 0) > 0
                  else ("heavy" if (refl.get("mood_slope_7", 0) or 0) < 0
                       else "steady"))),
            ]), unsafe_allow_html=True)
            sups = _B.learned_suppressions(
                fb, list(VOICE_META.keys()))
            if sups:
                st.caption("PULSE has learned to hold back these moves:")
                for s in sups:
                    st.markdown('- in **' + _e(s["page"]) + '** when **'
                                + _e(s["mood_band"]) + '**: '
                                + _e(s["feature"]),
                                unsafe_allow_html=True)
            else:
                st.caption("No learned suppressions yet. Use 👎 on a "
                           "message to teach PULSE your taste.")
            ca, cb, cc = st.columns(3)
            with ca:
                if st.button("Rebuild memory index", key="plc_rebuild"):
                    _B.rebuild(_stores(ctx, True))
                    st.success("Memory rebuilt.")
                    st.rerun()
            with cb:
                if st.button("Reset learned taste", key="plc_resetfb"):
                    _B.reset_feedback()
                    st.success("Feedback cleared.")
                    st.rerun()
            with cc:
                st.download_button(
                    "Export brain (.json)",
                    json.dumps({"index": idx, "feedback": fb,
                                "reflection": refl}, default=str),
                    file_name="pulse_brain.json",
                    mime="application/json", key="plc_expbrain")


def panel(ctx, voice="morning", allow_money=False, ask_box=True):
    try:
        if voice == "money" and not allow_money:
            voice = "review"
        pkt = build_packet(ctx, voice, allow_money)
        idx = _get_index(ctx, allow_money)
        fb = _get_feedback()
        refl = _get_reflection(ctx)
        sents, facts, feats = _deterministic(pkt, voice, idx, fb, refl,
                                             allow_money)
        msg = " ".join(sents)
        used = False
        if _have_key():
            lm = _llm_message(pkt, voice, idx, fb, refl, allow_money)
            if lm:
                msg = lm
                used = True
        st.markdown(_card_html(voice, msg, facts, used),
                    unsafe_allow_html=True)
        try:
            _feedback_widget(voice, feats, pkt)
        except Exception:
            pass
        if voice == "quiet":
            _companion_settings(ctx)
        elif ask_box:
            try:
                _ask_widget(pkt, voice, idx, fb, refl, allow_money)
            except Exception:
                pass
    except Exception:
        try:
            st.markdown(_card_html(voice or "morning",
                                   "I'm here. (the companion hit a snag - "
                                   "your data is safe.)", [], False),
                        unsafe_allow_html=True)
        except Exception:
            pass
