"""Derived stats for the life OS, the TrueWave pipeline, the money OS, the
pantry / runway / emergency model and the spiritual energy model. Pure
read-side: never mutates, never auto-deducts. Also provides the
effective-habit merge (auto-tick habits from real data) and the follow-back
clock so the shell and TrueWave never miss a scheduled call-back.
"""
from __future__ import annotations

import calendar as _cal
import datetime as dt

from .data import (role_id, stage_color, stage_label, stage_role,
                   terminal_ids)

CASH_CREDIT = "CASH OFFER - CREDIT"


def _mins(t):
    h, m = str(t).split(":")
    return int(h) * 60 + int(m)


# ---------- routine ----------
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
    from .data import TAG_COLORS
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
            m[date] = day_frac(log, habits, date.isoformat())
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


def effective_habit_log(habits, log, journal, sales_daily, clients,
                        weights, today):
    """Merge manual ticks with auto-ticks derived from REAL data, so the
    consistency wall reflects what actually happened. Never mutates the
    stored log; only adds True where real evidence exists. The weigh-in
    stays optional - it auto-ticks only on days a weigh-in was logged."""
    eff = {}
    for hid, d in (log or {}).items():
        eff[hid] = dict(d or {})
    journal_dates = set(str(d)[:10] for d in (journal or {}).keys())
    sales_dates = set(str(d)[:10] for d in (sales_daily or {}).keys())
    client_dates = set()
    for c in (clients or []):
        if not isinstance(c, dict):
            continue
        for h in (c.get("history") or []):
            d = str((h or {}).get("ts", "") or "")[:10]
            if d:
                client_dates.add(d)
    weight_dates = set(str((w or {}).get("date", "") or "")[:10]
                       for w in (weights or []))
    t_iso = today.isoformat() if hasattr(today, "isoformat") \
        else str(today)[:10]
    for h in (habits or []):
        hid = h.get("id")
        nm = str(h.get("name", "") or "").lower()
        src = None
        if "journal" in nm:
            src = journal_dates
        elif "sales" in nm or "rejection" in nm:
            src = sales_dates
        elif "client" in nm or "follow" in nm:
            src = client_dates
        elif "weigh" in nm:
            src = weight_dates
        if src is None:
            continue
        cur = eff.setdefault(hid, {})
        for d in src:
            if d and d <= t_iso and not cur.get(d):
                cur[d] = True
    return eff


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
    from .data import START_DATE
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
def is_cash_offer(c):
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


def follow_backs(clients, now_dt):
    """[(client, follow_at_iso, due_or_missed)] sorted by time."""
    now_iso = now_dt.isoformat()
    out = []
    for c in (clients or []):
        if not isinstance(c, dict):
            continue
        if c.get("ended") or c.get("follow_done"):
            continue
        fa = str(c.get("follow_at") or "")
        if not fa:
            continue
        out.append((c, fa, fa <= now_iso))
    out.sort(key=lambda x: x[1])
    return out


def follow_missed_count(clients, now_dt):
    return sum(1 for _c, _fa, due in follow_backs(clients, now_dt)
               if due)


def client_counts(clients, today):
    t = today.isoformat()
    wk = (today + dt.timedelta(days=7)).isoformat()
    term = terminal_ids()
    won = role_id("won")
    ret = role_id("returned")
    lost = role_id("lost")
    act = [c for c in clients if is_active_pipeline(c)]
    return dict(
        active=len(act),
        due=[c for c in act if c.get("next_date") == t],
        over=[c for c in act
              if c.get("next_date") and c["next_date"] < t],
        up=[c for c in act if c.get("next_date")
            and t < c["next_date"] <= wk],
        new7=sum(1 for c in clients if c.get("created", "") >=
                 (today - dt.timedelta(days=6)).isoformat()),
        sold=sum(1 for c in clients if won and c.get("stage") == won),
        cashq=sum(1 for c in clients if is_cash_offer(c)),
        returned=sum(1 for c in clients if ret
                     and c.get("stage") == ret),
        lost=sum(1 for c in clients if lost and c.get("stage") == lost),
    )


def stage_counts(clients):
    out = {}
    for c in clients:
        s = c.get("stage", "new")
        out[s] = out.get(s, 0) + 1
    return out


def call_sheet(clients, today):
    t = today.isoformat()
    act = [c for c in clients if is_active_pipeline(c)]
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


def flow_effect(f):
    k = f.get("kind")
    a = float(f.get("amount", 0))
    if k == "in":
        return abs(a)
    if k == "out":
        return -abs(a)
    return a


def flow_week_inout(flow, today):
    lo = (today - dt.timedelta(days=6)).isoformat()
    i = o = 0.0
    for f in flow:
        if f.get("date", "") < lo:
            continue
        if f.get("kind") == "in":
            i += abs(float(f.get("amount", 0)))
        elif f.get("kind") == "out":
            o += abs(float(f.get("amount", 0)))
    return i, o


# ---------- money OS ----------
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


def active_funds(v):
    return [f for f in v.get("funds", []) if not f.get("sealed")]


def sealed_funds(v):
    return [f for f in v.get("funds", []) if f.get("sealed")]


