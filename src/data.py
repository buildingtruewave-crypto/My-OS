"""Seeded, editable, persisted life data.

Generated relative to date.today() at seed time so streaks / calendar always
look current.  Writes go to data/*.json (VPS) and are silently skipped where
the filesystem is read-only (Streamlit Cloud).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from . import util as U

DATA = Path(__file__).resolve().parent.parent / "data"
DEFAULT_SEED = 73126
DEFAULT_NAME = "Mwangi.Alex"
START_BALANCE = 16000.0

TAG_COLORS = {"Trade": "#4C8DFF", "Body": "#34D399", "Mind": "#D946EF",
              "Life": "#F5B544", "Rest": "#7C8AA5", "Focus": "#8B7CFF"}
ACCENTS = {"Electric Blue": "#4C8DFF", "Terminal Teal": "#2DD4BF",
           "Signal Violet": "#8B7CFF", "Amber Edge": "#F5B544"}
MOODS = ["drained", "flat", "steady", "sharp", "on fire"]
DAY_ABBR = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

ROUTINE_SEED = [
    ("05:00", "Wake - hydrate - light", "Body", "all"),
    ("05:15", "Prayer / meditation", "Mind", "all"),
    ("05:45", "Workout - mobility", "Body", "weekdays"),
    ("06:45", "Shower - breakfast", "Life", "all"),
    ("07:15", "Journal - plan the day", "Mind", "all"),
    ("07:45", "Pre-market analysis - levels", "Trade", "weekdays"),
    ("08:00", "London open - execution", "Trade", "weekdays"),
    ("10:30", "Step away - walk", "Body", "weekdays"),
    ("11:00", "Review morning trades", "Trade", "weekdays"),
    ("12:00", "Lunch - no screens", "Rest", "all"),
    ("13:00", "Study - backtest", "Focus", "weekdays"),
    ("14:00", "New York prep - bias", "Trade", "weekdays"),
    ("14:30", "New York session", "Trade", "weekdays"),
    ("17:00", "Close books - EOD review", "Trade", "weekdays"),
    ("17:45", "Walk - errands", "Life", "all"),
    ("18:30", "Dinner - family", "Life", "all"),
    ("19:30", "Read - build a skill", "Focus", "all"),
    ("20:30", "Wind down - no screens", "Rest", "all"),
    ("21:30", "Sleep", "Rest", "all"),
]

HABITS_SEED = [
    ("Z", "Sleep 7h+", 0.74), ("W", "Workout", 0.80), ("M", "Pray / meditate", 0.88),
    ("J", "Journal", 0.82), ("P", "Pre-market plan", 0.78), ("N", "No phone 1st hr", 0.62),
    ("R", "Read 20 min", 0.70), ("H", "Hydrate 2L", 0.66), ("C", "Clean desk", 0.58),
    ("E", "EOD review", 0.84), ("F", "No junk food", 0.60), ("K", "Walk outside", 0.72),
]

GOALS_SEED = [
    ("Account +12% this quarter", "return %", 12.0, 7.4, "Q3"),
    ("Win rate >= 60%", "win %", 60.0, 58.0, "Q3"),
    ("Log 25 trading days", "days", 25.0, 17.0, "Q3"),
    ("Read 6 books", "books", 6.0, 3.0, "Q3"),
    ("90% routine adherence", "consistency %", 90.0, 76.0, "Q3"),
    ("Journal 30 days straight", "day streak", 30.0, 12.0, "Q3"),
]

TASKS_SEED = [
    ("Backtest the London fade on EURUSD", "Trade", "High", -1, False),
    ("Renew gym membership", "Life", "Normal", 2, False),
    ("Finish chapter 4 of Trading in the Zone", "Focus", "Normal", 0, False),
    ("Call dad", "Life", "High", 0, False),
    ("Review last week journal for repeats", "Mind", "Normal", -2, True),
    ("Prep NY bias notes", "Trade", "Normal", 0, True),
]

TRADE_ASSETS = {
    "XAUUSD": (2350.0, 2, 0.10, 100.0, 0.05, 0.50, 0.42, 0.70),
    "BTCUSD": (67000.0, 1, 1.00, 1.0, 0.30, 3.00, 0.18, 0.62),
    "EURUSD": (1.0850, 5, 0.0001, 100000.0, 0.50, 3.00, 0.16, 0.66),
}
TRADE_STRATS = ["Pullback + Trend", "Breakout", "Range Fade", "Scalp"]


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
        m = re.match(r"^(\d{1,2}):(\d{2})\s*(AM|PM)?\s*[-|]?\s*(.+)$", line, re.I)
        if not m:
            continue
        hh = int(m.group(1))
        mm = int(m.group(2))
        ap = m.group(3)
        rest = m.group(4).strip()
        if ap and ap.upper() == "PM" and hh != 12:
            hh += 12
        if ap and ap.upper() == "AM" and hh == 12:
            hh = 0
        tag, scope = "Life", "all"
        sm = re.search(r"@(\S+)", rest)
        if sm:
            scope = sm.group(1)
            rest = rest.replace(sm.group(0), "").strip()
        tm = re.search(r"#(\w+)", rest)
        if tm:
            tag = tm.group(1).capitalize()
            rest = rest.replace(tm.group(0), "").strip()
        if tag not in TAG_COLORS:
            tag = "Life"
        tstr = str(hh).zfill(2) + ":" + str(mm).zfill(2)
        blocks.append({"time": tstr, "label": rest.strip(),
                       "tag": tag, "days": _scope_days(scope)})
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
            scope = ",".join(k for k, v in DAY_ABBR.items() if v in b["days"])
        t = b["time"]
        lab = b["label"]
        tg = b["tag"]
        lines.append(t + "  " + lab + "  #" + tg + "  @" + scope)
    return "\n".join(lines)


def parse_habits_text(text):
    out = []
    for raw in str(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        icon = parts[0] if parts else "*"
        name = parts[1] if len(parts) > 1 else parts[0]
        out.append({"id": U.slug(name), "icon": icon, "name": name})
    seen = set()
    dedup = []
    for h in out:
        if h["id"] not in seen:
            seen.add(h["id"])
            dedup.append(h)
    return dedup


def habits_to_text(habits):
    lines = []
    for h in habits:
        lines.append(h["icon"] + "  " + h["name"])
    return "\n".join(lines)


def _seed_routine():
    return [{"time": t, "label": l, "tag": tg, "days": _scope_days(sc)}
            for (t, l, tg, sc) in ROUTINE_SEED]


def _seed_habits():
    return [{"id": U.slug(n), "icon": i, "name": n} for (i, n, _) in HABITS_SEED]


def _seed_habit_log(habits, rng, days=120):
    rates = {U.slug(n): r for (_, n, r) in HABITS_SEED}
    log = {}
    today = dt.date.today()
    for h in habits:
        rate = rates.get(h["id"], 0.7)
        prev = False
        series = {}
        for off in range(days - 1, -1, -1):
            d = today - dt.timedelta(days=off)
            p = rate + (0.18 if prev else -0.06)
            done = bool(rng.random() < max(0.08, min(0.97, p)))
            if d.weekday() >= 5 and h["name"] in ("Pre-market plan", "EOD review"):
                done = bool(rng.random() < 0.25)
            series[d.isoformat()] = done
            prev = done
        log[h["id"]] = series
    return log


def _seed_goals():
    return [{"id": str(uuid.uuid4())[:8], "title": t, "metric": m,
             "target": tg, "current": cu, "quarter": q}
            for (t, m, tg, cu, q) in GOALS_SEED]


def _seed_tasks(rng):
    today = dt.date.today()
    out = []
    for (text, area, pri, off, done) in TASKS_SEED:
        due = (today + dt.timedelta(days=off)).isoformat()
        out.append({"id": str(uuid.uuid4())[:8], "text": text, "area": area,
                    "priority": pri, "due": due, "done": bool(done)})
    return out


def _seed_journal(rng, days=30):
    today = dt.date.today()
    grat = ["health", "my discipline", "a clean chart", "family", "small wins", "the process"]
    win = ["followed my rules", "took the A+ setup", "walked away from a bad one",
           "hit the gym", "no phone morning", "journalled honestly"]
    lesson = ["size down after 2 losses", "do not chase the London open",
              "sleep beats one more hour of charts", "the plan over the mood"]
    out = {}
    for off in range(days - 1, -1, -1):
        if rng.random() < 0.82:
            d = today - dt.timedelta(days=off)
            les = str(rng.choice(lesson)) if rng.random() < 0.7 else ""
            out[d.isoformat()] = {
                "gratitude": str(rng.choice(grat)),
                "win": str(rng.choice(win)),
                "lesson": les,
                "mood": str(rng.choice(MOODS)),
            }
    return out


def _seed_trades(rng, days=300):
    today = dt.date.today()
    names = list(TRADE_ASSETS.keys())
    rows = []
    day = today - dt.timedelta(days=days)
    while day <= today:
        if day.weekday() < 5 and rng.random() < 0.8:
            for _ in range(int(rng.choice([1, 1, 2, 2, 3]))):
                a = str(rng.choice(names))
                bp, dec, pip, mult, llo, lhi, _w, wp = TRADE_ASSETS[a]
                entry = round(bp + rng.normal(0, pip * 8), dec)
                direction = "BUY" if rng.random() < 0.5 else "SELL"
                lots = round(float(rng.uniform(llo, lhi)), 2)
                win = rng.random() < wp
                if win:
                    target = float(rng.lognormal(np.log(90), 0.6))
                else:
                    target = -float(rng.lognormal(np.log(45), 0.5))
                dsign = 1.0 if direction == "BUY" else -1.0
                imp = abs(target) / max(lots * mult, 1e-9)
                sign = 1 if target > 0 else -1
                exitp = round(entry + sign * dsign * imp, dec)
                pnl = round((exitp - entry) * dsign * lots * mult, 2)
                hh = int(rng.integers(7, 21))
                mm = int(rng.integers(0, 60))
                tstr = str(hh).zfill(2) + ":" + str(mm).zfill(2)
                rows.append({"date": day.isoformat(), "time": tstr,
                             "asset": a, "direction": direction, "entry": entry,
                             "exit": exitp, "lots": lots, "pnl": pnl,
                             "strategy": str(rng.choice(TRADE_STRATS)),
                             "duration_min": int(rng.integers(5, 240))})
        day += dt.timedelta(days=1)
    return rows


def _write_trades(rows):
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(DATA / "trades.csv", index=False)
    except Exception:
        pass


def _read_trades():
    try:
        f = DATA / "trades.csv"
        if f.exists() and f.stat().st_size > 0:
            df = pd.read_csv(f)
            if not df.empty and "pnl" in df.columns:
                return df
    except Exception:
        pass
    return None


def _finalize_trades(df):
    cols = ["date", "time", "asset", "direction", "entry",
            "exit", "lots", "pnl", "strategy", "duration_min"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    df = df.copy()
    for c in ("entry", "exit", "lots", "pnl"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df["dt"] = pd.to_datetime(df["date"] + " " + df["time"].astype(str).str.slice(0, 5))
    df["dt_date"] = df["dt"].dt.date
    return df.sort_values("dt").reset_index(drop=True)


def ensure():
    rng = np.random.default_rng(int(st.session_state.get("seed", DEFAULT_SEED)))
    prefs = _read("prefs.json") or {}
    if "routine" not in st.session_state:
        st.session_state["routine"] = _read("routine.json") or _seed_routine()
    if "habits" not in st.session_state:
        st.session_state["habits"] = _read("habits.json") or _seed_habits()
    if "habit_log" not in st.session_state:
        st.session_state["habit_log"] = _read("habit_log.json") or _seed_habit_log(st.session_state["habits"], rng)
    if "goals" not in st.session_state:
        st.session_state["goals"] = _read("goals.json") or _seed_goals()
    if "tasks" not in st.session_state:
        st.session_state["tasks"] = _read("tasks.json") or _seed_tasks(rng)
    if "journal" not in st.session_state:
        st.session_state["journal"] = _read("journal.json") or _seed_journal(rng)
    if "trades" not in st.session_state:
        rows = _read_trades()
        if rows is not None:
            st.session_state["trades"] = _finalize_trades(rows)
        else:
            seeded = _seed_trades(rng)
            st.session_state["trades"] = _finalize_trades(pd.DataFrame(seeded))
            _write_trades(seeded)
    st.session_state.setdefault("name", prefs.get("name", DEFAULT_NAME))
    st.session_state.setdefault("accent", prefs.get("accent", "#4C8DFF"))
    st.session_state.setdefault("tz_offset", float(prefs.get("tz_offset", 0)))
    st.session_state.setdefault("seed", DEFAULT_SEED)


def _save_prefs():
    _write("prefs.json", {"name": st.session_state.get("name"),
                          "accent": st.session_state.get("accent"),
                          "tz_offset": st.session_state.get("tz_offset", 0)})


def get(k):
    return st.session_state[k]


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


def save_tasks(x):
    st.session_state["tasks"] = x
    _write("tasks.json", x)


def save_journal(x):
    st.session_state["journal"] = x
    _write("journal.json", x)


def save_trades(df):
    st.session_state["trades"] = df
    clean = df.drop(columns=["dt", "dt_date"], errors="ignore")
    _write_trades(clean.to_dict("records"))


def add_task(t):
    tasks = list(st.session_state["tasks"])
    t = dict(t)
    t["id"] = str(uuid.uuid4())[:8]
    t.setdefault("done", False)
    tasks.insert(0, t)
    save_tasks(tasks)


def add_goal(g):
    goals = list(st.session_state["goals"])
    g = dict(g)
    g["id"] = str(uuid.uuid4())[:8]
    goals.append(g)
    save_goals(goals)


def regenerate(seed):
    st.session_state["seed"] = int(seed)
    rng = np.random.default_rng(int(seed))
    habits = _seed_habits()
    st.session_state["routine"] = _seed_routine()
    st.session_state["habits"] = habits
    st.session_state["habit_log"] = _seed_habit_log(habits, rng)
    st.session_state["goals"] = _seed_goals()
    st.session_state["tasks"] = _seed_tasks(rng)
    st.session_state["journal"] = _seed_journal(rng)
    seeded = _seed_trades(rng)
    st.session_state["trades"] = _finalize_trades(pd.DataFrame(seeded))
    _write("routine.json", st.session_state["routine"])
    _write("habits.json", st.session_state["habits"])
    _write("habit_log.json", st.session_state["habit_log"])
    _write("goals.json", st.session_state["goals"])
    _write("tasks.json", st.session_state["tasks"])
    _write("journal.json", st.session_state["journal"])
    _write_trades(seeded)


def export_zip():
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("routine.json", json.dumps(st.session_state["routine"], default=str))
        z.writestr("habits.json", json.dumps(st.session_state["habits"], default=str))
        z.writestr("habit_log.json", json.dumps(st.session_state["habit_log"], default=str))
        z.writestr("goals.json", json.dumps(st.session_state["goals"], default=str))
        z.writestr("tasks.json", json.dumps(st.session_state["tasks"], default=str))
        z.writestr("journal.json", json.dumps(st.session_state["journal"], default=str))
        tr = st.session_state["trades"].drop(columns=["dt", "dt_date"], errors="ignore")
        z.writestr("trades.csv", tr.to_csv(index=False))
    return buf.getvalue()
