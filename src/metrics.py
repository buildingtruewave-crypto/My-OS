"""Derived stats for the life OS + a compact trade summary."""
from __future__ import annotations

import datetime as dt
import math
from typing import List

import numpy as np
import pandas as pd


def _mins(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def today_blocks(routine, weekday):
    b = [dict(x, min=_mins(x["time"])) for x in routine if weekday in x.get("days", list(range(7)))]
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
    prog = max(0.0, min(1.0, (now_min - cur["min"]) / max(end - cur["min"], 1)))
    return idx, prog, cur, nxt


# ---------------------------------------------------------------- habits
def _series(log, hid, n):
    today = dt.date.today()
    s = log.get(hid, {})
    return [(today - dt.timedelta(days=o)).isoformat() for o in range(n - 1, -1, -1)], s


def habit_stats(log, hid, n=30):
    dates, s = _series(log, hid, n)
    done = sum(1 for d in dates if s.get(d))
    total = len(dates)
    streak = 0
    for d in reversed(dates):
        if s.get(d):
            streak += 1
        else:
            break
    return done, total, (done / total * 100 if total else 0.0), streak


def habit_streak(log, hid):
    return habit_stats(log, hid, 400)[3]


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
        vals = [1.0 if log.get(h["id"], {}).get(ds) else 0.0 for h in habits]
        if vals:
            acc[d.weekday()].append(sum(vals) / len(vals))
    return {w: (sum(v) / len(v) * 100 if v else 0.0) for w, v in acc.items()}


def habit_completion_series(log, hid, dates):
    s = log.get(hid, {})
    return [bool(s.get(d.isoformat())) for d in dates]


# ---------------------------------------------------------------- goals / tasks / journal
def goal_pct(g):
    try:
        return max(0.0, min(100.0, float(g["current"]) / float(g["target"]) * 100)) if g["target"] else 0.0
    except Exception:
        return 0.0


def task_counts(tasks):
    done = sum(1 for t in tasks if t.get("done"))
    return done, len(tasks)


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
    hit = sum(1 for o in range(n) if (today - dt.timedelta(days=o)).isoformat() in journal)
    return hit / n * 100


def life_score(cons, jcomp, twr, goal_avg):
    v = cons * 0.4 + jcomp * 0.2 + twr * 0.2 + goal_avg * 0.2
    return int(max(0, min(100, round(v))))


# ---------------------------------------------------------------- trades
def trade_summary(trades, start):
    zero = dict(n=0, w=0, l=0, wr=0.0, net=0.0, win_streak=0, loss_streak=0,
                day_pnl={}, recent=pd.DataFrame(), eq_pts=[], today_pnl=0.0)
    if trades is None or trades.empty:
        return zero
    pnl = trades["pnl"]
    n = len(trades); w = int((pnl > 0).sum()); l = int((pnl < 0).sum())
    wr = w / n * 100 if n else 0.0
    net = float(pnl.sum())
    seq = [1 if x > 0 else (-1 if x < 0 else 0) for x in pnl]
    ws = ls = 0
    for x in reversed(seq):
        if x == 1:
            ws += 1
        else:
            break
    for x in reversed(seq):
        if x == -1:
            ls += 1
        else:
            break
    day_pnl = {d: float(v) for d, v in trades.groupby("dt_date")["pnl"].sum().items()}
    g = trades.sort_values("dt").groupby("dt_date")["pnl"].sum().sort_index()
    eq_pts, run = [], float(start)
    for d, v in g.items():
        run += float(v); eq_pts.append((d, run))
    today = trades["dt_date"].max()
    today_pnl = float(trades.loc[trades["dt_date"] == today, "pnl"].sum())
    return dict(n=n, w=w, l=l, wr=wr, net=net, win_streak=ws, loss_streak=ls,
                day_pnl=day_pnl, recent=trades.sort_values("dt").tail(6).iloc[::-1],
                eq_pts=eq_pts, today_pnl=today_pnl)