def active_funds_balance(v):
    return sum(float(f.get("balance", 0)) for f in active_funds(v))


def sealed_funds_balance(v):
    return sum(float(f.get("balance", 0)) for f in sealed_funds(v))


def emergency_balance(v):
    return float(v.get("emergency", {}).get("balance", 0) or 0)


def protected_total(v):
    return emergency_balance(v) + sealed_funds_balance(v)


def safety_runway_months(v):
    b = float(v.get("runway", {}).get("monthly_burn", 0) or 0)
    if b <= 0:
        return None
    return protected_total(v) / b


def allocated(v):
    return (bills_saved(v) + fun_remaining(v) + items_saved(v)
            + active_funds_balance(v))


def net_worth(v):
    return cash_on_hand(v) + active_funds_balance(v)


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


# ---------- pantry / runway / emergency ----------
def pantry_days_left_item(it, today):
    daily = float(it.get("daily", 0) or 0)
    stock = float(it.get("stock", 0) or 0)
    if daily <= 0:
        return (None, None)
    raw = stock / daily
    chk = it.get("checked", "")
    age = 0
    if chk:
        try:
            age = max(0, (today - dt.date.fromisoformat(chk)).days)
        except Exception:
            age = 0
    aged = max(0.0, raw - age)
    return (raw, aged)


def pantry_bottleneck(pantry, today):
    items = [it for it in pantry.get("items", [])
             if not it.get("hidden")
             and float(it.get("daily", 0) or 0) > 0]
    best = None
    for it in items:
        raw, aged = pantry_days_left_item(it, today)
        if aged is None:
            continue
        if best is None or aged < best[0]:
            best = (aged, raw, it.get("name", "?"))
    return best


def pantry_checked_age(pantry, today):
    upd = pantry.get("updated", "")
    if not upd:
        return None
    try:
        return max(0, (today - dt.date.fromisoformat(upd)).days)
    except Exception:
        return None


def runway_months(vault):
    burn = float(vault.get("runway", {}).get("monthly_burn", 0) or 0)
    if burn <= 0:
        return None
    return cash_on_hand(vault) / burn


def emergency_target(vault):
    burn = float(vault.get("runway", {}).get("monthly_burn", 0) or 0)
    months = int(vault.get("runway", {}).get("emergency_months", 3) or 3)
    return burn * months


def emergency_progress(vault):
    t = emergency_target(vault)
    if t <= 0:
        return 0.0
    return max(0.0, min(100.0, emergency_balance(vault) / t * 100))


# ---------- spiritual energy ----------
def _spirit_present(e):
    if not e:
        return False
    return (float(e.get("minutes", 0) or 0) > 0
            or bool((e.get("felt") or "").strip())
            or bool((e.get("word") or "").strip())
            or bool(e.get("acts")))


def spiritual_energy(e):
    if not e:
        return 0
    mins = float(e.get("minutes", 0) or 0)
    depth = int(e.get("depth", 0) or 0)
    acts = e.get("acts") or []
    felt = (e.get("felt") or "").strip()
    presence = 25.0 if (mins > 0 or felt or e.get("word") or acts) else 0.0
    m_comp = min(mins / 60.0, 1.0) * 25.0
    d_comp = (max(0, min(depth, 5)) / 5.0) * 25.0
    a_comp = min(len(acts) / 3.0, 1.0) * 15.0
    r_comp = min(len(felt) / 20.0, 1.0) * 10.0
    return int(max(0, min(100, round(presence + m_comp + d_comp
                                     + a_comp + r_comp))))


def spiritual_streak(spiritual):
    today = dt.date.today()
    s = 0
    for o in range(400):
        d = (today - dt.timedelta(days=o)).isoformat()
        if _spirit_present(spiritual.get(d)):
            s += 1
        else:
            break
    return s


def spiritual_series(spiritual, n=30):
    today = dt.date.today()
    out = []
    for o in range(n - 1, -1, -1):
        d = today - dt.timedelta(days=o)
        e = spiritual.get(d.isoformat())
        if e is not None:
            out.append((d, spiritual_energy(e)))
    return out


def spiritual_health(spiritual, n=30):
    pts = spiritual_series(spiritual, n)
    if not pts:
        return 0.0
    return sum(v for _, v in pts) / len(pts)


def spiritual_today(spiritual, today):
    e = spiritual.get(today.isoformat())
    return spiritual_energy(e) if e is not None else None


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
    clients = ctx["clients"]
    term = terminal_ids()
    non_t = [c for c in clients if c.get("stage") not in term]
    outcomes = [c for c in clients
                if c.get("paid_date") == d_iso
                or c.get("returned_date") == d_iso]
    v = ctx["vault"]
    flow = [f for f in v.get("flow", []) if f.get("date") == d_iso]
    se = ctx.get("spiritual", {}).get(d_iso)
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
        "bot_logs": [l for l in ctx["bots"].get("logs", [])
                     if l.get("date") == d_iso],
        "weight": next((w for w in ctx["weights"]
                        if w.get("date") == d_iso), None),
        "tasks_done": [t for t in ctx["tasks"]
                       if t.get("done_date") == d_iso],
        "spiritual": spiritual_energy(se) if se is not None else None,
    }
