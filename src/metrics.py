"""Derived stats for the life OS + a compact trade summary."""
from __future__ import annotations

import calendar as _cal
import datetime as dt

import pandas as pd

WEEK_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HOUR_BUCKETS = ["00-04", "04-08", "08-12", "12-16", "16-20", "20-24"]


def _mins(t):
    h, m = str(t).split(":")
    return int(h) * 60 + int(m)


def today_blocks(routine, weekday):
    b = []
    for x in routine:
        days = x.get("days", list(range(7)))
        if weekday in days:
            item = dict(x)
            item["min"] = _mins(x["time"])
            b.append(item)
    b.sort(key=lambda x: x["min"])
    return b


def active_block_info(blocks, now_dt):
    now_min = now_dt.hour * 60 + now_dt.minute
    if not blocks:
        return -1, 0.0, None, None
    idx = -1
    for i, b in enumerate(blocks):
        if b["min"] <= now_min:
            idx = i
    if idx < 0:
        return -1, 0.0, None, blocks[0]
    cur = blocks[idx]
    nxt = blocks[idx + 1] if idx + 1 < len(blocks) else None
    end = nxt["min"] if nxt else min(cur["min"] + 75, 1440)
    span = max(end - cur["min"], 1)
    prog = max(0.0, min(1.0, (now_min - cur["min"]) / span))
    return idx, prog, cur, nxt


def day_frac(log, habits, date_iso):
    if not habits:
        return 0.0
    done = 0
    for h in habits:
        if log.get(h["id"], {}).get(date_iso):
            done += 1
    return done / len(habits) * 100


def consistency_series(log, habits, n=30):
    today = dt.date.today()
    out = []
    for o in range(n - 1, -1, -1):
        d = today - dt.timedelta(days=o)
        out.append((d, day_frac(log, habits, d.isoformat())))
    return out


def day_consistency_map(log, habits, year, month, today):
    _first, nd = _cal.monthrange(year, month)
    m = {}
    for d in range(1, nd + 1):
        date = dt.date(year, month, d)
        if date <= today:
            m[date] = day_frac(log, habits, date.isoformat())
    return m


def week_consistency(log, habits):
    today = dt.date.today()
    out = []
    for o in range(6, -1, -1):
        d = today - dt.timedelta(days=o)
        out.append((
            WEEK_NAMES[d.weekday()],
            day_frac(log, habits, d.isoformat()),
        ))
    return out


