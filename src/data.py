"""Empty-on-purpose, editable, persisted life + business + money + spirit data.
Recording starts Friday 1 August 2026 (Nairobi). Nothing is faked.
Two locks. The outer vault (ARCHIVE_PIN) holds everyday money. Inside it, two
sealed chambers - Pantry and Reserve - sit behind DEEP_PIN, the protected
heart: food security on one side, the emergency ring-fence plus any venture
you choose to seal on the other. Sealing a venture moves it out of active
money; the system never auto-deducts food or cash.
Also carries the Signals engine constants (CONNECTIONS / EVENT_*), the events
ledger, habit auto-fill helpers and the TrueWave journey fields.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import uuid
from pathlib import Path

import streamlit as st

from . import util as U

DATA = Path(__file__).resolve().parent.parent / "data"
START_DATE = dt.date(2026, 8, 1)
DEFAULT_NAME = "Mwangi.Alex"
ARCHIVE_PIN = "0444"
DEEP_PIN = "4440"
CASH_CREDIT = "CASH OFFER - CREDIT"

RESTORE_KEYS = ["pipeline", "routine", "habits", "habit_log", "goals",
                "issues", "journal", "weights", "clients", "sales_daily",
                "sales", "income", "tasks", "bots", "vault", "spiritual",
                "events"]

# ---------------------------------------------------------------------------
# Signals engine - declarative map of what each event ripples into, plus the
# labels / colours the Signals page renders. Self-contained so the page can
# never crash on a missing constant.
# ---------------------------------------------------------------------------
CONNECTIONS = {
    "client_added": [
        ("pipeline", "enters the active pipeline + call sheet"),
        ("journal", "shows in Day Pulse as a new inquiry"),
        ("signals", "logged on the Signals feed"),
    ],
    "stage_moved": [
        ("pipeline", "pipeline counts + funnel re-flow instantly"),
        ("callsheet", "call sheet re-sorts by next action"),
        ("journal", "client touch lands in Day Pulse"),
        ("signals", "logged on the Signals feed"),
    ],
    "client_called": [
        ("callsheet", "drops off today's Call Sheet immediately"),
        ("pipeline", "next call auto-scheduled to the chosen day"),
        ("journal", "logged as a client touch"),
        ("signals", "logged on the Signals feed"),
    ],
    "credit_cash_offer": [
        ("cash_queue", "auto-loads into the Cash-Offer Queue (rejected)"),
        ("task", "auto-creates a cash-offer follow-up task"),
        ("pipeline", "removed from the active pipeline - it is a rejection"),
        ("signals", "highlighted on the Signals feed"),
    ],
    "client_delivered": [
        ("window", "7-day return window opens"),
        ("commission", "commission windows start (+20/+50)"),
        ("journal", "logged as an outcome"),
    ],
    "client_paid": [
        ("sold", "Paid & Closed increments everywhere"),
        ("cash_queue", "leaves the Cash-Offer Queue - it is won"),
        ("income", "ready to record as Commission income"),
        ("stats", "TrueWave KPIs update"),
    ],
    "client_returned": [
        ("returned", "Returned increments + window closes"),
        ("cash_queue", "leaves the Cash-Offer Queue"),
        ("journal", "logged as an outcome"),
    ],
    "journey_ended": [
        ("pipeline", "leaves call sheet, active count, follow-ups"),
        ("cash_queue", "STAYS in the Cash-Offer Queue - rejection list"),
        ("journal", "removed from live Day Pulse"),
        ("signals", "logged on the Signals feed"),
    ],
    "journey_reopened": [
        ("pipeline", "re-enters the active pipeline"),
        ("signals", "logged on the Signals feed"),
    ],
    "sale_logged": [
        ("commission", "instalments auto-due +20/+50 days"),
        ("income", "pending commission tracked"),
        ("journal", "appears in Day Pulse"),
        ("stats", "sales KPIs update"),
    ],
    "commission_paid": [
        ("vault", "cash drops into the chosen pocket (live)"),
        ("flow", "a Daily Flow entry is written"),
        ("stats", "collected commissions update"),
    ],
    "income_added": [
        ("vault", "optionally drops into a pocket"),
        ("stats", "income-by-source updates"),
    ],
    "task_added": [
        ("focus", "appears on Tasks + Focus voice"),
        ("now", "counts on the Now dashboard"),
    ],
}
EVENT_LABELS = {
    "client_added": "Lead logged", "stage_moved": "Stage moved",
    "client_called": "Called & rescheduled",
    "credit_cash_offer": "Cash offer issued",
    "credit_set": "Credit outcome", "client_delivered": "Delivered",
    "client_paid": "Paid & closed", "client_returned": "Returned",
    "journey_ended": "Journey ended",
    "journey_reopened": "Journey reopened",
    "sale_logged": "Sale logged",
    "commission_paid": "Commission collected",
    "income_added": "Income recorded", "task_added": "Task created",
    "touch": "Client touch", "plan_set": "Plan chosen", "note": "Note",
}
EVENT_COLOR = {
    "client_added": "#4C8DFF", "stage_moved": "#2DD4BF",
    "client_called": "#38BDF8", "credit_cash_offer": "#F5B544",
    "credit_set": "#8B7CFF", "client_delivered": "#2DD4BF",
    "client_paid": "#34D399", "client_returned": "#F0556B",
    "journey_ended": "#7C8AA5", "journey_reopened": "#34D399",
    "sale_logged": "#34D399", "commission_paid": "#34D399",
    "income_added": "#34D399", "task_added": "#8B7CFF",
    "touch": "#2DD4BF", "plan_set": "#38BDF8", "note": "#8893AB",
}

TAG_COLORS = {
    "Content": "#4C8DFF", "Sales": "#2DD4BF", "Body": "#34D399",
    "Mind": "#D946EF", "Life": "#F5B544", "Rest": "#7C8AA5",
    "Focus": "#8B7CFF",
}
ACCENTS = {
    "Electric Blue": "#4C8DFF", "Terminal Teal": "#2DD4BF",
    "Signal Violet": "#8B7CFF", "Amber Edge": "#F5B544",
}
MOODS = ["drained", "flat", "steady", "sharp", "on fire"]
DAY_ABBR = {"mon": 0, "tue": 1, "wed": 2, "thu": 3,
            "fri": 4, "sat": 5, "sun": 6}
ROLES = ["", "won", "lost", "cash", "delivered", "returned"]
ROLE_LABEL = {
    "": "— (none)", "won": "Closed won", "lost": "Closed lost",
    "cash": "Cash-offer hold", "delivered": "Delivered (window)",
    "returned": "Returned",
}
TERMINAL_ROLES = {"won", "lost", "returned"}
SOURCES = ["Facebook Ads", "TikTok Live", "TikTok DM", "Instagram",
           "WhatsApp", "Walk-in", "Referral", "Outbound Call"]
HEATS = ["Hot", "Warm", "Cold"]
DOC_ITEMS = ["id_card", "selfie", "next_of_kin"]
DOC_LABEL = {"id_card": "ID Card", "selfie": "Clear Selfie",
             "next_of_kin": "Next of Kin"}
DOC_STATES = ["pending", "passed", "failed"]
CREDIT_OUTCOMES = ["pending", "APPROVED", "CASH OFFER - CREDIT",
                   "PLAN CHANGE", "DECLINED"]
COMM_WINDOWS = {1: 20, 2: 50}
INCOME_TYPES = ["Commission", "Bonus", "DRV Streamlit",
                "Stock Streamlit", "Gift", "Other"]
PANTRY_CATS = ["staple", "protein", "drink", "treat", "other"]
PANTRY_SEED = [
    ("ugali", "Ugali (maize flour)", "g", 2000.0, 500.0, "staple", False),
    ("omena", "Omena", "g", 1000.0, 100.0, "protein", False),
    ("eggs", "Eggs", "pcs", 30.0, 5.0, "protein", False),
    ("milk", "Milk (porridge)", "ml", 1500.0, 500.0, "drink", False),
    ("coffee", "Coffee", "g", 112.0, 8.0, "drink", False),
    ("smoothie", "Smoothie pack", "pcs", 0.0, 1.0, "treat", True),
    ("oil", "Cooking oil", "ml", 750.0, 15.0, "staple", True),
]
RUNWAY_SEED = {"monthly_burn": 0.0, "emergency_months": 3}
SPIRIT_ACTS = ["Prayer", "Reading", "Worship", "Fasting", "Silence",
               "Serving", "Giving", "Prayer walk"]
SPIRIT_DEPTHS = [1, 2, 3, 4, 5]
ROUTINE_SEED = [
    ("06:00", "Wake up", "Life", "weekdays"),
    ("06:10", "Morning coffee", "Life", "weekdays"),
    ("06:20", "Brush teeth", "Body", "weekdays"),
    ("06:30", "Clean yesterday's clothes", "Life", "weekdays"),
    ("07:00", "Mop the house", "Life", "weekdays"),
    ("07:30", "Shower", "Body", "weekdays"),
    ("08:00", "Commute to work", "Life", "weekdays"),
    ("09:30", "Arrive - post TikTok drafts", "Content", "weekdays"),
    ("10:00", "Schedule FB + IG drafts", "Content", "weekdays"),
    ("10:30", "Tea - stories - reply DMs", "Content", "weekdays"),
    ("11:15", "Call urgent buyers (if clear)", "Sales", "weekdays"),
    ("12:00", "TikTok Live + lunch calls", "Content", "weekdays"),
    ("13:00", "Follow-up calls - urgent push", "Sales", "weekdays"),
    ("15:00", "Log promised clients + remarks", "Sales", "weekdays"),
    ("15:30", "Schedule tomorrow's TikToks", "Content", "weekdays"),
    ("16:30", "Bus home", "Life", "weekdays"),
    ("18:30", "Home - unwind", "Rest", "weekdays"),
    ("19:00", "Music - free creative time", "Rest", "all"),
    ("20:00", "Workout - 45 min", "Body", "all"),
    ("20:45", "Shower", "Body", "all"),
    ("21:00", "Wind down - no screens", "Rest", "all"),
    ("22:00", "Sleep", "Rest", "all"),
    ("07:00", "Wake up + breakfast", "Life", "sat"),
    ("07:45", "Music", "Rest", "sat"),
    ("08:15", "Clean beddings", "Life", "sat"),
    ("09:00", "Clean house", "Life", "sat"),
    ("09:45", "Shower", "Body", "sat"),
    ("10:15", "Head out - work from location", "Life", "sat"),
    ("10:30", "Post TikTok drafts", "Content", "sat"),
    ("11:00", "Schedule FB + IG", "Content", "sat"),
    ("11:30", "Stories + DMs", "Content", "sat"),
    ("12:00", "Lunch + calls", "Sales", "sat"),
    ("13:00", "Follow-up calls - urgent push", "Sales", "sat"),
    ("15:00", "Log promised clients + remarks", "Sales", "sat"),
    ("15:30", "Schedule tomorrow's TikToks", "Content", "sat"),
    ("17:00", "Head home", "Life", "sat"),
    ("18:00", "Cool off", "Rest", "sat"),
    ("08:00", "Slow morning", "Life", "sun"),
    ("09:00", "Breakfast", "Life", "sun"),
    ("10:00", "Free - whatever the day asks", "Rest", "sun"),
    ("13:00", "Lunch", "Life", "sun"),
    ("14:00", "Out / free time", "Rest", "sun"),
    ("18:00", "Evening unwind", "Rest", "sun"),
]
HABITS_SEED = [
    ("W", "Workout 45 min"), ("J", "Journal the day"),
    ("S", "Log sales + rejections"), ("C", "Log client follow-ups"),
    ("G", "Weigh-in"), ("R", "Morning routine done"),
    ("L", "Lights out by 10"),
]
BOT_SEED = [
    ("deriv", "Deriv Bot", "Deriv - 24/7 Streamlit", "testing"),
    ("alpaca", "Alpaca Bot", "Alpaca stocks - 24/7 Streamlit", "testing"),
]
POSITION_SEED = [("wallet", "Cash Wallet"), ("mpesa", "M-Pesa"),
                 ("bank", "Bank Account")]
BILL_SEED = [("rent", "Rent"), ("power", "Power (KPLC)"),
             ("water", "Water"), ("internet", "Internet / WiFi"),
             ("food", "Food & Shopping"), ("transport", "Transport")]
FUND_SEED = [("hho", "HHO Carbon Cleaning - Nairobi",
              150000.0, 200000.0, "2027-01-31")]


def _uid():
    return str(uuid.uuid4())[:8]


def _read(name):
    try:
        f = DATA / name
        if f.exists() and f.stat().st_size > 0:
            return json.loads(f.read_text())
    except Exception:
        pass
    return None


def _write(name, obj):
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        (DATA / name).write_text(json.dumps(obj, default=str))
    except Exception:
        pass


def _scope_days(token):
    t = (token or "all").strip().lower().lstrip("@")
    if t in ("all", "everyday", ""):
        return list(range(7))
    if t == "weekdays":
        return list(range(5))
    if t == "weekend":
        return [5, 6]
    out = []
    for p in re.split(r"[,\s]+", t):
        if p[:3] in DAY_ABBR:
            out.append(DAY_ABBR[p[:3]])
    return sorted(set(out)) or list(range(7))


def parse_routine_text(text):
    blocks = []
    for raw in str(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(\d{1,2}):(\d{2})\s*(AM|PM)?\s*[-|]?\s*(.+)$",
                     line, re.I)
        if not m:
            continue
        hh, mm = int(m.group(1)), int(m.group(2))
        ap, rest = m.group(3), m.group(4).strip()
        if ap and ap.upper() == "PM" and hh != 12:
            hh += 12
        if ap and ap.upper() == "AM" and hh == 12:
            hh = 0
        tag, scope = "Life", "all"
        sm = re.search(r"@(\S+)", rest)
        if sm:
            scope = sm.group(1)
            rest = rest.replace(sm.group(0), " ").strip()
        tm = re.search(r"#(\w+)", rest)
        if tm:
            tag = tm.group(1).capitalize()
            rest = rest.replace(tm.group(0), " ").strip()
        if tag not in TAG_COLORS:
            tag = "Life"
        blocks.append({"time": str(hh).zfill(2) + ":" + str(mm).zfill(2),
                       "label": rest.strip(), "tag": tag,
                       "days": _scope_days(scope)})
    blocks.sort(key=lambda b: b["time"])
    return blocks


def routine_to_text(blocks):
    lines = []
    for b in blocks:
        if b["days"] == list(range(5)):
            scope = "weekdays"
        elif b["days"] == [5, 6]:
            scope = "weekend"
        elif b["days"] == list(range(7)):
            scope = "all"
        else:
            scope = ", ".join(k for k, v in DAY_ABBR.items()
                              if v in b["days"])
        lines.append(b["time"] + "   " + b["label"] + "  #" + b["tag"]
                     + "  @" + scope)
    return "\n".join(lines)


def parse_habits_text(text):
    out, seen = [], set()
    for raw in str(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        icon = parts[0] if parts else "*"
        name = parts[1] if len(parts) > 1 else parts[0]
        hid = U.slug(name)
        if hid not in seen:
            seen.add(hid)
            out.append({"id": hid, "icon": icon, "name": name})
    return out


def habits_to_text(habits):
    return "\n".join(h["icon"] + "  " + h["name"] for h in habits)


# ---------------------------------------------------------------------------
# habit auto-fill model: which habits map to REAL data, and which stay
# optional. The weigh-in is optional - it auto-ticks only on days a weigh-in
# was logged and never counts against consistency.
# ---------------------------------------------------------------------------
def habit_source(habit):
    name = str((habit or {}).get("name", "") or "").lower()
    if "journal" in name:
        return "journal"
    if "sales" in name or "rejection" in name:
        return "sales"
    if "client" in name or "follow" in name:
        return "clients"
    if "weigh" in name or "weight" in name:
        return "weigh"
    return None


def habit_optional(habit):
    return habit_source(habit) == "weigh"


def _seed_routine():
    return [{"time": t, "label": l, "tag": tg, "days": _scope_days(sc)}
            for (t, l, tg, sc) in ROUTINE_SEED]


def _seed_habits():
    return [{"id": U.slug(n), "icon": i, "name": n}
            for (i, n) in HABITS_SEED]


def _seed_bots():
    return {"bots": [{"id": bid, "name": nm, "platform": pf,
                      "status": stt, "live_date": "", "notes": ""}
                     for (bid, nm, pf, stt) in BOT_SEED], "logs": []}


def _seed_pantry():
    return {"items": [
        {"id": i, "name": n, "unit": u, "stock": float(s),
         "daily": float(d), "category": c, "hidden": bool(h),
         "checked": ""} for (i, n, u, s, d, c, h) in PANTRY_SEED],
        "updated": ""}


def _seed_vault():
    return {
        "positions": [{"id": pid, "name": nm, "balance": 0.0, "tx": []}
                      for (pid, nm) in POSITION_SEED],
        "bills": [{"id": bid, "name": nm, "need": 0.0, "saved": 0.0,
                   "due": "", "paid": False, "paid_date": "", "tx": []}
                  for (bid, nm) in BILL_SEED],
        "fun": {"budget": 0.0, "used": 0.0, "tx": []},
        "items": [],
        "funds": [{"id": fid, "name": nm, "target_lo": lo,
                   "target_hi": hi, "deadline": dl, "balance": 0.0,
                   "sealed": False, "tx": []}
                  for (fid, nm, lo, hi, dl) in FUND_SEED],
        "flow": [], "snapshots": [], "pantry": _seed_pantry(),
        "runway": dict(RUNWAY_SEED),
        "emergency": {"balance": 0.0, "tx": []},
    }


def _seed_pipeline():
    stages = [
        ("new", "New Lead", "#4C8DFF", True, ""),
        ("no_pickup", "Called - No Pickup", "#F5B544", False, ""),
        ("picked", "In Conversation", "#2DD4BF", True, ""),
        ("declined_call", "Declined on Call", "#F0556B", False, ""),
        ("application", "Application Started", "#8B7CFF", True, ""),
        ("mpesa_review", "M-Pesa Review", "#D946EF", True, ""),
        ("plan_choice", "Plan Selection", "#38BDF8", True, ""),
        ("docs", "Docs Check", "#F5B544", True, ""),
        ("credit_call", "Credit Review Call", "#F0556B", True, ""),
        ("cash_offer", "Cash Offer - Credit", "#F5B544", False, "cash"),
        ("deposit", "Deposit & Delivery", "#34D399", True, ""),
        ("delivered", "Delivered - Window Open", "#2DD4BF", True,
         "delivered"),
        ("paid", "Paid & Closed", "#34D399", True, "won"),
        ("returned", "Returned", "#F0556B", False, "returned"),
        ("lost", "Lost / Declined", "#7C8AA5", False, "lost"),
    ]
    plans = [
        ("std", "Standard (12 mo)", "12 months - standard weekly"),
        ("lite", "Lite (12 mo)",
         "12 months - lower weekly, slightly higher total"),
        ("saver", "Saver (6 mo)",
         "6 months - higher deposit + higher weekly"),
    ]
    return {"stages": [{"id": i, "label": l, "color": c, "track": tr,
                        "role": ro} for (i, l, c, tr, ro) in stages],
            "plans": [{"id": i, "label": l, "note": n}
                      for (i, l, n) in plans]}


def get_pipeline_obj():
    return st.session_state.get("pipeline") or _seed_pipeline()


def save_pipeline_obj(o):
    st.session_state["pipeline"] = o
    _write("pipeline.json", o)


def get_stages():
    return get_pipeline_obj().get("stages", [])


def get_plans():
    return get_pipeline_obj().get("plans", [])


def all_stage_ids():
    return [s["id"] for s in get_stages()]


def _stage(sid):
    for s in get_stages():
        if s["id"] == sid:
            return s
    return None


def stage_label(sid, default="?"):
    s = _stage(sid)
    if s:
        return s.get("label") or str(sid)
    return str(sid) if default is None else default


def stage_color(sid, default="#7C8AA5"):
    s = _stage(sid)
    return s.get("color", default) if s else default


def stage_role(sid):
    s = _stage(sid)
    return s.get("role", "") if s else ""


def role_id(role):
    for s in get_stages():
        if s.get("role") == role:
            return s["id"]
    return None


def terminal_ids():
    return [s["id"] for s in get_stages()
            if s.get("role") in TERMINAL_ROLES]


def journey_ids():
    return [s["id"] for s in get_stages() if s.get("track")]


def is_cash_offer(c):
    """Cash-offer (rejected) clients. They are NOT in the active pipeline;
    they live in their own queue and only leave it via a terminal stage."""
    if not isinstance(c, dict):
        return False
    if c.get("stage", "") in terminal_ids():
        return False
    if stage_role(c.get("stage", "")) == "cash":
        return True
    if str(c.get("credit", "") or "").upper() == CASH_CREDIT:
        return True
    if str(c.get("pre_credit", "") or "").upper() == CASH_CREDIT:
        return True
    return False


def is_active_pipeline(c):
    if not isinstance(c, dict):
        return False
    if c.get("ended"):
        return False
    if c.get("stage", "") in terminal_ids():
        return False
    if is_cash_offer(c):
        return False
    return True


def plan_note(label):
    for p in get_plans():
        if p.get("label") == label:
            return p.get("note", "")
    return ""


def _ensure_key(key, fname, factory):
    if key not in st.session_state:
        st.session_state[key] = _read(fname) or factory()


def _migrate_vault(v):
    dirty = False
    for k, fab in (("positions", lambda: [
            {"id": pid, "name": nm, "balance": 0.0, "tx": []}
            for (pid, nm) in POSITION_SEED]),
            ("bills", lambda: [
                {"id": bid, "name": nm, "need": 0.0, "saved": 0.0,
                 "due": "", "paid": False, "paid_date": "", "tx": []}
                for (bid, nm) in BILL_SEED]),
            ("fun", lambda: {"budget": 0.0, "used": 0.0, "tx": []}),
            ("items", list),
            ("funds", lambda: [
                {"id": fid, "name": nm, "target_lo": lo, "target_hi": hi,
                 "deadline": dl, "balance": 0.0, "sealed": False,
                 "tx": []} for (fid, nm, lo, hi, dl) in FUND_SEED]),
            ("flow", list), ("snapshots", list),
            ("pantry", _seed_pantry),
            ("runway", lambda: dict(RUNWAY_SEED)),
            ("emergency", lambda: {"balance": 0.0, "tx": []})):
        if k not in v:
            v[k] = fab()
            dirty = True
    for it in v.get("pantry", {}).get("items", []):
        if "checked" not in it:
            it["checked"] = ""
            dirty = True
        if "hidden" not in it:
            it["hidden"] = False
            dirty = True
    for f in v.get("funds", []):
        if "sealed" not in f:
            f["sealed"] = False
            dirty = True
    if dirty:
        _write("vault.json", v)


def ensure():
    prefs = _read("prefs.json") or {}
    _ensure_key("pipeline", "pipeline.json", _seed_pipeline)
    _ensure_key("routine", "routine.json", _seed_routine)
    _ensure_key("habits", "habits.json", _seed_habits)
    _ensure_key("habit_log", "habit_log.json", dict)
    _ensure_key("goals", "goals.json", list)
    _ensure_key("issues", "issues.json", list)
    _ensure_key("journal", "journal.json", dict)
    _ensure_key("weights", "weights.json", list)
    _ensure_key("clients", "clients.json", list)
    _ensure_key("sales_daily", "sales_daily.json", dict)
    _ensure_key("sales", "sales.json", list)
    _ensure_key("income", "income.json", list)
    _ensure_key("tasks", "tasks.json", list)
    _ensure_key("bots", "bots.json", _seed_bots)
    _ensure_key("vault", "vault.json", _seed_vault)
    _ensure_key("spiritual", "spiritual.json", dict)
    _ensure_key("events", "events.json", list)
    _migrate_vault(st.session_state["vault"])
    st.session_state.setdefault("name", prefs.get("name", DEFAULT_NAME))
    st.session_state.setdefault("accent",
                                prefs.get("accent", "#4C8DFF"))
    st.session_state.setdefault("tz_offset",
                                float(prefs.get("tz_offset", 0)))


def get(k):
    if k in st.session_state:
        return st.session_state[k]
    if k in ("events", "goals", "issues", "weights", "clients",
             "sales", "income", "tasks"):
        return []
    if k in ("habit_log", "journal", "sales_daily", "vault",
             "spiritual"):
        return {}
    return None


def _save_prefs():
    _write("prefs.json", {
        "name": st.session_state.get("name"),
        "accent": st.session_state.get("accent"),
        "tz_offset": st.session_state.get("tz_offset", 0),
    })


def set_pref(key, value):
    st.session_state[key] = value
    _save_prefs()


def save_routine(x):
    st.session_state["routine"] = x
    _write("routine.json", x)


def save_habits(x):
    st.session_state["habits"] = x
    _write("habits.json", x)


def save_habit_log(x):
    st.session_state["habit_log"] = x
    _write("habit_log.json", x)


def save_goals(x):
    st.session_state["goals"] = x
    _write("goals.json", x)


def save_issues(x):
    st.session_state["issues"] = x
    _write("issues.json", x)


def save_journal(x):
    st.session_state["journal"] = x
    _write("journal.json", x)


def save_weights(x):
    st.session_state["weights"] = x
    _write("weights.json", x)


def save_clients(x):
    st.session_state["clients"] = x
    _write("clients.json", x)


def save_sales_daily(x):
    st.session_state["sales_daily"] = x
    _write("sales_daily.json", x)


def save_sales(x):
    st.session_state["sales"] = x
    _write("sales.json", x)


def save_income(x):
    st.session_state["income"] = x
    _write("income.json", x)


def save_tasks(x):
    st.session_state["tasks"] = x
    _write("tasks.json", x)


def save_bots(x):
    st.session_state["bots"] = x
    _write("bots.json", x)


def save_vault(x):
    st.session_state["vault"] = x
    _write("vault.json", x)


def save_spiritual(x):
    st.session_state["spiritual"] = x
    _write("spiritual.json", x)


# ---------- events ledger (Signals feed) ----------
def save_events(x):
    st.session_state["events"] = x
    _write("events.json", x)


def get_events():
    v = st.session_state.get("events")
    if isinstance(v, list):
        return v
    return []


def add_event(date_iso, time_str, title, note=""):
    ev = list(get_events())
    ev.insert(0, {"id": _uid(), "date": date_iso, "time": time_str,
                  "title": title, "note": note, "done": False})
    save_events(ev)


# ---------- the single writer that moves real money ----------
def move_money(pocket_id, effect, kind, note="", time_str="",
               txid="", date_iso=None):
    v = st.session_state["vault"]
    p = None
    for x in v.get("positions", []):
        if x["id"] == pocket_id:
            p = x
            break
    if p is None:
        return
    eff = float(effect)
    p["balance"] = float(p.get("balance", 0)) + eff
    d = date_iso or U.today_local().isoformat()
    rec = {"id": _uid(), "date": d, "time": time_str or "",
           "txid": txid or "", "kind": kind, "amount": eff,
           "note": note}
    p.setdefault("tx", []).insert(0, dict(rec))
    flow_rec = dict(rec)
    flow_rec["id"] = _uid()
    flow_rec["pocket"] = pocket_id
    v.setdefault("flow", []).insert(0, flow_rec)
    _snap(v)
    save_vault(v)


def pos_tx(pid, kind, amount, note=""):
    eff = float(amount) if kind == "in" else -float(amount)
    move_money(pid, eff, kind, note=note,
               time_str=U.now_local().strftime("%H:%M"), txid="")


def add_position(name):
    v = st.session_state["vault"]
    v["positions"].append({"id": U.slug(name), "name": name,
                           "balance": 0.0, "tx": []})
    save_vault(v)


# ---------- bills / fun / items / funds ----------
def bill_tx(bid, kind, amount):
    v = st.session_state["vault"]
    for b in v["bills"]:
        if b["id"] == bid:
            amt = float(amount)
            if kind == "save":
                b["saved"] = float(b["saved"]) + amt
            else:
                b["saved"] = max(0.0, float(b["saved"]) - amt)
            b["tx"].insert(0, {"id": _uid(),
                               "date": U.today_local().isoformat(),
                               "kind": kind, "amount": amt})
    _snap(v)
    save_vault(v)


def add_bill(name, need, due):
    v = st.session_state["vault"]
    v["bills"].append({"id": U.slug(name), "name": name,
                       "need": float(need), "saved": 0.0, "due": due,
                       "paid": False, "paid_date": "", "tx": []})
    save_vault(v)


def set_bill(bid, need=None, due=None):
    v = st.session_state["vault"]
    for b in v["bills"]:
        if b["id"] == bid:
            if need is not None:
                b["need"] = float(need)
            if due is not None:
                b["due"] = due
    save_vault(v)


def bill_paid(bid, date_iso):
    v = st.session_state["vault"]
    for b in v["bills"]:
        if b["id"] == bid:
            b["paid"] = True
            b["paid_date"] = date_iso
    _snap(v)
    save_vault(v)


def bill_reopen(bid):
    v = st.session_state["vault"]
    for b in v["bills"]:
        if b["id"] == bid:
            b["paid"] = False
            b["paid_date"] = ""
            b["saved"] = 0.0
    _snap(v)
    save_vault(v)


def fun_tx(kind, amount, note=""):
    v = st.session_state["vault"]
    f = v["fun"]
    amt = float(amount)
    if kind == "add":
        f["budget"] = float(f["budget"]) + amt
    else:
        f["used"] = float(f["used"]) + amt
    f["tx"].insert(0, {"id": _uid(),
                       "date": U.today_local().isoformat(),
                       "kind": kind, "amount": amt, "note": note})
    _snap(v)
    save_vault(v)


def add_item(name, price):
    v = st.session_state["vault"]
    v["items"].insert(0, {"id": _uid(), "name": name,
                          "price": float(price), "tx": [],
                          "bought": False, "bought_date": ""})
    save_vault(v)


def item_tx(iid, amount):
    v = st.session_state["vault"]
    for it in v["items"]:
        if it["id"] == iid:
            it["tx"].append({"id": _uid(),
                             "date": U.today_local().isoformat(),
                             "amount": float(amount)})
    _snap(v)
    save_vault(v)


def buy_item(iid, date_iso):
    v = st.session_state["vault"]
    for it in v["items"]:
        if it["id"] == iid:
            it["bought"] = True
            it["bought_date"] = date_iso
    _snap(v)
    save_vault(v)


def fund_tx(fid, kind, amount, note=""):
    v = st.session_state["vault"]
    for f in v["funds"]:
        if f["id"] == fid:
            amt = float(amount)
            if kind == "in":
                f["balance"] = float(f["balance"]) + amt
            else:
                f["balance"] = max(0.0, float(f["balance"]) - amt)
            f["tx"].insert(0, {"id": _uid(),
                               "date": U.today_local().isoformat(),
                               "kind": kind, "amount": amt,
                               "note": note})
    _snap(v)
    save_vault(v)


def add_fund(name, target_lo, target_hi, deadline):
    v = st.session_state["vault"]
    v["funds"].append({"id": U.slug(name), "name": name,
                       "target_lo": float(target_lo),
                       "target_hi": float(target_hi),
                       "deadline": deadline, "balance": 0.0,
                       "sealed": False, "tx": []})
    save_vault(v)


def seal_fund(fid):
    v = st.session_state["vault"]
    for f in v.get("funds", []):
        if f["id"] == fid:
            f["sealed"] = True
    _snap(v)
    save_vault(v)


def unseal_fund(fid):
    v = st.session_state["vault"]
    for f in v.get("funds", []):
        if f["id"] == fid:
            f["sealed"] = False
    _snap(v)
    save_vault(v)


# ---------- pantry ----------
def _pantry(v):
    return v.setdefault("pantry", _seed_pantry())


def pantry_add(name, unit, daily, category, hidden, stock=0.0):
    v = st.session_state["vault"]
    pan = _pantry(v)
    nid = U.slug(name)
    base, kk = nid, 2
    while any(x["id"] == nid for x in pan["items"]):
        nid = base + str(kk)
        kk += 1
    now = U.today_local().isoformat()
    has = float(stock) > 0
    pan["items"].append({
        "id": nid, "name": name.strip(), "unit": unit.strip() or "u",
        "stock": float(stock), "daily": max(0.0, float(daily)),
        "category": category, "hidden": bool(hidden),
        "checked": (now if has else ""),
    })
    if has:
        pan["updated"] = now
    save_vault(v)


def pantry_set_stock(vid, stock):
    v = st.session_state["vault"]
    pan = _pantry(v)
    now = U.today_local().isoformat()
    for it in pan["items"]:
        if it["id"] == vid:
            it["stock"] = float(stock)
            it["checked"] = now
            pan["updated"] = now
    save_vault(v)


def pantry_save_details(vid, name, unit, daily, category, hidden,
                        stock=None):
    v = st.session_state["vault"]
    pan = _pantry(v)
    now = U.today_local().isoformat()
    for it in pan["items"]:
        if it["id"] == vid:
            it["name"] = name.strip() or it["name"]
            it["unit"] = unit.strip() or it["unit"]
            it["daily"] = max(0.0, float(daily))
            it["category"] = category
            it["hidden"] = bool(hidden)
            if stock is not None:
                it["stock"] = float(stock)
                it["checked"] = now
                pan["updated"] = now
    save_vault(v)


def pantry_toggle_hidden(vid):
    v = st.session_state["vault"]
    for it in _pantry(v)["items"]:
        if it["id"] == vid:
            it["hidden"] = not bool(it.get("hidden"))
    save_vault(v)


def pantry_remove(vid):
    v = st.session_state["vault"]
    pan = _pantry(v)
    pan["items"] = [x for x in pan["items"] if x["id"] != vid]
    save_vault(v)


# ---------- runway + emergency ----------
def set_runway(monthly_burn=None, emergency_months=None):
    v = st.session_state["vault"]
    r = v.setdefault("runway", dict(RUNWAY_SEED))
    if monthly_burn is not None:
        r["monthly_burn"] = max(0.0, float(monthly_burn))
    if emergency_months is not None:
        r["emergency_months"] = max(1, int(emergency_months))
    save_vault(v)


def _cash(v):
    return sum(float(p.get("balance", 0))
               for p in v.get("positions", []))


def emergency_tx(kind, amount, note=""):
    v = st.session_state["vault"]
    e = v.setdefault("emergency", {"balance": 0.0, "tx": []})
    amt = float(amount)
    cap = _cash(v)
    if kind == "in":
        applied = min(amt, max(0.0, cap - float(e["balance"])))
        e["balance"] = float(e["balance"]) + applied
    else:
        applied = min(amt, float(e["balance"]))
        e["balance"] = float(e["balance"]) - applied
    if applied > 0.0001:
        e["tx"].insert(0, {
            "id": _uid(), "date": U.today_local().isoformat(),
            "time": U.now_local().strftime("%H:%M"), "kind": kind,
            "amount": applied, "note": note,
        })
    save_vault(v)


def emergency_ratchet():
    v = st.session_state["vault"]
    r = v.setdefault("runway", dict(RUNWAY_SEED))
    r["emergency_months"] = int(r.get("emergency_months", 3)) + 1
    save_vault(v)


# ---------- clients ----------
def add_client(name, phone, source, heat, want, budget, note,
               today_iso, now_str, location=""):
    clients = list(st.session_state["clients"])
    ids = all_stage_ids()
    first = ids[0] if ids else "new"
    c = {
        "id": _uid(), "name": name, "phone": phone,
        "source": source, "heat": heat, "want": want,
        "budget": budget, "created": today_iso, "stage": first,
        "location": location, "plan": "", "qualified": "",
        "deposit": 0.0, "weekly": 0.0,
        "docs": {"id_card": "pending", "selfie": "pending",
                 "next_of_kin": "pending"},
        "pre_credit": "pending", "credit": "pending",
        "delivery": "pending", "hold_reason": "",
        "delivered_date": "", "paid": False, "paid_date": "",
        "returned": False, "returned_date": "", "return_outcome": "",
        "ended": False, "ended_date": "",
        "follow_at": "", "follow_done": False, "service": [],
        "next_action": "First call", "next_date": today_iso,
        "remark": "", "why_not": "",
        "history": [{"ts": now_str,
                     "note": note or ("Lead logged from " + source),
                     "stage": first}],
    }
    clients.insert(0, c)
    save_clients(clients)


def _find_client(cid):
    for c in st.session_state["clients"]:
        if c["id"] == cid:
            return c
    return None


def touch_client(cid, note, now_str):
    c = _find_client(cid)
    if c:
        c.setdefault("history", []).append(
            {"ts": now_str, "note": note, "stage": c.get("stage", "")})
        save_clients(st.session_state["clients"])


def set_stage(cid, stage, now_str, note=""):
    c = _find_client(cid)
    if c:
        c["stage"] = stage
        label = stage_label(stage, stage)
        c.setdefault("history", []).append(
            {"ts": now_str, "note": note or ("Stage -> " + label),
             "stage": stage})
        save_clients(st.session_state["clients"])


def update_client(cid, patch, now_str, log_note=""):
    c = _find_client(cid)
    if c:
        c.update(patch)
        if log_note:
            c.setdefault("history", []).append(
                {"ts": now_str, "note": log_note,
                 "stage": c.get("stage", "")})
        save_clients(st.session_state["clients"])


# ---------- goals / issues / weights / tasks ----------
def add_goal(g):
    goals = list(st.session_state["goals"])
    g = dict(g)
    g["id"] = _uid()
    goals.append(g)
    save_goals(goals)


def add_issue(text, area, due):
    issues = list(st.session_state["issues"])
    issues.insert(0, {"id": _uid(), "text": text, "area": area,
                      "due": due, "done": False})
    save_issues(issues)


def add_weight(date_iso, kg):
    ws = [w for w in st.session_state["weights"]
          if w["date"] != date_iso]
    ws.append({"date": date_iso, "kg": float(kg)})
    ws.sort(key=lambda w: w["date"])
    save_weights(ws)


def add_task(t):
    tasks = list(st.session_state["tasks"])
    t = dict(t)
    t["id"] = _uid()
    t.setdefault("done", False)
    t.setdefault("done_date", "")
    tasks.insert(0, t)
    save_tasks(tasks)


# ---------- sales / income ----------
def add_sale(s):
    sales = list(st.session_state["sales"])
    s = dict(s)
    s["id"] = _uid()
    anchor = s.get("delivered_date") or s.get("date") or ""
    try:
        a = dt.date.fromisoformat(anchor)
    except Exception:
        a = dt.date.today()
    inst = []
    for i in s.get("inst", []):
        i = dict(i)
        i["id"] = _uid()
        i.setdefault("paid", False)
        i.setdefault("reason", "")
        i.setdefault("paid_date", "")
        w = int(i.get("window", 20))
        i["due"] = (a + dt.timedelta(days=w)).isoformat()
        inst.append(i)
    s["inst"] = inst
    sales.insert(0, s)
    save_sales(sales)


def save_daily_entry(date_iso, entry):
    d = dict(st.session_state["sales_daily"])
    d[date_iso] = entry
    save_sales_daily(d)


def add_income(date_iso, kind, amount, note):
    inc = list(st.session_state["income"])
    inc.insert(0, {"id": _uid(), "date": date_iso, "type": kind,
                   "amount": float(amount), "note": note})
    save_income(inc)


# ---------- bots ----------
def add_bot_log(date_iso, bot_id, risk, pnl, notes):
    b = st.session_state["bots"]
    b["logs"].insert(0, {"id": _uid(), "date": date_iso,
                         "bot": bot_id, "risk": float(risk),
                         "pnl": float(pnl), "notes": notes})
    save_bots(b)


def add_bot(name, platform):
    b = st.session_state["bots"]
    b["bots"].append({"id": U.slug(name), "name": name,
                      "platform": platform, "status": "testing",
                      "live_date": "", "notes": ""})
    save_bots(b)


def set_bot_status(bot_id, status, date_iso):
    b = st.session_state["bots"]
    for x in b["bots"]:
        if x["id"] == bot_id:
            x["status"] = status
            x["live_date"] = date_iso if status == "live" else ""
    save_bots(b)


# ---------- net worth snapshot (cash + active ventures) ----------
def _snap(v):
    today = U.today_local().isoformat()
    snaps = [s for s in v.get("snapshots", []) if s["date"] != today]
    cash = sum(float(p.get("balance", 0))
               for p in v.get("positions", []))
    active = sum(float(f.get("balance", 0))
                 for f in v.get("funds", [])
                 if not f.get("sealed"))
    snaps.append({"date": today, "net": cash + active})
    snaps.sort(key=lambda s: s["date"])
    v["snapshots"] = snaps


# ---------- backup / restore ----------
def reset_all():
    defaults = {
        "pipeline": _seed_pipeline(),
        "routine": _seed_routine(),
        "habits": _seed_habits(),
        "habit_log": {}, "goals": [], "issues": [],
        "journal": {}, "weights": [], "clients": [],
        "sales_daily": {}, "sales": [], "income": [], "tasks": [],
        "bots": _seed_bots(), "vault": _seed_vault(),
        "spiritual": {}, "events": [],
    }
    for key, obj in defaults.items():
        _write(key + ".json", obj)
        st.session_state[key] = obj


def _csv_text(headers, rows):
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def export_csv_zip():
    import io
    import zipfile
    buf = io.BytesIO()
    clients = st.session_state.get("clients", [])
    c_rows = [[c.get("created", ""), c.get("name", ""),
               c.get("phone", ""), c.get("source", ""),
               c.get("heat", ""), c.get("want", ""),
               c.get("budget", ""), c.get("stage", ""),
               c.get("plan", ""), c.get("next_action", ""),
               c.get("next_date", ""), c.get("remark", ""),
               c.get("why_not", ""), c.get("paid_date", ""),
               c.get("returned_date", ""),
               len(c.get("history", []))] for c in clients]
    flow = st.session_state.get("vault", {}).get("flow", [])
    f_rows = [[x.get("date", ""), x.get("time", ""),
               x.get("txid", ""), x.get("kind", ""),
               x.get("amount", ""), x.get("pocket", ""),
               x.get("note", "")] for x in flow]
    sales = st.session_state.get("sales", [])
    s_rows = []
    for s in sales:
        inst = s.get("inst", [])
        n_paid = sum(1 for i in inst if i.get("paid"))
        s_rows.append([s.get("date", ""), s.get("client", ""),
                       s.get("phone", ""), s.get("commission", ""),
                       str(n_paid) + "/" + str(len(inst)),
                       s.get("delivered_date", "")])
    income = st.session_state.get("income", [])
    i_rows = [[x.get("date", ""), x.get("type", ""),
               x.get("amount", ""), x.get("note", "")] for x in income]
    tasks = st.session_state.get("tasks", [])
    t_rows = [[x.get("text", ""), x.get("area", ""),
               x.get("priority", ""), x.get("due", ""),
               x.get("done", "")] for x in tasks]
    pantry = st.session_state.get("vault", {}).get("pantry", {})
    p_rows = [[x.get("name", ""), x.get("unit", ""),
               x.get("stock", ""), x.get("daily", ""),
               x.get("category", ""), x.get("hidden", ""),
               x.get("checked", "")]
              for x in pantry.get("items", [])]
    spiritual = st.session_state.get("spiritual", {})
    sp_rows = [[d, e.get("minutes", ""), e.get("depth", ""),
                "|".join(e.get("acts", [])), e.get("word", ""),
                e.get("felt", ""), e.get("gratitude", "")]
               for d, e in sorted(spiritual.items(), reverse=True)]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("clients.csv", _csv_text(
            ["created", "name", "phone", "source", "heat", "want",
             "budget", "stage", "plan", "next_action", "next_date",
             "remark", "why_not", "paid_date", "returned_date",
             "history_count"], c_rows))
        z.writestr("flow.csv", _csv_text(
            ["date", "time", "txid", "kind", "amount", "pocket",
             "note"], f_rows))
        z.writestr("sales.csv", _csv_text(
            ["date", "client", "phone", "commission", "paid_ratio",
             "delivered_date"], s_rows))
        z.writestr("income.csv", _csv_text(
            ["date", "type", "amount", "note"], i_rows))
        z.writestr("tasks.csv", _csv_text(
            ["text", "area", "priority", "due", "done"], t_rows))
        z.writestr("pantry.csv", _csv_text(
            ["name", "unit", "stock", "daily", "category", "hidden",
             "checked"], p_rows))
        z.writestr("spiritual.csv", _csv_text(
            ["date", "minutes", "depth", "acts", "word", "felt",
             "gratitude"], sp_rows))
    return buf.getvalue()


def export_zip():
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for k in RESTORE_KEYS:
            z.writestr(k + ".json", json.dumps(
                st.session_state.get(k, []), default=str))
        z.writestr("prefs.json", json.dumps({
            "name": st.session_state.get("name"),
            "accent": st.session_state.get("accent"),
            "tz_offset": st.session_state.get("tz_offset", 0),
        }, default=str))
    return buf.getvalue()


def restore_from_zip(blob):
    import io
    import zipfile
    restored = []
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            names = set(z.namelist())
            for k in RESTORE_KEYS:
                fn = k + ".json"
                if fn in names:
                    obj = json.loads(z.read(fn))
                    _write(fn, obj)
                    st.session_state[k] = obj
                    restored.append(k)
            if "prefs.json" in names:
                pr = json.loads(z.read("prefs.json"))
                _write("prefs.json", pr)
                if pr.get("name"):
                    st.session_state["name"] = pr["name"]
                if pr.get("accent"):
                    st.session_state["accent"] = pr["accent"]
                if "tz_offset" in pr:
                    st.session_state["tz_offset"] = float(
                        pr["tz_offset"])
        if "vault" in st.session_state:
            _migrate_vault(st.session_state["vault"])
    except Exception:
        pass
    return restored
