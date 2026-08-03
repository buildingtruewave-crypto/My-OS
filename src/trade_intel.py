"""Trade Intelligence - the connected analyst council.
The trading app SENDS each Deriv trade (profit/loss) into Supabase. PULSE
RECEIVES it, stores it in the deriv_trades table, and continuously scans it
across 7d / 30d / 90d / all-time windows to answer one question:
"is this a good venture, and how much can we risk?"

Everything is deterministic and measurable - real expectancy, profit factor,
drawdown and fractional-Kelly sizing. The council returns WAIT until the
sample is large enough; it never gambles on a handful of trades. The LLM
router only narrates the findings; the verdict is pure math. Fails open: if
Supabase is offline the panel shows a clean OFFLINE state, never an error.
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

MIN_SAMPLE = 20          # trades needed before a real verdict
CACHE_TTL = 60           # seconds between Supabase pulls
_PNL_KEYS = ("pnl", "profit", "profit_loss", "pl", "net",
             "result", "amount", "pips_amount")
_TS_KEYS = ("ts", "timestamp", "time", "created_at", "date",
            "closed_at", "trade_time")


# ---------------------------------------------------------------------------
# low-level helpers
# ---------------------------------------------------------------------------
def _utcnow():
    try:
        return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    except Exception:
        return dt.datetime.utcnow()


def _naive(d):
    if d is None:
        return dt.datetime.min
    try:
        return d.replace(tzinfo=None)
    except Exception:
        return d


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


# ---------------------------------------------------------------------------
# Supabase table + fetch
# ---------------------------------------------------------------------------
def _create_table(conn):
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS deriv_trades ("
            " id BIGSERIAL PRIMARY KEY,"
            " ts TIMESTAMPTZ DEFAULT now(),"
            " pnl DOUBLE PRECISION,"
            " stake DOUBLE PRECISION,"
            " market TEXT,"
            " strategy TEXT,"
            " note TEXT"
            ");")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS deriv_trades_ts_idx "
            "ON deriv_trades (ts);")
    conn.commit()


def _columns(conn, table="deriv_trades"):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = %s ORDER BY ordinal_position;",
            (table,))
        return [r[0] for r in cur.fetchall()]


def _normalize(rows, cols):
    lower = [c.lower() for c in cols]
    ts_col = next((cols[i] for i, c in enumerate(lower)
                   if c in _TS_KEYS), None)
    pnl_col = next((cols[i] for i, c in enumerate(lower)
                    if c in _PNL_KEYS), None)
    if pnl_col is None:
        return None
    out = []
    for r in rows:
        d = dict(r)
        pnl = _to_float(d.get(pnl_col))
        if pnl is None:
            continue
        ts = _to_dt(d.get(ts_col)) if ts_col else None
        out.append({
            "ts": ts,
            "pnl": pnl,
            "stake": _to_float(d.get("stake")),
            "market": d.get("market") or d.get("symbol") or "",
            "note": d.get("note") or d.get("strategy") or "",
        })
    out.sort(key=lambda x: _naive(x["ts"]))
    return out


def fetch_trades(limit=4000):
    """Return (trades, message). trades is None on failure, [] if empty."""
    if not _HAS_SB:
        return None, "supabase module not loaded"
    conn = SB.get_connection()
    if conn is None:
        return None, "cannot reach Supabase"
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.deriv_trades');")
            exists = cur.fetchone()[0]
        if not exists:
            _create_table(conn)
            return [], "table ready - waiting for the trading app"
        cols = _columns(conn)
        if not cols:
            return [], "table ready - waiting for the trading app"
        lower = [c.lower() for c in cols]
        pnl_col = next((c for c in lower if c in _PNL_KEYS), None)
        if pnl_col is None:
            return None, ("no pnl column found - expected one of: "
                          + ", ".join(_PNL_KEYS))
        ts_col = next((c for c in lower if c in _TS_KEYS), "id")
        try:
            import psycopg2.extras as _pe
            _cf = _pe.RealDictCursor
        except Exception:
            _cf = None
        with conn.cursor(cursor_factory=_cf) as cur:
            cur.execute("SELECT * FROM deriv_trades ORDER BY "
                        + ts_col + " DESC LIMIT %s;", (int(limit),))
            rows = cur.fetchall()
        norm = _normalize(rows, cols)
        if norm is None:
            return None, "could not read a pnl column"
        return norm, "ok"
    except Exception as e:
        return None, str(e)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# measurable statistics
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
    base = {"n": n, "net": 0.0, "win_rate": 0.0, "wins": 0, "losses": 0,
            "avg_win": 0.0, "avg_loss": 0.0, "expectancy": 0.0,
            "profit_factor": 0.0, "gross_profit": 0.0, "gross_loss": 0.0,
            "max_drawdown": 0.0, "max_cons_loss": 0, "sharpe": 0.0}
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
    run = 0.0
    peak = 0.0
    mdd = 0.0
    for p in pnls:
        run += p
        if run > peak:
            peak = run
        dd = peak - run
        if dd > mdd:
            mdd = dd
    mcl = 0
    cur = 0
    for p in pnls:
        if p <= 0:
            cur += 1
            if cur > mcl:
                mcl = cur
        else:
            cur = 0
    mean = net / n
    var = sum((p - mean) ** 2 for p in pnls) / n
    std = var ** 0.5
    sharpe = (mean / std) if std > 0 else 0.0
    base.update({"net": net, "win_rate": wr, "wins": len(wins),
                 "losses": len(losses), "avg_win": aw, "avg_loss": al,
                 "expectancy": exp, "profit_factor": pf,
                 "gross_profit": gp, "gross_loss": gl,
                 "max_drawdown": mdd, "max_cons_loss": mcl,
                 "sharpe": sharpe})
    return base


def _kelly(win_rate, avg_win, avg_loss):
    if avg_loss <= 0 or avg_win <= 0:
        return 0.0
    b = avg_win / avg_loss
    q = 1.0 - win_rate
    k = win_rate - (q / b)
    return max(0.0, k)


def _risk_pct(all_s):
    if all_s["expectancy"] <= 0:
        return 0.0
    k = _kelly(all_s["win_rate"], all_s["avg_win"], all_s["avg_loss"])
    quarter = k * 0.25
    return round(min(quarter, 0.05) * 100.0, 2)


def _venture_score(a, r):
    n = a["n"]
    if n == 0:
        return 0
    score = 50.0
    pf = min(a["profit_factor"], 99.0)
    if a["expectancy"] > 0:
        score += 15
    else:
        score -= 20
    if pf >= 2.0:
        score += 15
    elif pf >= 1.5:
        score += 10
    elif pf >= 1.2:
        score += 5
    elif pf >= 1.0:
        score += 0
    else:
        score -= 15
    gp = a["gross_profit"]
    if gp > 0:
        ratio = a["max_drawdown"] / gp
        if ratio < 0.25:
            score += 10
        elif ratio < 0.5:
            score += 5
        elif ratio < 1.0:
            score -= 5
        else:
            score -= 15
    if a["max_cons_loss"] >= 8:
        score -= 10
    elif a["max_cons_loss"] >= 5:
        score -= 5
    if r.get("n", 0) >= 10 and n >= 30:
        if r["expectancy"] < 0 and a["expectancy"] > 0:
            score -= 10
        elif r["expectancy"] > a["expectancy"]:
            score += 5
    return int(max(0, min(100, round(score))))


def _conf(n):
    if n >= 100:
        return "high"
    if n >= 50:
        return "medium"
    return "low"


def _verdict(all_s, recent_s, score):
    n = all_s["n"]
    if n < MIN_SAMPLE:
        return {"action": "WAIT", "score": score, "risk_pct": 0.0,
                "confidence": "low",
                "summary": ("Only %d trades logged. The council won't call "
                            "a venture on a sample this small - keep the bot "
                            "logging; the verdict sharpens at %d+ trades."
                            % (n, MIN_SAMPLE))}
    risk = _risk_pct(all_s)
    if score >= 70 and all_s["expectancy"] > 0:
        return {"action": "ENTER", "score": score, "risk_pct": risk,
                "confidence": _conf(n),
                "summary": ("Positive expectancy with controlled drawdown. "
                            "The council says take it - size each trade at "
                            "~%.2f%% of bankroll (quarter-Kelly, capped at "
                            "5%%)." % risk)}
    if score >= 55 and all_s["expectancy"] > 0:
        risk = min(risk, 2.0)
        return {"action": "ENTER SMALL", "score": score, "risk_pct": risk,
                "confidence": _conf(n),
                "summary": ("A real but modest edge. Enter at pilot size "
                            "(~%.2f%% per trade) and scale only if the next "
                            "%d trades hold up." % (risk, MIN_SAMPLE))}
    if score >= 40:
        return {"action": "WAIT", "score": score, "risk_pct": 0.0,
                "confidence": _conf(n),
                "summary": ("Borderline - the edge isn't proven yet. Keep "
                            "logging; don't commit real risk." )}
    return {"action": "AVOID", "score": score, "risk_pct": 0.0,
            "confidence": _conf(n),
            "summary": ("Negative or unproven edge with risky drawdown "
                        "behaviour. Stay out until the numbers improve.")}


# ---------------------------------------------------------------------------
# the analyst council (deterministic, measurable)
# ---------------------------------------------------------------------------
def _council(a, r):
    out = []
    if a["n"] == 0:
        out.append({"name": "Edge Analyst", "stance": "cautious",
                    "point": "No trades yet - nothing to measure."})
    else:
        pf = min(a["profit_factor"], 99.0)
        if a["expectancy"] > 0 and pf >= 1.5:
            out.append({"name": "Edge Analyst", "stance": "bullish",
                        "point": ("Expectancy %+.2f/trade with a %.2f profit "
                                  "factor - a genuine edge."
                                  % (a["expectancy"], pf))})
        elif a["expectancy"] > 0:
            out.append({"name": "Edge Analyst", "stance": "cautious",
                        "point": ("Expectancy is positive (%+.2f) but the "
                                  "%.2f profit factor is thin."
                                  % (a["expectancy"], pf))})
        else:
            out.append({"name": "Edge Analyst", "stance": "bearish",
                        "point": ("Expectancy is negative (%+.2f/trade) - the "
                                  "system loses on average."
                                  % a["expectancy"])})
    if a["n"] == 0:
        out.append({"name": "Risk Analyst", "stance": "cautious",
                    "point": "No exposure yet."})
    else:
        dd = a["max_drawdown"]
        gp = a["gross_profit"]
        ratio = (dd / gp) if gp > 0 else (9.9 if dd > 0 else 0.0)
        if a["max_cons_loss"] >= 8 or ratio >= 1.0:
            tail = (" (%.0f%% of gross profit)" % (ratio * 100)) if gp > 0 else ""
            out.append({"name": "Risk Analyst", "stance": "bearish",
                        "point": ("Max drawdown %.2f%s and %d straight losses "
                                  "- the downside is violent."
                                  % (dd, tail, a["max_cons_loss"]))})
        elif a["max_cons_loss"] >= 5 or ratio >= 0.5:
            out.append({"name": "Risk Analyst", "stance": "cautious",
                        "point": ("Drawdown %.2f and a %d-loss streak - "
                                  "manageable, but watch sizing."
                                  % (dd, a["max_cons_loss"]))})
        else:
            out.append({"name": "Risk Analyst", "stance": "bullish",
                        "point": ("Drawdown is contained (%.2f) and losing "
                                  "streaks stay short (%d)."
                                  % (dd, a["max_cons_loss"]))})
    n = a["n"]
    if n >= 100:
        out.append({"name": "Sample Analyst", "stance": "bullish",
                    "point": "%d trades - the statistics are trustworthy." % n})
    elif n >= MIN_SAMPLE:
        out.append({"name": "Sample Analyst", "stance": "cautious",
                    "point": "%d trades - enough for a first read, keep logging." % n})
    else:
        out.append({"name": "Sample Analyst", "stance": "bearish",
                    "point": "Only %d trades - far too early to call this." % n})
    if r.get("n", 0) < 5:
        out.append({"name": "Form Analyst", "stance": "cautious",
                    "point": "Not enough recent trades to judge form."})
    else:
        if r["expectancy"] > a["expectancy"]:
            out.append({"name": "Form Analyst", "stance": "bullish",
                        "point": ("Last 30d expectancy (%+.2f) beats the "
                                  "all-time (%+.2f) - improving."
                                  % (r["expectancy"], a["expectancy"]))})
        elif r["expectancy"] < 0 and a["expectancy"] > 0:
            out.append({"name": "Form Analyst", "stance": "bearish",
                        "point": ("The last 30d turned negative (%+.2f) while "
                                  "the all-time edge is positive - the edge "
                                  "may be fading." % r["expectancy"])})
        else:
            out.append({"name": "Form Analyst", "stance": "cautious",
                        "point": ("Recent form (%+.2f/trade) is holding near "
                                  "the long-term level." % r["expectancy"])})
    return out


# ---------------------------------------------------------------------------
# discussion narration (LLM if available, deterministic fallback)
# ---------------------------------------------------------------------------
def _build_prompt(rep):
    a = rep["windows"]["all"]
    r = rep["windows"]["30d"]
    v = rep["verdict"]
    pf = min(a["profit_factor"], 99.0)
    lines = []
    lines.append("You are a four-analyst trading council reviewing a Deriv "
                 "bot's live results for one operator. Speak plainly, weigh "
                 "risk honestly, and reference only the numbers given.")
    lines.append("")
    lines.append("All-time: %d trades | net %s | win rate %.1f%% | "
                 "expectancy %s/trade | profit factor %.2f | max drawdown "
                 "%s | longest losing streak %d."
                 % (a["n"], _money(a["net"]), a["win_rate"] * 100,
                    _money(a["expectancy"]), pf,
                    _money(a["max_drawdown"]), a["max_cons_loss"]))
    lines.append("Last 30d: %d trades | net %s | expectancy %s/trade."
                 % (r["n"], _money(r["net"]), _money(r["expectancy"])))
    lines.append("")
    lines.append("Council findings:")
    for c in rep["council"]:
        lines.append("- %s (%s): %s" % (c["name"], c["stance"], c["point"]))
    lines.append("")
    lines.append("Deterministic verdict: %s | score %d/100 | suggested risk "
                 "%.2f%% of bankroll per trade | confidence %s."
                 % (v["action"], v["score"], v["risk_pct"], v["confidence"]))
    lines.append("")
    lines.append("Write the council's final discussion in at most 5 short "
                 "sentences. Cover the edge, then the risk, then whether the "
                 "sample is trustworthy, then end with a clear verdict on "
                 "whether to enter this venture and at what size. Do not "
                 "invent numbers. Plain text only, no headings, no emojis.")
    return "\n".join(lines)


def _fallback_discussion(rep):
    parts = []
    for c in rep["council"]:
        parts.append("%s (%s): %s"
                     % (c["name"], c["stance"].upper(), c["point"]))
    v = rep["verdict"]
    parts.append("VERDICT: %s - %s" % (v["action"], v["summary"]))
    return "\n".join(parts)


def _discussion(rep):
    if _HAS_ROUTER:
        try:
            if _R.has_providers():
                text, _prov = _R.chat(
                    [{"role": "user", "content": _build_prompt(rep)}],
                    temperature=0.6, max_tokens=320)
                if text:
                    return text
        except Exception:
            pass
    return _fallback_discussion(rep)


# ---------------------------------------------------------------------------
# assembly + caching
# ---------------------------------------------------------------------------
def _build():
    now = _utcnow()
    trades, msg = fetch_trades()
    if trades is None:
        return {"connected": False, "message": msg, "n_total": 0,
                "windows": {"7d": _stats([]), "30d": _stats([]),
                            "90d": _stats([]), "all": _stats([])},
                "council": [], "verdict": None, "discussion": "",
                "recent": [], "last_sync": now.isoformat(),
                "span_days": 0, "earliest": "", "latest": ""}
    windows = {}
    for label, days in (("7d", 7), ("30d", 30), ("90d", 90), ("all", None)):
        windows[label] = _stats(_window(trades, days, now))
    all_s = windows["all"]
    recent_s = windows["30d"]
    score = _venture_score(all_s, recent_s)
    council = _council(all_s, recent_s)
    verdict = _verdict(all_s, recent_s, score)
    ts_list = [_naive(t["ts"]) for t in trades if t["ts"] is not None]
    span = 0
    earliest = ""
    latest = ""
    if ts_list:
        span = (max(ts_list) - min(ts_list)).days
        earliest = min(ts_list).strftime("%b %d, %Y")
        latest = max(ts_list).strftime("%b %d, %Y")
    rep = {"windows": windows, "council": council, "verdict": verdict,
           "n_total": len(trades)}
    discussion = _discussion(rep)
    recent = list(reversed(trades))[:12]
    return {"connected": True, "message": msg, "n_total": len(trades),
            "windows": windows, "council": council, "verdict": verdict,
            "discussion": discussion, "recent": recent,
            "last_sync": now.isoformat(), "span_days": span,
            "earliest": earliest, "latest": latest}


def get_signal(force=False):
    """Return the intelligence report, cached for CACHE_TTL seconds."""
    try:
        import time as _time
        now = _time.time()
        cache = st.session_state.get("_ti_cache")
        if cache and not force and (now - cache.get("at", 0) < CACHE_TTL):
            return cache.get("data")
        data = _build()
        st.session_state["_ti_cache"] = {"at": now, "data": data}
        return data
    except Exception as e:
        return {"connected": False, "message": str(e), "n_total": 0,
                "windows": {"7d": _stats([]), "30d": _stats([]),
                            "90d": _stats([]), "all": _stats([])},
                "council": [], "verdict": None, "discussion": "",
                "recent": [], "last_sync": "", "span_days": 0,
                "earliest": "", "latest": ""}
