"""Trade Intelligence - the connected analyst council.
The trading app SENDS trades + AI research + venture advice into Supabase.
PULSE RECEIVES it and shows the other app's council verdict (from
deriv_venture_advice) as the primary read, with PULSE's own deterministic
math (expectancy / profit factor / drawdown / fractional-Kelly) as a
cross-check. Fails open everywhere - a missing table never breaks the page.
"""
from __future__ import annotations

import datetime as dt

import streamlit as st

try:
    from . import supabase_db as SB
    _HAS_SB = True
except Exception:
    SB = None
    _HAS_SB = False

try:
    from . import llm_router as _R
    _HAS_ROUTER = True
except Exception:
    _R = None
    _HAS_ROUTER = False

MIN_SAMPLE = 20
CACHE_TTL = 60
_PNL_KEYS = ("pnl", "profit", "profit_loss", "pl", "net",
             "result", "amount", "pips_amount")
_TS_KEYS = ("ts", "timestamp", "time", "created_at", "date",
            "closed_at", "trade_time")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _utcnow():
    try:
        return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    except Exception:
        return dt.datetime.utcnow()


def _naive(d):
    if d is None:
        return dt.datetime.min
    if isinstance(d, dt.datetime):
        return d.replace(tzinfo=None)
    if isinstance(d, dt.date):
        return dt.datetime(d.year, d.month, d.day)
    return dt.datetime.min


def _to_dt(v):
    if isinstance(v, dt.datetime):
        return v
    if isinstance(v, dt.date):
        return dt.datetime(v.year, v.month, v.day)
    if v is None:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt)
        except Exception:
            continue
    try:
        return dt.datetime.fromisoformat(s)
    except Exception:
        return None


def _to_float(v):
    try:
        return float(v)
    except Exception:
        return None


def _money(x):
    try:
        return "%+.2f" % float(x)
    except Exception:
        return "+0.00"


def _normalize(rows):
    out = []
    for d in rows:
        if not isinstance(d, dict):
            continue
        pnl = None
        for k in _PNL_KEYS:
            if k in d and d[k] is not None:
                pnl = _to_float(d[k])
                if pnl is not None:
                    break
        if pnl is None:
            continue
        ts = None
        for k in _TS_KEYS:
            if k in d and d[k] is not None:
                ts = _to_dt(d[k])
                if ts is not None:
                    break
        out.append({
            "ts": ts, "pnl": pnl,
            "stake": _to_float(d.get("stake") or d.get("lots")),
            "market": d.get("symbol") or d.get("asset")
            or d.get("market") or "",
            "direction": d.get("direction") or d.get("side") or "",
            "strategy": d.get("strategy") or "",
            "note": d.get("note") or "",
        })
    out.sort(key=lambda x: _naive(x["ts"]))
    return out


# ---------------------------------------------------------------------------
# remote research / advice
# ---------------------------------------------------------------------------
def _map_action(verdict_text):
    v = (verdict_text or "").upper()
    if any(k in v for k in ("AVOID", "STAY OUT", "NO TRADE", "STOP",
                            "STAND DOWN")):
        return "AVOID", "#F0556B"
    if any(k in v for k in ("WAIT", "HOLD", "OBSERVE", "STAND BY")):
        return "WAIT", "#F5B544"
    if any(k in v for k in ("SMALL", "PILOT", "CAUTION", "HALF",
                            "REDUCED")):
        return "ENTER SMALL", "#2DD4BF"
    if any(k in v for k in ("ENTER", "GO", "YES", "TAKE", "PROCEED",
                            "FAVORABLE")):
        return "ENTER", "#34D399"
    return "WATCH", "#7C8AA5"


def _agg_research(rows):
    agg = {"n": 0, "strengths": 0, "weaknesses": 0, "mistakes": 0,
           "patterns": {}}
    if not rows:
        return agg
    agg["n"] = len(rows)
    for r in rows:
        try:
            agg["strengths"] += len(r.get("strengths") or [])
            agg["weaknesses"] += len(r.get("weaknesses") or [])
            agg["mistakes"] += len(r.get("mistakes") or [])
        except Exception:
            pass
        p = str(r.get("pattern_detected") or "").strip()
        if p:
            agg["patterns"][p] = agg["patterns"].get(p, 0) + 1
    return agg


