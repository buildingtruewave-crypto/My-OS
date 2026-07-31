"""Empty-on-purpose, editable, persisted life data.
Recording starts Friday 1 August 2026 (Nairobi). Nothing is faked:
the routine, habit names, bot names and vault targets come from the
operator's real plan - every figure is entered by hand from day one.
Everything persists to data/*.json so a reboot loses nothing.
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
DEFAULT_PIN = "2580"

TAG_COLORS = {
    "Content": "#4C8DFF",
    "Sales": "#2DD4BF",
    "Body": "#34D399",
    "Mind": "#D946EF",
    "Life": "#F5B544",
    "Rest": "#7C8AA5",
    "Focus": "#8B7CFF",
}
ACCENTS = {
    "Electric Blue": "#4C8DFF",
    "Terminal Teal": "#2DD4BF",
    "Signal Violet": "#8B7CFF",
    "Amber Edge": "#F5B544",
}
MOODS = ["drained", "flat", "steady", "sharp", "on fire"]
SOURCES = ["TikTok", "TikTok Live", "Instagram", "Facebook",
           "WhatsApp", "Walk-in", "Referral"]
HEATS = ["Hot", "Warm", "Cold"]
DAY_ABBR = {"mon": 0, "tue": 1, "wed": 2, "thu": 3,
            "fri": 4, "sat": 5, "sun": 6}

# (time, label, tag, scope)  scope: all | weekdays | sat | sun
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
    ("18:30", "Home - blunt + unwind", "Rest", "weekdays"),
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
    ("W", "Workout 45 min"),
    ("J", "Journal the day"),
    ("S", "Log sales + rejections"),
    ("C", "Log client follow-ups"),
    ("G", "Weigh-in"),
    ("R", "Morning routine done"),
    ("L", "Lights out by 10"),
]

BOT_SEED = [
    ("deriv", "Deriv Bot", "Deriv - 24/7 Streamlit", "testing"),
    ("alpaca", "Alpaca Bot", "Alpaca stocks - 24/7 Streamlit",
     "testing"),
]

BUCKET_SEED = [
    ("household", "Household", 0.0),
    ("enjoy", "Enjoyment", 0.0),
    ("emergency", "Emergency Fund", 0.0),
]


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
        hh, mm, ap, rest = int(m.group(1)), int(m.group(2)), \
            m.group(3), m.group(4).strip()
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
        blocks.append({
            "time": str(hh).zfill(2) + ":" + str(mm).zfill(2),
            "label": rest.strip(), "tag": tag,
            "days": _scope_days(scope),
        })
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
            scope = ",".join(k for k, v in DAY_ABBR.items()
                             if v in b["days"])
        lines.append(b["time"] + "  " + b["label"] + "  #" + b["tag"]
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


def _seed_routine():
    return [{"time": t, "label": l, "tag": tg,
             "days": _scope_days(sc)}
            for (t, l, tg, sc) in ROUTINE_SEED]


def _seed_habits():
    return [{"id": U.slug(n), "icon": i, "name": n}
            for (i, n) in HABITS_SEED]


def _seed_bots():
    return {
        "bots": [{"id": bid, "name": nm, "platform": pf,
                  "status": stt, "live_date": "", "notes": ""}
                 for (bid, nm, pf, stt) in BOT_SEED],
        "logs": [],
    }


def _seed_vault():
    return {
        "fund": {
            "name": "HHO Carbon Cleaning - Nairobi",
            "target_lo": 150000.0,
            "target_hi": 200000.0,
            "deadline": "2027-01-31",
            "start_capital": 0.0,
            "tx": [],
        },
        "buckets": [{"id": bid, "name": nm, "target": tg, "tx": []}
                    for (bid, nm, tg) in BUCKET_SEED],
        "items": [],
    }


def _ensure_key(key, fname, factory):
    if key not in st.session_state:
        st.session_state[key] = _read(fname) or factory()


def ensure():
    prefs = _read("prefs.json") or {}
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
    _ensure_key("bots", "bots.json", _seed_bots)
    _ensure_key("vault", "vault.json", _seed_vault)
    st.session_state.setdefault(
        "name", prefs.get("name", DEFAULT_NAME))
    st.session_state.setdefault(
        "accent", prefs.get("accent", "#4C8DFF"))
    st.session_state.setdefault(
        "tz_offset", float(prefs.get("tz_offset", 0)))
    st.session_state.setdefault("pin", str(prefs.get("pin",
                                                     DEFAULT_PIN)))


def get(k):
    return st.session_state[k]


def _save_prefs():
    _write("prefs.json", {
        "name": st.session_state.get("name"),
        "accent": st.session_state.get("accent"),
        "tz_offset": st.session_state.get("tz_offset", 0),
        "pin": st.session_state.get("pin", DEFAULT_PIN),
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


def save_bots(x):
    st.session_state["bots"] = x
    _write("bots.json", x)


def save_vault(x):
    st.session_state["vault"] = x
    _write("vault.json", x)


# ---------- add helpers ----------

def add_client(c):
    clients = list(st.session_state["clients"])
    c = dict(c)
    c["id"] = _uid()
    c.setdefault("status", "open")
    c.setdefault("outcome_date", "")
    clients.insert(0, c)
    save_clients(clients)


def add_issue(text, area, due):
    issues = list(st.session_state["issues"])
    issues.insert(0, {"id": _uid(), "text": text, "area": area,
                      "due": due, "done": False})
    save_issues(issues)


def add_goal(g):
    goals = list(st.session_state["goals"])
    g = dict(g)
    g["id"] = _uid()
    goals.append(g)
    save_goals(goals)


def add_weight(date_iso, kg):
    ws = [w for w in st.session_state["weights"]
          if w["date"] != date_iso]
    ws.append({"date": date_iso, "kg": float(kg)})
    ws.sort(key=lambda w: w["date"])
    save_weights(ws)


def add_sale(s):
    sales = list(st.session_state["sales"])
    s = dict(s)
    s["id"] = _uid()
    inst = []
    for i in s.get("inst", []):
        i = dict(i)
        i["id"] = _uid()
        i.setdefault("paid", False)
        i.setdefault("reason", "")
        inst.append(i)
    s["inst"] = inst
    sales.insert(0, s)
    save_sales(sales)


def save_daily_entry(date_iso, entry):
    d = dict(st.session_state["sales_daily"])
    d[date_iso] = entry
    save_sales_daily(d)


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


def fund_tx(date_iso, kind, amount, source):
    v = st.session_state["vault"]
    v["fund"]["tx"].insert(0, {"id": _uid(), "date": date_iso,
                               "kind": kind, "amount": float(amount),
                               "source": source})
    save_vault(v)


def set_fund_capital(x):
    v = st.session_state["vault"]
    v["fund"]["start_capital"] = float(x)
    save_vault(v)


def bucket_tx(bid, date_iso, kind, amount, note):
    v = st.session_state["vault"]
    for b in v["buckets"]:
        if b["id"] == bid:
            b["tx"].insert(0, {"id": _uid(), "date": date_iso,
                               "kind": kind, "amount": float(amount),
                               "note": note})
    save_vault(v)


def set_bucket_target(bid, target):
    v = st.session_state["vault"]
    for b in v["buckets"]:
        if b["id"] == bid:
            b["target"] = float(target)
    save_vault(v)


def add_item(name, price):
    v = st.session_state["vault"]
    v["items"].insert(0, {"id": _uid(), "name": name,
                          "price": float(price), "tx": [],
                          "bought": False, "bought_date": ""})
    save_vault(v)


def item_tx(iid, date_iso, amount):
    v = st.session_state["vault"]
    for it in v["items"]:
        if it["id"] == iid:
            it["tx"].append({"date": date_iso,
                             "amount": float(amount)})
    save_vault(v)


def buy_item(iid, date_iso):
    v = st.session_state["vault"]
    for it in v["items"]:
        if it["id"] == iid:
            it["bought"] = True
            it["bought_date"] = date_iso
    save_vault(v)


def reset_all():
    defaults = {
        "routine": _seed_routine(),
        "habits": _seed_habits(),
        "habit_log": {}, "goals": [], "issues": [],
        "journal": {}, "weights": [], "clients": [],
        "sales_daily": {}, "sales": [],
        "bots": _seed_bots(), "vault": _seed_vault(),
    }
    for key, obj in defaults.items():
        _write(key + ".json", obj)
        st.session_state[key] = obj


def export_zip():
    import io
    import zipfile
    buf = io.BytesIO()
    keys = ["routine", "habits", "habit_log", "goals", "issues",
            "journal", "weights", "clients", "sales_daily", "sales",
            "bots", "vault"]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for k in keys:
            z.writestr(k + ".json", json.dumps(
                st.session_state[k], default=str))
    return buf.getvalue()
