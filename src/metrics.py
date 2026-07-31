"""Derived stats for the life OS, the TrueWave pipeline and the money OS."""
from __future__ import annotations

import calendar as _cal
import datetime as dt

from .data import START_DATE, TAG_COLORS

TERMINAL = ("paid", "returned", "lost")


def _mins(t):
    h, m = str(t).split(":")
    return int(h) * 60 + int(m)


def today_blocks(routine, weekday):
    b = [dict(x) for x in routine
         if weekday in x.get("days", list(range(7)))]
    for x in b:
        x["min"] = _mins(x["time"])
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


def today_area_split(routine, weekday):
    counts = {}
    for b in routine:
        if weekday in b.get("days", list(range(7))):
            tg = b.get("tag", "Life")
            counts[tg] = counts.get(tg, 0) + 1
    out = [(tag, c, TAG_COLORS.get(tag, "#7C8AA5"))
           for tag, c in counts.items()]
    out.sort(key=lambda x: x[1], reverse=True)
    return out


# ---------- habits ----------

def day_frac(log, habits, date_iso):
    if not habits:
        return 0.0
    done = sum(1 for h in habits
               if log.get(h["id"], {}).get(date_iso))
    return done / len(habits) * 100


def consistency_series(log, habits, n=30):
    today = dt.date.today()
    return [(today - dt.timedelta(days=o),
             day_frac(log, habits,
                      (today - dt.timedelta(days=o)).isoformat()))
            for o in range(n - 1, -1, -1)]


def day_consistency_map(log, habits, year, month, today):
    _f, nd = _cal.monthrange(year, month)
    m = {}
    for d in range(1, nd + 1):
        date = dt.date(year, month, d)
        if date <= today:
            ds = date.isoformat()
            if any(ds in log.get(h["id"], {}) for h in habits):
                m[date] = day_frac(log, habits, ds)
    return m


def habit_stats(log, hid, n=30):
    today = dt.date.today()
    s = log.get(hid, {})
    dates = [(today - dt.timedelta(days=o)).isoformat()
             for o in range(n - 1, -1, -1)]
    done = sum(1 for d in dates if s.get(d))
    streak = 0
    for d in reversed(dates):
        if s.get(d):
            streak += 1
        else:
            break
    pct = (done / len(dates) * 100) if dates else 0.0
    return done, len(dates), pct, streak


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
        vals = [1.0 if log.get(h["id"], {}).get(ds) else 0.0
                for h in habits]
        if vals:
            acc[d.weekday()].append(sum(vals) / len(vals))
    return {w: (sum(v) / len(v) * 100 if v else 0.0)
            for w, v in acc.items()}


# ---------- goals / journal ----------

def goal_pct(g):
    try:
        if not g["target"]:
            return 0.0
        return max(0.0, min(100.0,
                            float(g["current"]) / float(g["target"])
                            * 100))
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
    hit = sum(1 for o in range(n)
              if (today - dt.timedelta(days=o)).isoformat()
              in journal)
    return hit / n * 100


# ---------- sales ----------

def sales_rate(daily, today, n=30):
    start = max(START_DATE, today - dt.timedelta(days=n - 1))
    days = (today - start).days + 1
    if days <= 0:
        return 0.0
    hits = sum(1 for o in range(days)
               if daily.get((today - dt.timedelta(days=o))
                            .isoformat()))
    return hits / days * 100


def sales_streak(daily, today):
    streak = 0
    for o in range(400):
        if (today - dt.timedelta(days=o)).isoformat() in daily:
            streak += 1
        else:
            break
    return streak


def week_sales(daily, today, days=7):
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    out = []
    for o in range(days - 1, -1, -1):
        d = today - dt.timedelta(days=o)
        e = daily.get(d.isoformat()) or {}
        out.append((names[d.weekday()], int(e.get("sold", 0))))
    return out


def rejects_30d(daily, today):
    sys_n = cash_n = 0
    for o in range(30):
        e = daily.get((today - dt.timedelta(days=o)).isoformat())
        if e:
            sys_n += int(e.get("system_rej", 0))
            cash_n += int(e.get("cash_rej", 0))
    return sys_n, cash_n


# ---------- TrueWave pipeline ----------

def client_counts(clients, today):
    t = today.isoformat()
    wk = (today + dt.timedelta(days=7)).isoformat()
    act = [c for c in clients if c.get("stage") not in TERMINAL]
    return dict(
        active=len(act),
        due=[c for c in act if c.get("next_date") == t],
        over=[c for c in act
              if c.get("next_date") and c["next_date"] < t],
        up=[c for c in act if c.get("next_date")
            and t < c["next_date"] <= wk],
        new7=sum(1 for c in clients if c.get("created", "") >=
                 (today - dt.timedelta(days=6)).isoformat()),
        sold=sum(1 for c in clients if c.get("stage") == "paid"),
        cashq=sum(1 for c in clients
                  if c.get("stage") == "cash_offer"),
        returned=sum(1 for c in clients
                     if c.get("stage") == "returned"),
        lost=sum(1 for c in clients if c.get("stage") == "lost"),
    )