def today_area_split(routine, weekday):
    from .data import TAG_COLORS
    counts = {}
    for b in routine:
        if weekday in b.get("days", list(range(7))):
            tg = b.get("tag", "Life")
            counts[tg] = counts.get(tg, 0) + 1
    out = []
    for tag, c in counts.items():
        out.append((tag, c, TAG_COLORS.get(tag, "#7C8AA5")))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def trade_heatmap(trades):
    mat = [[0.0] * 6 for _ in range(7)]
    if trades is None or trades.empty:
        return mat
    for _, t in trades.iterrows():
        wd = int(t["dt"].weekday())
        hb = min(int(t["dt"].hour) // 4, 5)
        mat[wd][hb] += float(t["pnl"])
    return mat


def habit_stats(log, hid, n=30):
    today = dt.date.today()
    s = log.get(hid, {})
    dates = [
        (today - dt.timedelta(days=o)).isoformat()
        for o in range(n - 1, -1, -1)
    ]
    done = sum(1 for d in dates if s.get(d))
    total = len(dates)
    streak = 0
    for d in reversed(dates):
        if s.get(d):
            streak += 1
        else:
            break
    pct = (done / total * 100) if total else 0.0
    return done, total, pct, streak


def habit_streak(log, hid):
    return habit_stats(log, hid, 400)[3]


def best_habit_streak(log, habits):
    if not habits:
        return 0
    return max(habit_streak(log, h["id"]) for h in habits)


def overall_consistency(habits, log, n=30):
    if not habits:
        return 0.0
    pcts = [habit_stats(log, h["id"], n)[2] for h in habits]
    return sum(pcts) / len(pcts)


def consistency_by_weekday(habits, log, days=60):
    today = dt.date.today()
    acc = {w: [] for w in range(7)}
    for o in range(days):
        d = today - dt.timedelta(days=o)
        ds = d.isoformat()
        vals = [
            1.0 if log.get(h["id"], {}).get(ds) else 0.0
            for h in habits
        ]
        if vals:
            acc[d.weekday()].append(sum(vals) / len(vals))
    out = {}
    for w, v in acc.items():
        out[w] = (sum(v) / len(v) * 100) if v else 0.0
    return out


def goal_pct(g):
    try:
        if not g["target"]:
            return 0.0
        return max(0.0, min(100.0,
                   float(g["current"]) / float(g["target"]) * 100))
    except Exception:
        return 0.0


def goal_buckets(goals):
    on = at = done = 0
    for g in goals:
        p = goal_pct(g)
        if p >= 100:
            done += 1
        elif p >= 60:
            on += 1
        else:
            at += 1
    return on, at, done


def task_counts(tasks):
    done = sum(1 for t in tasks if t.get("done"))
    return done, len(tasks)


def overdue_tasks(tasks):
    today = dt.date.today()
    n = 0
    for t in tasks:
        if t.get("done"):
            continue
        try:
            if dt.date.fromisoformat(t["due"]) < today:
                n += 1
        except Exception:
            pass
    return n


def journal_streak(journal):
    today = dt.date.today()
    streak = 0
    for o in range(400):
        if (today - dt.timedelta(days=o)).isoformat() in journal:
            streak += 1
        else:
            break
    return streak


def journal_completion(journal, n=30):
    today = dt.date.today()
    hit = sum(
        1 for o in range(n)
        if (today - dt.timedelta(days=o)).isoformat() in journal
    )
    return hit / n * 100


def life_score(cons, jcomp, twr, goal_avg):
    v = cons * 0.4 + jcomp * 0.2 + twr * 0.2 + goal_avg * 0.2
    return int(max(0, min(100, round(v))))


def trade_summary(trades, start):
    zero = dict(n=0, w=0, l=0, wr=0.0, net=0.0, win_streak=0,
                loss_streak=0, day_pnl={}, recent=pd.DataFrame(),
                eq_pts=[], today_pnl=0.0, today_n=0)
    if trades is None or trades.empty:
        return zero
    pnl = trades["pnl"]
    n = len(trades)
    w = int((pnl > 0).sum())
    l = int((pnl < 0).sum())
    wr = (w / n * 100) if n else 0.0
    net = float(pnl.sum())
    seq = [1 if x > 0 else (-1 if x < 0 else 0) for x in pnl]
    ws = 0
    for x in reversed(seq):
        if x == 1:
            ws += 1
        else:
            break
    ls = 0
    for x in reversed(seq):
        if x == -1:
            ls += 1
        else:
            break
    day_pnl = {
        d: float(v)
        for d, v in trades.groupby("dt_date")["pnl"].sum().items()
    }
    g = trades.sort_values("dt").groupby("dt_date")["pnl"].sum().sort_index()
    eq_pts = []
    run = float(start)
    for d, v in g.items():
        run += float(v)
        eq_pts.append((d, run))
    today = trades["dt_date"].max()
    tmask = trades["dt_date"] == today
    today_pnl = float(trades.loc[tmask, "pnl"].sum())
    today_n = int(tmask.sum())
    recent = trades.sort_values("dt").tail(6).iloc[::-1]
    return dict(n=n, w=w, l=l, wr=wr, net=net, win_streak=ws,
                loss_streak=ls, day_pnl=day_pnl, recent=recent,
                eq_pts=eq_pts, today_pnl=today_pnl, today_n=today_n)
