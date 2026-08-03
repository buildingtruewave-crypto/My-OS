"""Derived stats for the life OS, the TrueWave pipeline, the money OS, the
pantry / runway / emergency model, the spiritual energy model and the signal
layer. Pure read-side: never mutates, never auto-deducts.

Pipeline separation:
- ACTIVE PIPELINE = in-progress clients only (not ended, not terminal,
  not cash-offer).
- CASH-OFFER QUEUE = rejected clients; the `ended` flag never empties it.

Habits: optional habits (the weigh-in) are excluded from every consistency
computation. effective_habit_log merges stored ticks with habits that
auto-fill from real data (journal / sales / client touches / weigh-ins).

Life score weights: sales 25% · spirit 25% · journal 20% · goals 15% ·
habits 15%.
"""
from __future__ import annotations

import calendar as _cal
import datetime as dt

from .data import (EVENT_COLOR, EVENT_ICON, EVENT_LABELS,
                   START_DATE, habit_optional, habit_source,
                   is_active_pipeline, is_cash_offer, role_id,
                   stage_color, stage_label, terminal_ids)


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


# ---------- habit auto-fill ----------
def effective_habit_log(habits, stored_log, journal, sales_daily,
                        clients, weights, today):
    """Merge stored habit ticks with habits that are auto-detected from real
    data (journal / sales tally / client touches / weigh-ins). Auto habits
    are recomputed on every run, so they always self-correct - you never
    tick them. Optional habits (weigh-in) only ever get True entries, never
    False, so a day without a weigh-in stays neutral instead of reading as
    missed. Never mutates stored_log."""
    eff = {}
    for hid, days in (stored_log or {}).items():
        eff[hid] = dict(days)
    auto = []
    for h in (habits or []):
        src = habit_source(h)
        if src:
            auto.append((h, src))
    if not auto:
        return eff
    journal_dates = set()
    for d_iso, e in (journal or {}).items():
        if e and (e.get("happened") or e.get("win")
                  or e.get("lesson") or e.get("mood")):
            journal_dates.add(d_iso)
    sales_dates = set((sales_daily or {}).keys())
    client_dates = set()
    for c in (clients or []):
        for entry in c.get("history", []):
            ts = str(entry.get("ts", ""))[:10]
            if ts:
                client_dates.add(ts)
    weight_dates = set(w.get("date") for w in (weights or [])
                       if w.get("date"))
    src_dates = {"journal": journal_dates, "sales": sales_dates,
                 "clients": client_dates, "weigh": weight_dates}
    one = dt.timedelta(days=1)
    d = START_DATE
    while d <= today:
        diso = d.isoformat()
        for h, src in auto:
            optional = (src == "weigh")
            if diso in src_dates.get(src, set()):
                eff.setdefault(h["id"], {})[diso] = True
            elif not optional:
                eff.setdefault(h["id"], {})[diso] = False
        d += one
    return eff


# ---------- habits ----------
def day_frac(log, habits, date_iso):
    counted = [h for h in habits if not habit_optional(h)]
    if not counted:
        return 0.0
    done = sum(1 for h in counted
               if log.get(h["id"], {}).get(date_iso))
    return done / len(counted) * 100


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
    counted = [h for h in habits if not habit_optional(h)]
    if not counted:
        return 0.0
    pcts = [habit_stats(log, h["id"], n)[2] for h in counted]
    return sum(pcts) / len(pcts)


def consistency_by_weekday(habits, log, days=60):
    counted = [h for h in habits if not habit_optional(h)]
    today = dt.date.today()
    acc = {w: [] for w in range(7)}
    for o in range(days):
        d = today - dt.timedelta(days=o)
        ds = d.isoformat()
        vals = [1.0 if log.get(h["id"], {}).get(ds) else 0.0
                for h in counted]
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
    won = role_id("won")
    ret = role_id("returned")
    lost = role_id("lost")
    live = [c for c in clients if not c.get("ended")]
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
        sold=sum(1 for c in live if won and c.get("stage") == won),
        cashq=sum(1 for c in clients if is_cash_offer(c)),
        returned=sum(1 for c in live
                     if ret and c.get("stage") == ret),
        lost=sum(1 for c in live if lost and c.get("stage") == lost),
    )


def cash_queue(clients):
    """Every cash-offer (rejected) client. Deliberately ignores the `ended`
    flag: ending a journey never empties this queue. Only a terminal stage
    (Paid / Lost / Returned) removes a client from it."""
    return [c for c in clients if is_cash_offer(c)]


def stage_counts(clients):
    out = {}
    for c in clients:
        s = c.get("stage", "new")
        out[s] = out.get(s, 0) + 1
    return out


def call_sheet(clients, today):
    """In-progress clients only - cash-offer (rejected) clients are excluded
    because they live in their own queue."""
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


# ---------- spiritual energy (derived, never random) ----------
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
        auto=sum(1 for x in tasks if x.get("auto")),
    )


def life_score(cons, jcomp, srate, goal_avg, spirit=0.0):
    """Sales 25% · Spirit 25% · Journal 20% · Goals 15% · Habits 15%.
    Habits are supporting infrastructure, not the core of the OS."""
    v = (cons * 0.15 + jcomp * 0.20 + srate * 0.25
         + goal_avg * 0.15 + spirit * 0.25)
    return int(max(0, min(100, round(v))))


# ---------- signal layer ----------
def signal_feed(events, n=30):
    out = []
    for e in (events or [])[:n]:
        et = e.get("type", "note")
        out.append({
            "ts": e.get("ts", ""),
            "time": str(e.get("ts", ""))[11:16],
            "date": e.get("date", ""),
            "type": et,
            "label": e.get("label", EVENT_LABELS.get(et, et)),
            "detail": e.get("detail", ""),
            "icon": EVENT_ICON.get(et, "pulse"),
            "color": EVENT_COLOR.get(et, "#8893AB"),
            "autopilot": "autopilot" in (e.get("tags") or []),
        })
    return out


def signal_counts(events, today_iso):
    evs = events or []
    today_n = sum(1 for e in evs if e.get("date") == today_iso)
    auto_n = sum(1 for e in evs
                 if "autopilot" in (e.get("tags") or []))
    types = {}
    for e in evs:
        t = e.get("type", "note")
        types[t] = types.get(t, 0) + 1
    return dict(total=len(evs), today=today_n, autopilot=auto_n,
                types=types)


def day_pulse(d_iso, ctx):
    clients = ctx["clients"]
    act = [c for c in clients if is_active_pipeline(c)]
    outcomes = [c for c in clients
                if c.get("paid_date") == d_iso
                or c.get("returned_date") == d_iso]
    v = ctx["vault"]
    flow = [f for f in v.get("flow", []) if f.get("date") == d_iso]
    se = ctx.get("spiritual", {}).get(d_iso)
    events = [e for e in (ctx.get("events") or [])
              if e.get("date") == d_iso]
    return {
        "new_clients": [c for c in clients
                        if c.get("created") == d_iso],
        "followups": [c for c in act if c.get("next_date") == d_iso],
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
        "cash_offers": [e for e in events
                        if e.get("type") == "credit_cash_offer"],
        "events": events,
        "spiritual": spiritual_energy(se) if se is not None else None,
    }
