"""PULSE companion - the voice that has read your life.

The card feels spoken, not displayed: a slow breathing halo whose rhythm and
saturation are per-page, a caught-light sheen that sweeps on hover, a nudge
arrow that nudges on a loop, a fine linen grain, a left rail in the voice's
own colour, and the voice line set large and italic with a hanging drop-cap
quotation glyph. The companion speaks in nine distinct registers (one per
page) so TrueWave never sounds like the Vault and Spirit never carries a
number. Each register references live page state, so editing anything on a
page changes the spoken line within one rerun.

The companion speaks in five non-overlapping layers (moment / voice / notice /
pulse / nudge), each computed from a different angle of the LIVE state, so no
page reads the same and no layer repeats another. The moment eyebrow always
carries the real HH:MM so liveness is verifiable against the phone clock.

A single delicate provenance line sits in the margin like a citation; the
machinery (grounding facts, the ask-box, the tuning, the free-tier provider
that answered, a one-shot flash on tune) lives in one collapsed, whisper-
quiet drawer beneath the card, framed as tuning an instrument, never grading
a student. There is NO like/dislike on the card - PULSE learns from what the
operator does after it speaks (brain.reconcile_implicit).

Three layers over one context packet:
  * build_packet() reads recent journal / spirit / sales / mood / clients /
    tasks / habits / weight, and - ONLY when allow_money is True (inside the
    locked Archive) - pantry / runway / emergency / bills / commissions.
  * A deterministic feel-only voice per page (nine registers), augmented by
    the brain with a remembered verse or memory, plus the live timeline
    (moment / notice / pulse / nudge).
  * If the free-tier router (src.llm_router) has any provider configured, a
    strictly-grounded model writes the voice line, fed all layers as
    constraints so its voice is page-personalised too.

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

try:
    from . import llm_router as _R
    _HAS_ROUTER = True
except Exception:
    _R = None
    _HAS_ROUTER = False

try:
    from . import perceive as _P
    _HAS_PERC = True
except Exception:
    _P = None
    _HAS_PERC = False

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

_TUNE_CHIPS = [
    "softer", "more direct", "shorter", "skip scripture here",
    "cite scripture", "cite a past win", "more practical",
    "calmer / less pep",
]

_SRC_LABEL = {
    "spirit": "your spirit log", "journal": "your journal",
    "sale": "a past sale", "income": "an income entry",
    "client": "a client note", "flow": "your money log",
    "bill": "your money log", "emergency": "your money log",
    "fund": "your money log", "money": "your money log",
}

_STYLE = (
    "<style>"
    "@keyframes plcBreathe{0%,100%{transform:scale(1);opacity:.10}"
    "50%{transform:scale(1.16);opacity:.22}}"
    "@keyframes plcRise{from{opacity:0;transform:translateY(10px)}"
    "to{opacity:1;transform:none}}"
    "@keyframes plcSheen{0%{transform:translateX(-120%)}"
    "100%{transform:translateX(120%)}}"
    "@keyframes plcScan{0%{transform:translateX(-100%)}"
    "100%{transform:translateX(100%)}}"
    "@keyframes plcFlash{0%{opacity:.5}100%{opacity:0}}"
    "@keyframes plcNudge{0%,100%{transform:translateX(0)}"
    "50%{transform:translateX(3px)}}"
    ".plc{position:relative;overflow:hidden;margin:16px 0 6px;"
    "padding:20px 22px 18px 24px;border:1px solid var(--hair,#1C2740);"
    "border-radius:16px;background:linear-gradient(180deg,"
    "rgba(18,26,43,.94),rgba(12,18,30,.96));"
    "box-shadow:0 12px 34px -26px rgba(0,0,0,.92);"
    "transition:transform .28s cubic-bezier(.2,.7,.2,1),"
    "border-color .28s,box-shadow .28s;"
    "animation:plcRise .6s cubic-bezier(.2,.7,.2,1) both}"
    ".plc:hover{transform:translateY(-3px);border-color:var(--plc,#4C8DFF);"
    "box-shadow:0 26px 56px -28px rgba(0,0,0,.95),"
    "0 0 0 1px rgba(255,255,255,.03)}"
    ".plc::after{content:'';position:absolute;inset:0;pointer-events:none;"
    "background:linear-gradient(115deg,transparent 42%,"
    "rgba(255,255,255,.05) 50%,transparent 58%);opacity:0}"
    ".plc:hover::after{opacity:1;animation:plcScan 1.5s ease}"
    ".plc-grain{position:absolute;inset:0;pointer-events:none;opacity:.5;"
    "background-image:radial-gradient(rgba(255,255,255,.05) .5px,"
    "transparent .6px);background-size:3px 3px;mix-blend-mode:soft-light}"
    ".plc-sheen{position:absolute;top:0;left:0;width:60%;height:1px;"
    "pointer-events:none;background:linear-gradient(90deg,transparent,"
    "rgba(255,255,255,.5),transparent);opacity:0}"
    ".plc:hover .plc-sheen{opacity:.8;animation:plcSheen 1.1s ease}"
    ".plc-rail{position:absolute;left:0;top:0;bottom:0;width:3px;"
    "background:linear-gradient(180deg,var(--plc,#4C8DFF),transparent 82%);"
    "transition:width .28s}"
    ".plc:hover .plc-rail{width:4px}"
    ".plc-halo{position:absolute;left:-34px;top:-34px;width:132px;"
    "height:132px;border-radius:50%;pointer-events:none;"
    "background:radial-gradient(circle,var(--plc),transparent 70%);"
    "filter:blur(10px) saturate(var(--plc-sat,1));"
    "animation:plcBreathe var(--plc-breath,5s) ease-in-out infinite}"
    ".plc-flash{position:absolute;inset:0;pointer-events:none;"
    "border-radius:16px;background:radial-gradient(circle at 28% 26%,"
    "var(--plc),transparent 68%);opacity:0;"
    "animation:plcFlash 1.25s ease-out 1}"
    ".plc-head{position:relative;display:flex;align-items:center;"
    "gap:9px;margin-bottom:12px;flex-wrap:wrap}"
    ".plc-mark{font:700 11px/1 var(--mono,'JetBrains Mono',monospace);"
    "letter-spacing:.34em;text-transform:uppercase;color:var(--ink-2,#B6C0D4)}"
    ".plc-voice{font:600 10px/1 var(--mono,'JetBrains Mono',monospace);"
    "letter-spacing:.16em;text-transform:uppercase;color:var(--plc,#4C8DFF);"
    "padding:3px 9px;border-radius:999px;background:rgba(255,255,255,.03);"
    "border:1px solid var(--hair,#1C2740)}"
    ".plc-ai{font:700 8px/1 var(--mono,'JetBrains Mono',monospace);"
    "letter-spacing:.14em;text-transform:uppercase;color:#D946EF;"
    "border:1px solid rgba(217,70,239,.4);background:rgba(217,70,239,.12);"
    "border-radius:999px;padding:3px 8px}"
    ".plc-via{font:600 8px/1 var(--mono,'JetBrains Mono',monospace);"
    "letter-spacing:.1em;text-transform:uppercase;color:var(--mute-2,#8893AB);"
    "border:1px solid var(--hair,#1C2740);border-radius:999px;padding:3px 8px}"
    ".plc-body{position:relative;padding-left:30px}"
    ".plc-quote{position:absolute;left:0;top:-8px;"
    "font:700 54px/1 var(--disp,'Space Grotesk',sans-serif);"
    "color:var(--plc,#4C8DFF);opacity:.15;pointer-events:none;user-select:none}"
    ".plc-line{margin:0;font:500 18px/1.65 var(--body,'Manrope',sans-serif);"
    "color:var(--ink,#E8EDF7);font-style:italic;letter-spacing:-.006em}"
    ".plc-moment{display:flex;align-items:center;gap:7px;margin:0 0 11px;"
    "font:600 10px/1.3 var(--mono,'JetBrains Mono',monospace);"
    "letter-spacing:.14em;text-transform:uppercase;color:var(--mute-2,#8893AB)}"
    ".plc-moment-dot{width:6px;height:6px;border-radius:50%;"
    "background:var(--plc);box-shadow:0 0 7px var(--plc);"
    "animation:plcBreathe var(--plc-breath,5s) ease-in-out infinite;"
    "flex:0 0 auto}"
    ".plc-perceive{margin:11px 0 0 30px;padding:8px 11px;"
    "border-left:2px solid var(--plc);background:linear-gradient(90deg,"
    "rgba(255,255,255,.025),transparent);border-radius:0 8px 8px 0;"
    "font:500 13.5px/1.55 var(--body,'Manrope',sans-serif);color:var(--ink-2,#B6C0D4)}"
    ".plc-pulse{margin:8px 0 0 30px;font:600 11px/1.4 "
    "var(--mono,'JetBrains Mono',monospace);color:var(--mute,#69748C);"
    "letter-spacing:.04em}"
    ".plc-nudge{margin:11px 0 0 30px;display:flex;align-items:flex-start;"
    "gap:8px;font:600 12.5px/1.45 var(--body,'Manrope',sans-serif);"
    "color:var(--ink,#E8EDF7)}"
    ".plc-nudge .arr{color:var(--plc,#4C8DFF);"
    "font:700 13px/1.3 var(--mono,'JetBrains Mono',monospace);"
    "animation:plcNudge 1.6s ease-in-out infinite}"
    ".plc-cite{margin:11px 0 0 30px;font:500 11px/1.5 "
    "var(--mono,'JetBrains Mono',monospace);color:var(--mute-2,#8893AB);"
    "letter-spacing:.02em}"
    ".plc-tune-hint{position:absolute;right:16px;top:18px;"
    "font:600 13px/1 var(--mono,'JetBrains Mono',monospace);"
    "color:var(--mute,#69748C);opacity:0;transition:opacity .28s;"
    "pointer-events:none}"
    ".plc:hover .plc-tune-hint{opacity:.5}"
    ".plc-grounds-list{font:500 11px/1.5 "
    "var(--mono,'JetBrains Mono',monospace);color:var(--mute-2,#8893AB);"
    "margin:2px 0 12px;letter-spacing:.02em}"
    ".plc-taste{font:500 11.5px/1.5 var(--body,'Manrope',sans-serif);"
    "color:var(--ink-2,#B6C0D4);font-style:italic;margin:0 0 12px;"
    "border-left:2px solid var(--plc,#4C8DFF);padding-left:10px}"
    ".plc-ans{margin-top:10px;padding:12px 14px;border-radius:11px;"
    "border:1px solid var(--hair,#1C2740);background:rgba(255,255,255,.02);"
    "font:500 13.5px/1.6 var(--body,'Manrope',sans-serif);"
    "color:var(--ink-2,#B6C0D4);font-style:italic}"
    ".plc-health{display:grid;grid-template-columns:repeat(2,1fr);"
    "gap:6px 14px;margin:6px 0 4px}"
    ".plc-health .k{font:600 10px/1.4 "
    "var(--mono,'JetBrains Mono',monospace);color:var(--mute,#69748C);"
    "letter-spacing:.06em}"
    ".plc-health .v{font:700 12px/1.4 "
    "var(--mono,'JetBrains Mono',monospace);color:var(--ink,#E8EDF7)}"
    "@media (max-width:760px){.plc{padding:16px 16px 14px 18px}"
    ".plc-body{padding-left:22px}.plc-quote{font-size:40px;top:-2px}"
    ".plc-line{font-size:16px;line-height:1.6}"
    ".plc-cite,.plc-perceive,.plc-pulse,.plc-nudge{margin-left:22px}"
    ".plc-health{grid-template-columns:1fr}}"
    "</style>"
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

_SYS = (
    "You are PULSE, a grounded companion for one person. You receive a "
    "CONTEXT block of verified facts, a RETRIEVED block of the person's own "
    "past words most relevant to now, a PATTERNS block of what you have "
    "learned about them over time, a THREAD block of a feeling they have "
    "felt on multiple days, a PAGE MOMENT block of where and when they are, "
    "a PAGE NOTICE block of what you observe on this exact page, a PAGE "
    "RHYTHM block of how they show up to this part of their life, a NEXT "
    "MOVE block of the single most useful concrete action right now, and a "
    "CONSTRAINTS block of how they have tuned you. Rules: (1) Use ONLY "
    "facts present in CONTEXT and RETRIEVED; never invent sales, feelings, "
    "verses, dates, clients or events. (2) Speak in second person, warmly "
    "and specifically, in the register of the PAGE VOICE named below. (3) "
    "When you cite a number, quote or feeling, use the exact one given. "
    "(4) Match their current mood. (5) Obey every line in CONSTRAINTS "
    "without mentioning that you were told. (6) Weave the PAGE NOTICE and "
    "PAGE RHYTHM naturally so the line could only be spoken on this page, "
    "right now. (7) If a NEXT MOVE is given and it fits, weave it in as "
    "one concrete step. (8) If the question touches money, balances, "
    "pantry or the emergency fund but CONTEXT has no money facts, reply "
    "that you keep finances private and they should ask inside the "
    "Archive. (9) Do not ask a question back unless it is a single gentle "
    "offer. (10) No lists, no headers, no emojis."
)


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


def _get_state():
    if not _HAS_BRAIN:
        return {}
    try:
        return _B.load_state()
    except Exception:
        return {}


def _search(idx, fb, query, allow_money, mood, k=3, refl=None,
            state=None, page=None):
    if not _HAS_BRAIN or idx is None:
        return []
    try:
        return _B.search(idx, query, k=k, allow_money=allow_money,
                         mood=mood, fb=fb, refl=refl, state=state,
                         page=page)
    except Exception:
        return []


def _have_key():
    if not _HAS_ROUTER:
        return False
    try:
        return _R.has_providers()
    except Exception:
        return False


def _have_llm():
    return _have_key()


# ---------------------------------------------------------------------------
# live timeline view (anchors perception to the clock)
# ---------------------------------------------------------------------------

def _wt(s):
    out = []
    cur = ""
    for ch in (s or "").lower():
        if ch.isalnum():
            cur = cur + ch
        else:
            if len(cur) >= 4:
                out.append(cur)
            cur = ""
    if len(cur) >= 4:
        out.append(cur)
    return out


def _match_habit(block_label, habits, log, today_iso):
    bl = (block_label or "").lower()
    blt = set(_wt(block_label))
    for h in habits:
        nm = (h.get("name") or "").lower()
        if not nm:
            continue
        nmt = set(_wt(nm))
        if not (nmt & blt):
            continue
        if not log.get(h["id"], {}).get(today_iso):
            return h
    return None


def _compute_live(ctx, habits, log, today_iso):
    blocks = ctx.get("today_blocks") or []
    aidx = ctx.get("active_idx", -1)
    if aidx is None:
        aidx = -1
    try:
        prog = float(ctx.get("progress", 0.0) or 0.0)
    except Exception:
        prog = 0.0
    cur = ctx.get("current")
    nxt = ctx.get("next_block")
    now_dt = ctx.get("now_dt")
    now_hm = now_dt.strftime("%H:%M") if now_dt else "--:--"
    cur_label = (cur or {}).get("label", "") if isinstance(cur, dict) else ""
    cur_time = (cur or {}).get("time", "") if isinstance(cur, dict) else ""
    nxt_label = (nxt or {}).get("label", "") if isinstance(nxt, dict) else ""
    nxt_time = (nxt or {}).get("time", "") if isinstance(nxt, dict) else ""
    cur_habit = (_match_habit(cur_label, habits, log, today_iso)
                 if cur_label else None)
    nxt_habit = None
    nxt_habit_time = ""
    start = aidx if aidx >= 0 else 0
    for b in blocks[start + 1:]:
        h = _match_habit(b.get("label", ""), habits, log, today_iso)
        if h:
            nxt_habit = h
            nxt_habit_time = b.get("time", "")
            break
    if nxt_habit is None and now_dt is not None and now_dt.hour >= 21:
        for h in habits:
            nm = (h.get("name") or "").lower()
            if (("light" in nm or "sleep" in nm)
                    and not log.get(h["id"], {}).get(today_iso)):
                nxt_habit = h
                nxt_habit_time = ""
                break
    passed = None
    if aidx > 0:
        for b in blocks[:aidx]:
            h = _match_habit(b.get("label", ""), habits, log, today_iso)
            if h:
                passed = h
                break
    passed_n = aidx if aidx > 0 else 0
    ahead = max(0, len(blocks) - passed_n - (1 if cur_label else 0))
    return {
        "now_hm": now_hm,
        "cur_label": cur_label, "cur_time": cur_time,
        "nxt_label": nxt_label, "nxt_time": nxt_time,
        "prog": prog,
        "cur_habit": ((cur_habit or {}).get("name", "")
                      if isinstance(cur_habit, dict) else ""),
        "nxt_habit": ((nxt_habit or {}).get("name", "")
                      if isinstance(nxt_habit, dict) else ""),
        "nxt_habit_time": nxt_habit_time,
        "passed_habit": ((passed or {}).get("name", "")
                         if isinstance(passed, dict) else ""),
        "has_blocks": bool(blocks),
        "passed_n": passed_n, "ahead": ahead,
    }


# ---------------------------------------------------------------------------
# per-page stats (built from session data, handed to perceive.py)
# ---------------------------------------------------------------------------

def _page_stats(ctx, voice, allow_money):
    ps = {}
    try:
        _dt = __import__("datetime")
        today = ctx["today"]
        habits = ctx.get("habits") or []
        log = ctx.get("habit_log") or {}
        spiritual = ctx.get("spiritual") or {}
        sd = ctx.get("sales_daily") or {}
        clients = ctx.get("clients") or []
        journal = ctx.get("journal") or {}
        tasks = ctx.get("tasks") or []
        weights = ctx.get("weights") or []
        last7 = [(today - _dt.timedelta(days=o)).isoformat()
                 for o in range(7)]
        wid = None
        for h in habits:
            if str(h.get("name", "")).lower().startswith("workout"):
                wid = h["id"]
                break
        move_days_7 = sum(1 for d in last7
                          if wid and (log.get(wid, {}) or {}).get(d))
        sat_days_7 = sum(1 for d in last7
                         if _spirit_present(spiritual.get(d)))
        j_days_7 = sum(1 for d in last7 if d in journal)
        sold_days_7 = sum(
            1 for d in last7
            if int((sd.get(d) or {}).get("sold", 0) or 0) > 0)
        cleared_days_7 = sum(
            1 for d in last7
            if any(t.get("done_date") == d for t in tasks))
        first_undone = ""
        for h in habits:
            if not (log.get(h["id"], {}) or {}).get(today.isoformat()):
                first_undone = h.get("name", "")
                break
        term = set(D.terminal_ids())
        due_clients = [c for c in clients
                       if c.get("stage") not in term
                       and c.get("next_date") == today.isoformat()]
        over_clients = [c for c in clients
                        if c.get("stage") not in term
                        and c.get("next_date")
                        and c["next_date"] < today.isoformat()]
        hottest = ""
        for c in due_clients:
            if c.get("heat") == "Hot":
                hottest = c.get("name", "")
                break
        if not hottest and due_clients:
            hottest = due_clients[0].get("name", "")
        if not hottest and over_clients:
            hottest = over_clients[0].get("name", "")
        se = spiritual.get(today.isoformat())
        sat_today = bool(se)
        depth = int((se or {}).get("depth", 0) or 0)
        last_word = ((se or {}).get("word") or "").strip()
        if not last_word:
            for o in range(1, 8):
                e = spiritual.get(
                    (today - _dt.timedelta(days=o)).isoformat())
                if e and (e.get("word") or "").strip():
                    last_word = (e.get("word") or "").strip()
                    break
        yest_iso = (today - _dt.timedelta(days=1)).isoformat()
        lj = journal.get(yest_iso) or {}
        last_lesson = (lj.get("lesson") or lj.get("win") or "").strip()
        j_today = today.isoformat() in journal
        j_streak = _streak_j(journal)
        ws = 0
        if wid:
            s = log.get(wid, {}) or {}
            for o in range(0, 400):
                if s.get((today - _dt.timedelta(days=o)).isoformat()):
                    ws += 1
                else:
                    break
        wdelta = ""
        if len(weights) >= 2:
            ws2 = sorted(weights, key=lambda w: w.get("date", ""))
            try:
                dd = float(ws2[-1]["kg"]) - float(ws2[0]["kg"])
                wdelta = ("+" if dd >= 0 else "") + format(dd, ".1f") + " kg"
            except Exception:
                wdelta = ""
        overdue_t = sum(1 for t in tasks
                        if not t.get("done") and t.get("due")
                        and t["due"] < today.isoformat())
        due_t = sum(1 for t in tasks
                    if not t.get("done")
                    and t.get("due") == today.isoformat())
        cons7 = _consistency(habits, log, 7)
        sw = sum(int((sd.get(d) or {}).get("sold", 0) or 0) for d in last7)
        sh = _spirit_health(spiritual)
        name = ""
        days = ""
        bo = 0
        if allow_money:
            vault = ctx.get("vault") or {}
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
                        age = max(0, (today - _dt.date.fromisoformat(chk)).days)
                    except Exception:
                        age = 0
                aged = max(0.0, raw - age)
                if bn is None or aged < bn[0]:
                    bn = (aged, it.get("name", "?"))
            if bn is not None:
                days = int(round(bn[0]))
                name = bn[1] or ""
            bo = sum(1 for b in vault.get("bills", [])
                     if not b.get("paid") and b.get("due")
                     and b["due"] < today.isoformat())
        live = _compute_live(ctx, habits, log, today.isoformat())
        ps.update({
            "first_undone": first_undone,
            "due_n": len(due_clients), "due": len(due_clients),
            "over": len(over_clients),
            "yest": int((sd.get(yest_iso) or {}).get("sold", 0) or 0),
            "hottest": hottest,
            "last_word": last_word,
            "word": ((se or {}).get("word") or "").strip() if se else "",
            "depth": depth,
            "sat_streak": _streak_spirit(spiritual),
            "sat_today": sat_today,
            "last_lesson": last_lesson,
            "j_today": j_today, "j_streak": j_streak, "ws": ws,
            "delta": wdelta, "overdue": overdue_t, "due_t": due_t,
            "c": cons7, "sw": sw, "sh": sh,
            "sold_days_7": sold_days_7, "sat_days_7": sat_days_7,
            "move_days_7": move_days_7, "j_days_7": j_days_7,
            "cleared_days_7": cleared_days_7,
            "name": name, "days": days, "bo": bo,
            "live": live,
        })
    except Exception:
        pass
    return ps


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
        if (log.get(h["id"], {}) or {}).get(ti):
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
# retrieval weaving + augmentation (felt memory for the voice line)
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


def _prov_for(feat, pkt):
    if feat == "quoted_verse":
        lv = pkt.get("last_verse")
        lj = pkt.get("last_journal")
        d = (lv or {}).get("date") or (lj or {}).get("date") or ""
        if lv or lj:
            return "your verse" + (" · " + d if d else "")
        return None
    if feat == "quoted_memory":
        lj = pkt.get("last_journal")
        d = (lj or {}).get("date") or ""
        if d:
            return "your journal · " + d
        return "your journal"
    if feat == "money_advice":
        return "your money log"
    return None


def _augment(pkt, tagged, base_facts, idx, fb, refl, state, allow_money):
    mb = pkt.get("mood_band", "none")
    page = pkt.get("page", "morning")
    out = []
    feats = set()
    facts = list(base_facts)
    refs = []
    prov = []
    for text, feat in tagged:
        if feat and _HAS_BRAIN and not _B.move_allowed(state, fb, page, mb, feat):
            continue
        if feat:
            feats.add(feat)
        out.append(text)
    if _HAS_BRAIN and _B.move_allowed(state, fb, page, mb, "quoted_memory"):
        docs = _search(idx, fb, _auto_query(page, pkt), allow_money,
                       pkt.get("mood_today"), k=2, refl=refl, state=state,
                       page=page)
        if docs:
            d0 = docs[0]
            sent, mf = _weave_memory(d0, page)
            if not (_HAS_BRAIN and not _B.move_allowed(state, fb, page, mb, mf)):
                out.append(sent)
                feats.add(mf)
                facts.append("memory " + str(d0.get("date", "")))
                refs.append(str(d0.get("src", "")) + "|" + str(d0.get("date", "")))
                prov.append(_SRC_LABEL.get(d0.get("src", ""), "a note")
                            + " · " + str(d0.get("date", "")))
    if _HAS_BRAIN and _B.move_allowed(state, fb, page, mb, "pattern_cited"):
        pat = _B.top_pattern(refl, page, mb)
        if pat:
            out.append(pat)
            feats.add("pattern_cited")
            facts.append("pattern")
            prov.append("a pattern you keep writing")
    return out, facts, feats, refs, prov


# ---------------------------------------------------------------------------
# deterministic voices - nine distinct registers, each reactive to live state
# ---------------------------------------------------------------------------

def _cap_tagged(tagged, n):
    return tagged[:n]


def _v_morning(p):
    t = []
    live = p.get("_live", {}) or {}
    ps = p.get("_ps", {}) or {}
    cur = live.get("cur_label", "")
    fu = ps.get("first_undone", "")
    due = ps.get("due", 0) or p.get("clients_due_n", 0)
    if cur:
        t.append(["You're in " + cur + " right now - let it be the "
                  "whole hour; the rest can wait outside.", None])
    elif fu:
        t.append([fu + " is the first open thread on the wall - do "
                  "it and the wall answers.", None])
    elif due > 0:
        t.append([str(due) + " call(s) sit in the pipe; the morning "
                  "belongs to you until they wake.", None])
    else:
        t.append(["Clean hour. One true move and the day takes "
                  "shape.", None])
    return t, []


def _v_sales(p):
    t = []
    ps = p.get("_ps", {}) or {}
    due = ps.get("due", 0) or p.get("clients_due_n", 0)
    over = ps.get("over", 0) or p.get("clients_overdue_n", 0)
    hot = ps.get("hottest", "")
    yest = ps.get("yest", 0)
    if over > 0 and hot:
        t.append([str(over) + " gone quiet - dial " + hot + " first, "
                  "then chase the rest.", "pep_talk"])
    elif due > 0 and hot:
        t.append([str(due) + " waiting - " + hot + " is the one to "
                  "move; one call, log it, next.", "pep_talk"])
    elif due > 0:
        t.append([str(due) + " in the pipe - that's revenue sitting "
                  "in your phone; pick it up.", "pep_talk"])
    elif yest > 0:
        t.append(["You closed " + str(yest) + " yesterday - stack "
                  "today on top; queue the next draft.", "pep_talk"])
    else:
        t.append(["Quiet pipe - log the next call the second it "
                  "ends; speed feeds the queue.", "pep_talk"])
    return t, []


def _v_spirit(p):
    t = []
    ps = p.get("_ps", {}) or {}
    sat = ps.get("sat_today", False)
    lw = ps.get("last_word", "") or p.get("spirit_today_word", "")
    if not sat and lw:
        t.append(["Not yet still - '" + lw + "' is still warm; sit "
                  "with it a minute.", "quoted_verse"])
    elif not sat:
        t.append(["Five silent minutes before the phone wakes - "
                  "that's the whole ask.", None])
    else:
        t.append(["You're in the quiet now - be still; the rest of "
                  "the day can wait outside.", None])
    return t, []


def _v_journal(p):
    t = []
    ps = p.get("_ps", {}) or {}
    jt = ps.get("j_today", False)
    ll = ps.get("last_lesson", "")
    if not jt and ll:
        t.append(["Blank page - the thread you keep writing is '"
                  + ll + "'; give it today's line.", "quoted_memory"])
    elif not jt:
        t.append(["No line yet - one sentence is enough: what "
                  "happened, what you learned.", None])
    else:
        t.append(["Today's page is open - close it with the lesson "
                  "before it fades.", None])
    return t, []


def _v_body(p):
    t = []
    live = p.get("_live", {}) or {}
    ps = p.get("_ps", {}) or {}
    ws = p.get("workout_streak", 0)
    cur = (live.get("cur_label", "") or "").lower()
    nxtl = (live.get("nxt_label", "") or "").lower()
    nht = live.get("nxt_time", "")
    if "workout" in cur:
        t.append(["In the movement block now - give it the full "
                  "forty-five; the body trusts you.", None])
    elif "workout" in nxtl:
        t.append(["Movement is next at " + (nht or "--:--")
                  + " - protect it like a meeting.", None])
    elif ws > 0:
        t.append(["A " + str(ws) + "-day streak - the body trusts "
                  "you; keep it small and consistent.", None])
    else:
        t.append(["No streak running - twenty minutes tonight "
                  "resets it; small beats heroic.", None])
    return t, []


def _v_focus(p):
    t = []
    ps = p.get("_ps", {}) or {}
    over = ps.get("overdue", 0)
    due = ps.get("due_t", 0)
    if over > 0:
        t.append([str(over) + " overdue - the smallest one first "
                  "breaks the logjam; then one deep block.", None])
    elif due > 0:
        t.append([str(due) + " due today - protect one "
                  "twenty-five-minute block for the hardest.", None])
    else:
        t.append(["Nothing overdue - phones down, one tab; the quiet "
                  "is for building, not clearing.", None])
    return t, []


def _v_review(p):
    t = []
    c = p.get("consistency7", 0)
    sw = p.get("sales_week", 0)
    sh = p.get("spirit_health", 0)
    t.append(["The shape this week: consistency " + str(c) + "%, "
              + str(sw) + " closed, spirit " + str(sh) + "% - feed "
              "the lowest one.", None])
    return t, []


def _v_money(p):
    t = []
    ps = p.get("_ps", {}) or {}
    days = ps.get("days")
    try:
        days = int(days)
    except Exception:
        days = 99
    bo = ps.get("bo", 0)
    name = ps.get("name", "") or "the staple"
    if days <= 3 and bo > 0:
        t.append([name + " at " + str(days) + "d and " + str(bo)
                  + " bill(s) overdue - shop today, hold the fun "
                  "top-up; basics first.", "money_advice"])
    elif days <= 3:
        t.append([name + " at " + str(days) + "d - on the shop list "
                  "today; the rest can wait.", "money_advice"])
    elif bo > 0:
        t.append([str(bo) + " bill(s) overdue - clear the oldest "
                  "first; calm after.", "money_advice"])
    else:
        t.append(["Books are calm - move a little into the "
                  "ring-fence while it's quiet; protect the floor.",
                  "money_advice"])
    return t, []


def _v_quiet(p):
    t = []
    anc = p.get("anchor", "")
    if anc:
        t.append(["The companion is listening - your anchor holds: '"
                  + anc + "'.", None])
    else:
        t.append(["The companion is listening - set an anchor below "
                  "and I'll lean on it on the hard days.", None])
    bf = []
    if anc:
        bf.append("anchor set")
    return t, bf


_VOICES = {
    "morning": _v_morning, "sales": _v_sales, "spirit": _v_spirit,
    "journal": _v_journal, "body": _v_body, "focus": _v_focus,
    "review": _v_review, "money": _v_money, "quiet": _v_quiet,
}


# ---------------------------------------------------------------------------
# compose (deterministic feel voice + optional free-tier LLM voice)
# ---------------------------------------------------------------------------

def _compose(pkt, voice, idx, fb, refl, state, allow_money, extra):
    fn = _VOICES.get(voice, _v_morning)
    tagged, base_facts = fn(pkt)
    sents, facts, feats, refs, prov = _augment(
        pkt, tagged, base_facts, idx, fb, refl, state, allow_money)
    mb = pkt.get("mood_band", "none")
    brev = _B.taste_brevity(state, voice, mb) if _HAS_BRAIN else ""
    if voice == "quiet":
        cap = 1
    elif mb == "low" or brev == "short":
        cap = 2
    else:
        cap = 3
    sents = sents[:max(1, cap)]
    msg = " ".join(sents)
    style = (_B.taste_style(state, voice, mb) if _HAS_BRAIN else "") or ""
    cite = ("— " + " · ".join(prov)) if prov else ""
    used = False
    provider = None
    perc = (extra or {}).get("perc") or {}
    if _have_llm():
        lm, pn = _llm_message(pkt, voice, idx, fb, refl, state,
                              allow_money, style, brev, extra)
        if lm:
            msg = lm
            used = True
            provider = pn
    meta = dict(
        moves=list(feats), refs=refs, grounds=facts, provenance=prov,
        cite_line=cite, nudge=perc.get("nudge", ""),
        moment=perc.get("moment", ""),
        perceive=(extra or {}).get("perceive_chosen", ""),
        pulse=perc.get("pulse", ""),
        breath=perc.get("breath", 5.0), sat=perc.get("sat", 1.0),
        provider=provider,
    )
    return msg, used, meta


# ---------------------------------------------------------------------------
# free-tier LLM layer
# ---------------------------------------------------------------------------

def _retrieved_block(idx, fb, pkt, allow_money, refl, state, k=4):
    if not _HAS_BRAIN or idx is None:
        return ""
    docs = _search(idx, fb, _auto_query(pkt.get("page", "morning"), pkt),
                   allow_money, pkt.get("mood_today"), k=k, refl=refl,
                   state=state, page=pkt.get("page"))
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


def _constraints_block(fb, mb, page, state):
    out = []
    if _HAS_BRAIN:
        sups = _B.learned_suppressions(fb, [page], [mb])
        for s in sups:
            out.append("Do not use the move '" + str(s["feature"])
                       + "' in this state; the person tuned it away.")
        for note in _B.complaint_notes(fb, mb, page, limit=2):
            out.append("The person previously asked, in a state like this: '"
                       + note + "'.")
        tnote = _B.taste_note(state, page, mb)
        if tnote:
            out.append("Standing preference: " + tnote)
    return "\n".join(out)


def _llm_message(pkt, voice, idx, fb, refl, state, allow_money,
                 style, brev, extra):
    if not _HAS_ROUTER:
        return None, None
    extra = extra or {}
    perc = extra.get("perc") or {}
    pc = extra.get("perceive_chosen", "")
    th = extra.get("thread", "")
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
    rb = _retrieved_block(idx, fb, pkt, allow_money, refl, state)
    if rb:
        parts.append("")
        parts.append("RETRIEVED (the person's own most relevant past words):")
        parts.append(rb)
    pb = _patterns_block(refl, voice, pkt.get("mood_band", "none"))
    if pb:
        parts.append("")
        parts.append("PATTERNS (learned about them over time):")
        parts.append(pb)
    if th:
        parts.append("")
        parts.append("THREAD (a feeling they have felt on multiple days):")
        parts.append(th)
    if perc.get("moment"):
        parts.append("")
        parts.append("PAGE MOMENT (where and when they are right now):")
        parts.append(perc["moment"])
    if pc:
        parts.append("")
        parts.append("PAGE NOTICE (what you observe on this page; weave it in):")
        parts.append(pc)
    if perc.get("pulse"):
        parts.append("")
        parts.append("PAGE RHYTHM (how they show up to this part of their life):")
        parts.append(perc["pulse"])
    if perc.get("nudge"):
        parts.append("")
        parts.append("NEXT MOVE (the single most useful concrete step):")
        parts.append(perc["nudge"])
    cb = _constraints_block(fb, pkt.get("mood_band", "none"), voice, state)
    if cb:
        parts.append("")
        parts.append("CONSTRAINTS (how they tuned you):")
        parts.append(cb)
    if pkt.get("anchor"):
        parts.append("")
        parts.append("ANCHOR LINE: " + str(pkt["anchor"]))
    parts.append("")
    parts.append("MOOD: " + (pkt.get("mood_today") or "-"))
    parts.append("PAGE VOICE: " + voice)
    style_line = "STYLE: " + (style or "natural, warm, specific")
    if brev == "short":
        style_line = style_line + "; keep it to one or two sentences, no padding."
    parts.append(style_line)
    parts.append("Speak 1 to 3 sentences; prefer fewer when the line is strong.")
    system = "\n".join(parts)
    user = _AUTO.get(voice, _AUTO["morning"])
    try:
        text, prov_name = _R.chat(
            [{"role": "system", "content": system},
             {"role": "user", "content": user}],
            temperature=0.7, max_tokens=240)
    except Exception:
        text, prov_name = None, None
    return text, prov_name


def _llm_answer(pkt, voice, question, idx, fb, refl, state, allow_money):
    if not _HAS_ROUTER:
        return None, None
    parts = [_SYS, "", "CONTEXT (verified facts):"]
    parts.append("today " + str(pkt["today"]) + "; mood "
                 + (pkt.get("mood_today") or "-"))
    rb = _retrieved_block(idx, fb, pkt, allow_money, refl, state, k=5)
    if rb:
        parts.append("")
        parts.append("RETRIEVED (their own relevant past words):")
        parts.append(rb)
    pb = _patterns_block(refl, voice, pkt.get("mood_band", "none"))
    if pb:
        parts.append("")
        parts.append("PATTERNS:")
        parts.append(pb)
    cb = _constraints_block(fb, pkt.get("mood_band", "none"), voice, state)
    if cb:
        parts.append("")
        parts.append("CONSTRAINTS:")
        parts.append(cb)
    parts.append("")
    parts.append("Answer the question using only the facts above. "
                 "2 to 4 sentences, second person, no lists.")
    system = "\n".join(parts)
    fused = question + " " + _auto_query(pkt.get("page", "morning"), pkt)
    try:
        return _R.chat(
            [{"role": "system", "content": system},
             {"role": "user", "content": fused}],
            temperature=0.6, max_tokens=240)
    except Exception:
        return None, None


def _offline_answer(pkt, question, idx, fb, allow_money, refl, state):
    fused = question + " " + _auto_query(pkt.get("page", "morning"), pkt)
    docs = _search(idx, fb, fused, allow_money,
                   pkt.get("mood_today"), k=3, refl=refl, state=state,
                   page=pkt.get("page"))
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
        extra = (" Given how you're feeling right now, lean on that, "
                 "don't argue with it.")
    return base + extra


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _card_html(voice, message, cite_line, used_llm, provider, moment,
               perceive, pulse, nudge, breath, sat, pulse_once):
    label, color = VOICE_META.get(voice, ("Companion", "#8893AB"))
    msg = _e(message).replace("\n", "<br>")
    ai = '<span class="plc-ai">ai</span>' if used_llm else ""
    via = ('<span class="plc-via">via ' + _e(provider) + '</span>') \
        if (used_llm and provider) else ""
    flash = '<div class="plc-flash"></div>' if pulse_once else ""
    moment_html = ('<div class="plc-moment"><span class="plc-moment-dot">'
                   '</span>' + _e(moment) + '</div>') if moment else ""
    perceive_html = ('<div class="plc-perceive">' + _e(perceive)
                     + '</div>') if (perceive and not used_llm) else ""
    pulse_html = ('<div class="plc-pulse">↻ ' + _e(pulse)
                  + '</div>') if (pulse and not used_llm) else ""
    nudge_html = ('<div class="plc-nudge"><span class="arr">→</span>'
                  '<span>' + _e(nudge) + '</span></div>') if nudge else ""
    cite_html = ('<div class="plc-cite">' + _e(cite_line)
                 + '</div>') if cite_line else ""
    breath_s = format(float(breath), ".1f")
    sat_v = format(float(sat), ".2f")
    return (
        _STYLE
        + '<div class="plc" style="--plc:' + color + ';--plc-breath:'
        + breath_s + 's;--plc-sat:' + sat_v + '">'
        + '<div class="plc-grain"></div><div class="plc-sheen"></div>'
        + '<div class="plc-rail"></div><div class="plc-halo"></div>'
        + flash
        + '<span class="plc-tune-hint">✎</span>'
        + '<div class="plc-head"><span class="plc-mark">PULSE</span>'
        + '<span class="plc-voice">' + _e(label) + '</span>' + ai
        + via + '</div>'
        + moment_html
        + '<div class="plc-body"><span class="plc-quote">“</span>'
        + '<p class="plc-line">' + msg + '</p></div>'
        + perceive_html + pulse_html + nudge_html + cite_html
        + '</div>'
    )


def _extras(pkt, voice, idx, fb, refl, state, allow_money, meta):
    with st.expander("·  tune this voice  ·"):
        st.caption(
            "PULSE learns quietly from what you do after it speaks - you "
            "rarely need to touch this. Open it to teach a preference, or "
            "to ask anything. There is no like or dislike here on purpose: "
            "rating a presence trains you to stand outside it.")
        g = meta.get("grounds") or []
        if g:
            st.markdown(
                '<div class="plc-grounds-list">grounded on: '
                + " · ".join(_e(x) for x in g) + '</div>',
                unsafe_allow_html=True)
        if _HAS_BRAIN:
            summ = _B.taste_summary(state, voice,
                                    pkt.get("mood_band", "none"))
            if summ:
                st.markdown(
                    '<div class="plc-taste">what PULSE has learned here: '
                    + _e(summ) + '</div>', unsafe_allow_html=True)
        with st.form("plc_tune_" + voice):
            chips = st.multiselect(
                "lean the next one toward", _TUNE_CHIPS,
                key="plc_tc_" + voice)
            note = st.text_input(
                "or in your own words - what should it have leaned toward?",
                key="plc_tn_" + voice)
            ok = st.form_submit_button("save tune")
            if ok and (chips or (note or "").strip()):
                rec = {
                    "ts": U.now_local().isoformat(), "kind": "tune",
                    "page": voice, "mood_band": pkt.get("mood_band", "none"),
                    "features": meta.get("moves", []),
                    "note": (note or "").strip(), "chips": chips,
                    "rtags": [], "rsrc": "",
                }
                if _HAS_BRAIN:
                    _B.apply_tune(state, fb, rec)
                    _B.save_state(state)
                st.session_state["plc_pulse_once"] = True
                st.success("Tuned. PULSE will lean that way next time.")
                st.rerun()
        q = st.text_input(
            "ask PULSE anything", key="plc_ask_" + voice,
            placeholder="e.g. should I top up fun this week?")
        if st.button("ask", key="plc_go_" + voice):
            qq = (q or "").strip()
            if qq:
                ans, _pn = _llm_answer(pkt, voice, qq, idx, fb, refl,
                                       state, allow_money)
                if ans:
                    st.markdown(
                        '<div class="plc-ans">'
                        + _e(ans).replace("\n", "<br>") + '</div>',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div class="plc-ans">'
                        + _e(_offline_answer(pkt, qq, idx, fb,
                                             allow_money, refl, state))
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
            "**Make PULSE speak with a real model (optional, free tiers).** "
            "Add a [llm] table to Streamlit Cloud → Settings → Secrets with "
            "any of: groq_key, gemini_key, openrouter_key, cerebras_key, "
            "github_key, openai_key (see README for the full template). "
            "Without any key, PULSE still talks, grounded in your log and "
            "its own memory, and the ask-box answers offline.")
    with st.expander("Memory & training (the brain)"):
        if not _HAS_BRAIN:
            st.caption("The brain module is not loaded; the companion is "
                       "running on its built-in voice only.")
        else:
            idx = _get_index(ctx, True)
            fb = _get_feedback()
            refl = _get_reflection(ctx)
            state = _get_state()
            health = _B.memory_health(idx, state, fb, refl)
            provs = []
            if _HAS_ROUTER:
                try:
                    hs = _R.health_summary()
                    for name, info in hs.items():
                        ms = info.get("last_ms", 0)
                        mdl = info.get("model", "")
                        cooled = info.get("cooled", False)
                        line = name + " · " + str(ms) + "ms · " + mdl
                        if cooled:
                            line = line + " · cooling"
                        provs.append(line)
                except Exception:
                    pass
            lf = int(st.session_state.get("_plc_lf", 0) or 0)
            cells = (
                '<div class="plc-health">'
                + '<div><div class="k">memories indexed</div><div class="v">'
                + str(health.get("memories", 0)) + '</div></div>'
                + '<div><div class="k">semantic coverage</div><div class="v">'
                + str(health.get("semantic_pct", 0)) + '%</div></div>'
                + '<div><div class="k">threads detected</div><div class="v">'
                + str(health.get("threads", 0)) + '</div></div>'
                + '<div><div class="k">taste convergence</div><div class="v">'
                + str(health.get("taste_convergence_pct", 0)) + '%</div></div>'
                + '<div><div class="k">tunes recorded</div><div class="v">'
                + str(health.get("tunes", 0)) + '</div></div>'
                + '<div><div class="k">live facts this render</div><div class="v">'
                + str(lf) + '</div></div>'
                + '<div><div class="k">providers live</div><div class="v">'
                + str(len(provs)) + '</div></div>'
                + '<div><div class="k">page registers</div><div class="v">9</div></div>'
                + '</div>'
            )
            st.markdown(cells, unsafe_allow_html=True)
            if provs:
                st.caption("last response latency: " + " | ".join(provs))
            st.caption("Nine pages, nine voices - each speaks only in its "
                       "own register, recomputed on every edit.")
            sups = _B.learned_suppressions(fb, list(VOICE_META.keys()))
            if sups:
                st.caption("PULSE has learned to hold back these moves:")
                for s in sups:
                    st.markdown('- in **' + _e(s["page"]) + '** when **'
                                + _e(s["mood_band"]) + '**: '
                                + _e(s["feature"]),
                                unsafe_allow_html=True)
            else:
                st.caption("No learned suppressions yet. Use the tune "
                           "drawer under any message to teach a taste.")
            ca, cb, cc = st.columns(3)
            with ca:
                if st.button("Rebuild memory index", key="plc_rebuild"):
                    _B.rebuild(_stores(ctx, True))
                    st.success("Memory rebuilt.")
                    st.rerun()
            with cb:
                if st.button("Reset learned taste", key="plc_resetfb"):
                    _B.reset_feedback()
                    st.success("Taste and tunes cleared.")
                    st.rerun()
            with cc:
                st.download_button(
                    "Export brain (.json)",
                    json.dumps({"index": idx, "feedback": fb,
                                "reflection": refl, "state": state},
                               default=str),
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
        state = _get_state()
        if _HAS_BRAIN:
            try:
                _B.reconcile_implicit(state, _stores(ctx, True), fb)
                _B.save_state(state)
            except Exception:
                pass
        page_stats = _page_stats(ctx, voice, allow_money)
        pkt["_live"] = page_stats.get("live", {})
        pkt["_ps"] = page_stats
        perc = {}
        if _HAS_PERC:
            try:
                perc = _P.perceive(pkt, voice, page_stats, allow_money) or {}
            except Exception:
                perc = {}
        thread = ""
        if _HAS_BRAIN:
            try:
                thread = _B.thread_for(pkt, refl) or ""
            except Exception:
                thread = ""
        cand = [c for c in [thread, perc.get("line", ""),
                            perc.get("alt", "")] if c]
        pr = state.setdefault("page_recent", {}) \
            if isinstance(state, dict) else {}
        recent = pr.get(voice, []) if isinstance(pr, dict) else []
        pick = ""
        for c in cand:
            if c not in recent:
                pick = c
                break
        if not pick and cand:
            pick = cand[0]
        if isinstance(pr, dict):
            pr[voice] = [pick] if pick else []
            if isinstance(state, dict):
                state["page_recent"] = pr
        if _HAS_BRAIN and isinstance(state, dict):
            try:
                _B.save_state(state)
            except Exception:
                pass
        pulse_once = bool(st.session_state.pop("plc_pulse_once", False))
        extra = dict(perc=perc, perceive_chosen=pick, thread=thread)
        msg, used, meta = _compose(pkt, voice, idx, fb, refl, state,
                                   allow_money, extra)
        lf = len(meta.get("grounds", []))
        if meta.get("moment"):
            lf = lf + 1
        if meta.get("perceive"):
            lf = lf + 1
        if meta.get("nudge"):
            lf = lf + 1
        if meta.get("pulse"):
            lf = lf + 1
        st.session_state["_plc_lf"] = lf
        if _HAS_BRAIN:
            try:
                _B.note_surfaced(state, voice,
                                 pkt.get("mood_band", "none"),
                                 meta.get("moves", []),
                                 meta.get("refs", []))
                _B.save_state(state)
            except Exception:
                pass
        st.markdown(_card_html(
            voice, msg, meta.get("cite_line", ""), used,
            meta.get("provider"), meta.get("moment", ""),
            meta.get("perceive", ""), meta.get("pulse", ""),
            meta.get("nudge", ""), meta.get("breath", 5.0),
            meta.get("sat", 1.0), pulse_once),
            unsafe_allow_html=True)
        try:
            _extras(pkt, voice, idx, fb, refl, state, allow_money, meta)
        except Exception:
            pass
        if voice == "quiet":
            try:
                _companion_settings(ctx)
            except Exception:
                pass
    except Exception:
        try:
            st.markdown(_card_html(
                voice or "morning",
                "I'm here. (the companion hit a snag - your data is safe.)",
                "", False, None, "", "", "", "", 5.0, 1.0, False),
                unsafe_allow_html=True)
        except Exception:
            pass