def stage_counts(clients):
    out = {}
    for c in clients:
        s = c.get("stage", "new")
        out[s] = out.get(s, 0) + 1
    return out


def call_sheet(clients, today):
    """Who to phone today - due + overdue, hottest first."""
    t = today.isoformat()
    act = [c for c in clients if c.get("stage") not in TERMINAL]
    due = [c for c in act if c.get("next_date") and c["next_date"] <= t]
    heat_order = {"Hot": 0, "Warm": 1, "Cold": 2}
    due.sort(key=lambda c: (heat_order.get(c.get("heat", "Warm"), 1),
                            c.get("next_date", "")))
    return due


def window_info(c, today):
    dd = c.get("delivered_date")
    if not dd:
        return None
    try:
        d = dt.date.fromisoformat(dd)
    except Exception:
        return None
    close = d + dt.timedelta(days=7)
    left = (close - today).days
    closed = left < 0 or bool(c.get("returned")) or bool(c.get("paid"))
    return dict(close=close, left=max(left, 0), closed=closed)


def clients_in_window(clients, today):
    out = []
    for c in clients:
        w = window_info(c, today)
        if w and not w["closed"]:
            out.append(c)
    return out


def moves_on(clients, d_iso):
    out = []
    for c in clients:
        for h in c.get("history", []):
            if str(h.get("ts", "")).startswith(d_iso):
                out.append((c.get("name", "?"), h))
    return out


# ---------- commissions ----------

def commission_stats(sales, today_iso):
    due_today, overdue = [], []
    paid_sum = pending_sum = 0.0
    for s in sales:
        for i in s.get("inst", []):
            amt = float(i.get("amount", 0) or 0)
            if i.get("paid"):
                paid_sum += amt
                continue
            pending_sum += amt
            if i.get("due") == today_iso:
                due_today.append((s, i))
            elif i.get("due") and i["due"] < today_iso:
                overdue.append((s, i))
    return dict(due_today=due_today, overdue=overdue,
                paid=paid_sum, pending=pending_sum)


def commissions_window(sales, today, days=7):
    lo = today.isoformat()
    hi = (today + dt.timedelta(days=days)).isoformat()
    rows = []
    for s in sales:
        for i in s.get("inst", []):
            if (i.get("due") and lo <= i["due"] <= hi
                    and not i.get("paid")):
                rows.append((s, i))
    rows.sort(key=lambda p: p[1]["due"])
    return rows


def comm_editable(sale, inst, today):
    anchor = sale.get("delivered_date") or sale.get("date") or ""
    try:
        a = dt.date.fromisoformat(anchor)
    except Exception:
        return True
    return today <= a + dt.timedelta(days=int(inst.get("window", 20)))


# ---------- income / flow ----------

def income_total(income, lo="0000", hi="9999"):
    return sum(float(x.get("amount", 0)) for x in income
               if lo <= x.get("date", "") <= hi)


def income_by_type(income):
    d = {}
    for x in income:
        k = x.get("type", "Other")
        d[k] = d.get(k, 0.0) + float(x.get("amount", 0))
    return d


# ---------- the money OS ----------

def item_saved(it):
    return sum(float(t.get("amount", 0)) for t in it.get("tx", []))


def cash_on_hand(v):
    return sum(float(p.get("balance", 0))
               for p in v.get("positions", []))


def bills_saved(v):
    return sum(float(b.get("saved", 0)) for b in v.get("bills", []))


def fun_remaining(v):
    f = v.get("fun", {})
    return max(0.0, float(f.get("budget", 0)) - float(f.get("used", 0)))


def items_saved(v):
    return sum(item_saved(it) for it in v.get("items", []))


def funds_balance(v):
    return sum(float(x.get("balance", 0)) for x in v.get("funds", []))


def allocated(v):
    return (bills_saved(v) + fun_remaining(v) + items_saved(v)
            + funds_balance(v))


def net_worth(v):
    return cash_on_hand(v) + allocated(v)


def flow_week_inout(flow, today):
    lo = (today - dt.timedelta(days=6)).isoformat()
    i = sum(float(f["amount"]) for f in flow
            if f.get("date", "") >= lo and f["kind"] == "in")
    o = sum(float(f["amount"]) for f in flow
            if f.get("date", "") >= lo and f["kind"] == "out")
    return i, o