def _fetch_remote():
    out = {"advice": None, "verdict_view": None, "research": None,
           "knowledge": [], "has_trades": False}
    if not _HAS_SB:
        return out
    out["has_trades"] = SB.first_existing(
        ["trades", "deriv_trades", "bot_trades"]) is not None
    rows, _e = SB.fetch_rows("deriv_venture_advice", limit=1,
                             order="created_at.desc")
    if rows:
        adv = rows[0]
        action, color = _map_action(adv.get("verdict"))
        out["advice"] = adv
        out["verdict_view"] = {
            "action": action, "color": color,
            "raw": str(adv.get("verdict") or ""),
            "risk_pct": _to_float(adv.get("max_risk_pct")) or 0.0,
            "multiplier": _to_float(adv.get("risk_multiplier")),
            "confidence": _to_float(adv.get("confidence")),
            "reasoning": str(adv.get("reasoning") or ""),
            "period_days": adv.get("period_days"),
            "discussion": adv.get("discussion") or {},
        }
    krows, _e2 = SB.fetch_rows("deriv_research_knowledge", limit=12,
                               order="last_seen.desc")
    if krows:
        out["knowledge"] = krows
    rrows, _e3 = SB.fetch_rows("deriv_trade_research", limit=50,
                               order="created_at.desc")
    if rrows:
        out["research"] = _agg_research(rrows)
    return out


# ---------------------------------------------------------------------------
# local deterministic stats (cross-check)
# ---------------------------------------------------------------------------
def _window(trades, days, now):
    if days is None:
        return trades
    cutoff = now - dt.timedelta(days=days)
    return [t for t in trades
            if t["ts"] is not None and _naive(t["ts"]) >= cutoff]


def _stats(rows):
    pnls = [t["pnl"] for t in rows if t.get("pnl") is not None]
    n = len(pnls)
    base = {"n": n, "net": 0.0, "win_rate": 0.0, "wins": 0,
            "losses": 0, "avg_win": 0.0, "avg_loss": 0.0,
            "expectancy": 0.0, "profit_factor": 0.0,
            "max_drawdown": 0.0, "max_cons_loss": 0}
    if n == 0:
        return base
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    net = sum(pnls)
    wr = len(wins) / n
    aw = gp / len(wins) if wins else 0.0
    al = gl / len(losses) if losses else 0.0
    exp = (wr * aw) - ((1 - wr) * al)
    pf = (gp / gl) if gl > 0 else (99.0 if gp > 0 else 0.0)
    run = peak = mdd = 0.0
    for p in pnls:
        run += p
        if run > peak:
            peak = run
        dd = peak - run
        if dd > mdd:
            mdd = dd
    mcl = cur = 0
    for p in pnls:
        if p <= 0:
            cur += 1
            if cur > mcl:
                mcl = cur
        else:
            cur = 0
    base.update({"net": net, "win_rate": wr, "wins": len(wins),
                 "losses": len(losses), "avg_win": aw, "avg_loss": al,
                 "expectancy": exp, "profit_factor": pf,
                 "max_drawdown": mdd, "max_cons_loss": mcl})
    return base


def _kelly(win_rate, avg_win, avg_loss):
    if avg_loss <= 0 or avg_win <= 0:
        return 0.0
    b = avg_win / avg_loss
    q = 1.0 - win_rate
    return max(0.0, win_rate - (q / b))


def _risk_pct(all_s):
    if all_s["expectancy"] <= 0:
        return 0.0
    return round(min(_kelly(all_s["win_rate"], all_s["avg_win"],
                            all_s["avg_loss"]) * 0.25, 0.05) * 100.0, 2)


def _venture_score(a):
    n = a["n"]
    if n == 0:
        return 0
    score = 50.0
    pf = min(a["profit_factor"], 99.0)
    score += 15 if a["expectancy"] > 0 else -20
    if pf >= 2.0:
        score += 15
    elif pf >= 1.5:
        score += 10
    elif pf >= 1.2:
        score += 5
    elif pf < 1.0:
        score -= 15
    if a["max_cons_loss"] >= 8:
        score -= 10
    elif a["max_cons_loss"] >= 5:
        score -= 5
    return int(max(0, min(100, round(score))))