def snapshots_series(v):
    out = []
    for s in v.get("snapshots", []):
        try:
            out.append((dt.date.fromisoformat(s["date"]),
                        float(s["net"])))
        except Exception:
            pass
    return out


def bills_due_soon(v, today, days=7):
    t = today.isoformat()
    hi = (today + dt.timedelta(days=days)).isoformat()
    return [b for b in v.get("bills", []) if not b.get("paid")
            and b.get("due") and t <= b["due"] <= hi]


def bills_overdue(v, today):
    t = today.isoformat()
    return [b for b in v.get("bills", []) if not b.get("paid")
            and b.get("due") and b["due"] < t]


# ---------- bots ----------

def bot_stats(logs, bot_id):
    ls = [l for l in logs if l.get("bot") == bot_id]
    wins = [l for l in ls if float(l["pnl"]) > 0]
    losses = [l for l in ls if float(l["pnl"]) < 0]
    pnl = sum(float(l["pnl"]) for l in ls)
    risk = sum(float(l.get("risk", 0)) for l in ls)
    avg_win = (sum(float(l["pnl"]) for l in wins) / len(wins)) \
        if wins else 0.0
    avg_loss = (abs(sum(float(l["pnl"]) for l in losses))
                / len(losses)) if losses else 0.0
    rr = (avg_win / avg_loss) if avg_loss > 0 else 0.0
    wr = (len(wins) / len(ls) * 100) if ls else 0.0
    return dict(n=len(ls), w=len(wins), l=len(losses), pnl=pnl,
                risk=risk, wr=wr, rr=rr)


def bot_week(logs, today, days=7):
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    out = []
    for o in range(days - 1, -1, -1):
        d = today - dt.timedelta(days=o)
        v = sum(float(l["pnl"]) for l in logs
                if l.get("date") == d.isoformat())
        out.append((names[d.weekday()], v))
    return out


# ---------- body / issues / tasks / score ----------

def weight_latest(weights):
    if not weights:
        return None
    return sorted(weights, key=lambda w: w["date"])[-1]


def weight_delta(weights):
    if len(weights) < 2:
        return 0.0
    ws = sorted(weights, key=lambda w: w["date"])
    return float(ws[-1]["kg"]) - float(ws[0]["kg"])


def issues_open(issues, today):
    t = today.isoformat()
    open_i = [i for i in issues if not i.get("done")]
    open_i.sort(key=lambda i: i.get("due") or "9999")
    over = [i for i in open_i if i.get("due") and i["due"] < t]
    return open_i, over


def task_counts(tasks, today):
    t = today.isoformat()
    return dict(
        open=sum(1 for x in tasks if not x.get("done")),
        done_today=sum(1 for x in tasks
                       if x.get("done_date") == t),
        overdue=sum(1 for x in tasks if not x.get("done")
                    and x.get("due") and x["due"] < t),
        total=len(tasks),
        done_all=sum(1 for x in tasks if x.get("done")),
    )


def life_score(cons, jcomp, srate, goal_avg):
    v = cons * 0.4 + jcomp * 0.2 + srate * 0.2 + goal_avg * 0.2
    return int(max(0, min(100, round(v))))


def day_pulse(d_iso, ctx):
    """Everything the system recorded on one date - the journal's
    memory is picked up automatically, nothing is re-typed."""
    clients = ctx["clients"]
    non_t = [c for c in clients if c.get("stage") not in TERMINAL]
    outcomes = [c for c in clients
                if c.get("paid_date") == d_iso
                or c.get("returned_date") == d_iso]
    v = ctx["vault"]
    flow = [f for f in v.get("flow", []) if f.get("date") == d_iso]
    return {
        "new_clients": [c for c in clients
                        if c.get("created") == d_iso],
        "followups": [c for c in non_t
                      if c.get("next_date") == d_iso],
        "moves": moves_on(clients, d_iso),
        "outcomes": outcomes,
        "daily": ctx["sales_daily"].get(d_iso),
        "sales": [s for s in ctx["sales"]
                  if s.get("date") == d_iso],
        "inst_due": [(s, i) for s in ctx["sales"]
                     for i in s.get("inst", [])
                     if i.get("due") == d_iso],
        "income": [x for x in ctx["income"]
                   if x.get("date") == d_iso],
        "flow": flow,
        "net_worth": net_worth(v),
        "cash": cash_on_hand(v),
        "bot_logs": [l for l in ctx["bots"].get("logs", [])
                     if l.get("date") == d_iso],
        "weight": next((w for w in ctx["weights"]
                        if w.get("date") == d_iso), None),
        "tasks_done": [t for t in ctx["tasks"]
                       if t.get("done_date") == d_iso],
    }