def _local_verdict(all_s, score):
    n = all_s["n"]
    if n < MIN_SAMPLE:
        return {"action": "WAIT", "score": score,
                "risk_pct": 0.0, "confidence": "low",
                "summary": ("Only %d trades logged - the cross-check "
                            "needs %d+ to speak." % (n, MIN_SAMPLE))}
    risk = _risk_pct(all_s)
    if score >= 70 and all_s["expectancy"] > 0:
        return {"action": "ENTER", "score": score, "risk_pct": risk,
                "confidence": "high" if n >= 100 else "medium",
                "summary": "Positive expectancy, controlled drawdown."}
    if score >= 55 and all_s["expectancy"] > 0:
        return {"action": "ENTER SMALL", "score": score,
                "risk_pct": min(risk, 2.0),
                "confidence": "medium",
                "summary": "Real but modest edge - pilot size."}
    if score >= 40:
        return {"action": "WAIT", "score": score, "risk_pct": 0.0,
                "confidence": "medium",
                "summary": "Borderline - keep logging."}
    return {"action": "AVOID", "score": score, "risk_pct": 0.0,
            "confidence": "medium",
            "summary": "Negative or unproven edge."}


def _council(a):
    out = []
    pf = min(a["profit_factor"], 99.0)
    if a["n"] == 0:
        return [{"name": "Edge Analyst", "stance": "cautious",
                 "point": "No trades yet - nothing to measure."}]
    if a["expectancy"] > 0 and pf >= 1.5:
        out.append({"name": "Edge Analyst", "stance": "bullish",
                    "point": "Expectancy %+.2f/trade, PF %.2f."
                    % (a["expectancy"], pf)})
    elif a["expectancy"] > 0:
        out.append({"name": "Edge Analyst", "stance": "cautious",
                    "point": "Positive expectancy (%+.2f) but thin PF."
                    % a["expectancy"]})
    else:
        out.append({"name": "Edge Analyst", "stance": "bearish",
                    "point": "Negative expectancy (%+.2f)."
                    % a["expectancy"]})
    if a["max_cons_loss"] >= 8:
        out.append({"name": "Risk Analyst", "stance": "bearish",
                    "point": "%d straight losses - violent downside."
                    % a["max_cons_loss"]})
    elif a["max_drawdown"] > 0:
        out.append({"name": "Risk Analyst", "stance": "cautious",
                    "point": "Max drawdown %.2f." % a["max_drawdown"]})
    else:
        out.append({"name": "Risk Analyst", "stance": "bullish",
                    "point": "Drawdown contained."})
    out.append({"name": "Sample Analyst",
                "stance": "bullish" if a["n"] >= 100 else
                ("cautious" if a["n"] >= MIN_SAMPLE else "bearish"),
                "point": "%d trades." % a["n"]})
    return out


# ---------------------------------------------------------------------------
# assembly + cache
# ---------------------------------------------------------------------------
def _build():
    now = _utcnow()
    rows, msg = (SB.fetch_trades() if _HAS_SB
                 else (None, "supabase_db not loaded"))
    if rows is None:
        return {"connected": False, "message": msg, "n_total": 0,
                "windows": {}, "council": [], "verdict": None,
                "recent": [], "remote": _fetch_remote() if _HAS_SB
                else {}, "last_sync": now.isoformat()}
    trades = _normalize(rows)
    windows = {}
    for label, days in (("7d", 7), ("30d", 30), ("90d", 90),
                        ("all", None)):
        windows[label] = _stats(_window(trades, days, now))
    all_s = windows["all"]
    score = _venture_score(all_s)
    remote = _fetch_remote()
    return {
        "connected": True, "message": msg,
        "n_total": len(trades), "windows": windows,
        "council": _council(all_s),
        "verdict": _local_verdict(all_s, score),
        "recent": list(reversed(trades))[:12],
        "remote": remote,
        "last_sync": now.isoformat(),
    }


def get_signal(force=False):
    try:
        import time as _time
        now = _time.time()
        cache = st.session_state.get("_ti_cache")
        if cache and not force \
                and (now - cache.get("at", 0) < CACHE_TTL):
            return cache.get("data")
        data = _build()
        st.session_state["_ti_cache"] = {"at": now, "data": data}
        return data
    except Exception as e:
        return {"connected": False, "message": str(e), "n_total": 0,
                "windows": {}, "council": [], "verdict": None,
                "recent": [], "remote": {}, "last_sync": ""}
