"""PULSE brain - offline, trainable, retrieval-augmented intelligence.

This is the layer that turns the companion from "reads the last three lines"
into a memory that knows you across time. It is pure standard library (no
Streamlit, no numpy) so no host or version can break it, and every public
function fails open: a corrupt index rebuilds, a bad search returns [], a
failed reflection is skipped. A bug here can never take down a page.

Design notes (the honest read of the blueprint bundle the operator supplied):
  * The DigitalOcean ELK blueprint is a *full-text search over your own
    history* engine. We translate that idea into a real, offline, in-app
    inverted index with TF-IDF + recency + mood + feedback weighting. No
    external vector DB, no embeddings, no network - retrieval that works on
    the bus with no signal.
  * The Airflow blueprint is a *durable scheduled-jobs* engine. We translate
    that into a nightly reflection pass that runs lazily once per calendar
    day (cached in data/brain_reflection.json) with no daemon. On a VPS the
    same files persist via the mounted data/ volume; if the operator ever
    scales to many heavy sources, a real scheduler (the Airflow pattern) is
    the migration target, but for one operator this lightweight equivalent
    is correct and already present.
  * The old trading-terminal PULSE files confirmed the design DNA and what
    NOT to regress (trading was deliberately retired for TrueWave); they are
    not reused here.

Privacy: money-sourced documents are indexed but only retrievable when the
caller passes allow_money=True (i.e. inside the locked Archive). The rule is
enforced at search time, not by trust.

Trainability: record_feedback() stores what the operator liked or disliked
together with the state they were in (mood band + page + which moves the
message used). is_suppressed() turns accumulated dislikes into learned rules
that the voice obeys, and complaint_notes() feeds the operator's own past
words back as constraints. All reset-able from Settings.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent / "data"
_IDX = _DATA / "brain_index.json"
_FB = _DATA / "brain_feedback.json"
_REFL = _DATA / "brain_reflection.json"

_STOP = set((
    "the", "and", "for", "that", "this", "with", "from", "they", "have",
    "been", "was", "were", "not", "but", "are", "its", "you", "your",
    "my", "me", "we", "our", "can", "will", "did", "do", "does", "has",
    "had", "about", "into", "over", "after", "before", "when", "while",
    "than", "then", "just", "like", "some", "more", "very", "today",
    "yesterday", "tomorrow", "day", "days", "one", "two", "got", "get",
    "make", "made", "much", "also", "still", "even", "only", "here",
    "there", "what", "which", "who", "how", "why", "because", "so",
    "would", "could", "should", "might", "may", "being", "through",
    "during", "again", "down", "out", "off", "up", "him", "her", "his",
    "she", "he", "them", "their", "these", "those", "am", "is", "it",
    "an", "in", "on", "at", "by", "to", "of", "or", "if", "as",
))

MONEY_SRCS = set(("money", "flow", "bill", "emergency", "fund"))

MOOD_LOW = set(("drained", "flat"))
MOOD_MID = set(("steady",))
MOOD_HIGH = set(("sharp", "on fire"))

FEATURES = (
    "quoted_memory", "quoted_verse", "money_advice", "pep_talk",
    "asked_back", "long_msg", "pattern_cited",
)

_TOK = re.compile(r"[a-z0-9]+")


# ---------------------------------------------------------------------------
# pure helpers
# ---------------------------------------------------------------------------

def mood_band(mood):
    m = (mood or "").strip().lower()
    if m in MOOD_LOW:
        return "low"
    if m in MOOD_MID:
        return "mid"
    if m in MOOD_HIGH:
        return "high"
    return "none"


def tokenize(text):
    out = []
    for tok in _TOK.findall((text or "").lower()):
        if len(tok) >= 3 and tok not in _STOP:
            out.append(tok)
    return out


def _bigrams(tokens):
    out = []
    for i in range(len(tokens) - 1):
        out.append(tokens[i] + " " + tokens[i + 1])
    return out


def _read_json(path):
    try:
        if path.exists() and path.stat().st_size > 0:
            return json.loads(path.read_text())
    except Exception:
        pass
    return None


def _write_json(path, obj):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, default=str))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# memory documents
# ---------------------------------------------------------------------------

def _doc(src, date, text, mood, tags, meta=None):
    t = (text or "").strip()
    if not t:
        return None
    return {
        "src": src, "date": str(date or ""), "text": t[:600],
        "mood": (mood or "").strip().lower(), "tags": list(tags or []),
        "meta": dict(meta or {}),
    }


def _docs_from_stores(stores):
    docs = []
    journal = stores.get("journal") or {}
    for d, e in journal.items():
        if not isinstance(e, dict):
            continue
        text = " ".join(filter(None, [
            e.get("happened"), e.get("win"), e.get("lesson"),
            e.get("gratitude"),
        ]))
        doc = _doc("journal", d, text, e.get("mood"),
                   ["journal", e.get("mood") or ""])
        if doc:
            docs.append(doc)
    spirit = stores.get("spiritual") or {}
    for d, e in spirit.items():
        if not isinstance(e, dict):
            continue
        acts = " ".join(e.get("acts") or [])
        text = " ".join(filter(None, [e.get("word"), e.get("felt"),
                                      e.get("gratitude"), acts]))
        doc = _doc("spirit", d, text, None,
                   ["spirit"] + list(e.get("acts") or []))
        if doc:
            docs.append(doc)
    for c in (stores.get("clients") or []):
        if not isinstance(c, dict):
            continue
        nm = c.get("name", "")
        src = c.get("source", "")
        stg = c.get("stage", "")
        for h in (c.get("history") or []):
            if not isinstance(h, dict):
                continue
            note = h.get("note", "")
            text = (nm + " " + note).strip()
            doc = _doc("client", h.get("ts", "")[:10], text, None,
                       ["client", stg, src],
                       {"name": nm, "phone": c.get("phone", "")})
            if doc:
                docs.append(doc)
    for x in (stores.get("income") or []):
        if not isinstance(x, dict):
            continue
        text = (str(x.get("type", "")) + " " + str(x.get("note", ""))).strip()
        doc = _doc("income", x.get("date", ""), text, None,
                   ["income", x.get("type", "")])
        if doc:
            docs.append(doc)
    for s in (stores.get("sales") or []):
        if not isinstance(s, dict):
            continue
        text = ("sale " + str(s.get("client", "")) + " "
                + str(s.get("phone", "")) + " "
                + str(s.get("phone_model", s.get("phone", "")))).strip()
        doc = _doc("sale", s.get("date", ""), text, None,
                   ["sale"], {"client": s.get("client", "")})
        if doc:
            docs.append(doc)
    vault = stores.get("vault") or {}
    for f in (vault.get("flow") or []):
        if not isinstance(f, dict):
            continue
        doc = _doc("flow", f.get("date", ""),
                   str(f.get("note", "")), None,
                   ["money", "flow", f.get("kind", "")])
        if doc:
            docs.append(doc)
    for b in (vault.get("bills") or []):
        if not isinstance(b, dict):
            continue
        doc = _doc("bill", b.get("due", ""),
                   str(b.get("name", "")), None, ["money", "bill"])
        if doc:
            docs.append(doc)
    for t in ((vault.get("emergency") or {}).get("tx") or []):
        if not isinstance(t, dict):
            continue
        doc = _doc("emergency", t.get("date", ""),
                   str(t.get("note", "")), None, ["money", "emergency"])
        if doc:
            docs.append(doc)
    for f in (vault.get("funds") or []):
        if not isinstance(f, dict):
            continue
        for t in (f.get("tx") or []):
            if not isinstance(t, dict):
                continue
            doc = _doc("fund", t.get("date", ""),
                       str(f.get("name", "")) + " " + str(t.get("note", "")),
                       None, ["money", "fund"])
            if doc:
                docs.append(doc)
    return docs


# ---------------------------------------------------------------------------
# inverted index (TF-IDF) - built, persisted, refreshed on content change
# ---------------------------------------------------------------------------

def _signature(stores):
    parts = []
    for key in ("journal", "spiritual", "clients", "income", "sales"):
        v = stores.get(key)
        if isinstance(v, dict):
            parts.append(key + ":" + str(len(v)))
        elif isinstance(v, list):
            parts.append(key + ":" + str(len(v)))
        else:
            parts.append(key + ":0")
    vault = stores.get("vault") or {}
    parts.append("flow:" + str(len(vault.get("flow") or [])))
    parts.append("bills:" + str(len(vault.get("bills") or [])))
    return "|".join(parts)


def _build(stores):
    docs = _docs_from_stores(stores)
    n = len(docs)
    df = {}
    vectors = []
    for i, doc in enumerate(docs):
        toks = tokenize(doc["text"])
        tf = {}
        ln = max(1, len(toks))
        for t in toks:
            tf[t] = tf.get(t, 0.0) + 1.0
        for t in tf:
            tf[t] = tf[t] / ln
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
        vectors.append({"i": i, "tf": tf})
    idf = {}
    for t, d in df.items():
        idf[t] = math.log((n + 1.0) / (d + 1.0)) + 1.0
    return {
        "sig": _signature(stores), "docs": docs,
        "idf": idf, "vectors": vectors,
    }


def load_index():
    obj = _read_json(_IDX)
    if isinstance(obj, dict) and "docs" in obj and "vectors" in obj:
        return obj
    return None


def save_index(idx):
    _write_json(_IDX, idx)


def refresh_index(stores):
    sig = _signature(stores)
    idx = load_index()
    if idx is not None and idx.get("sig") == sig:
        return idx
    idx = _build(stores)
    save_index(idx)
    return idx


def _feedback_boost_for(doc, fb):
    if not fb:
        return 0.0
    score = 0.0
    tags = set(doc.get("tags") or [])
    src = doc.get("src", "")
    for rec in fb:
        kind = rec.get("kind", "")
        w = 1.0 if kind in ("like", "prefer") else -1.4
        rt = set(rec.get("rtags") or [])
        rsrc = rec.get("rsrc", "")
        if (tags & rt) or (rsrc and rsrc == src):
            score += w
    return score


def search(idx, query, k=4, allow_money=False, mood=None, fb=None):
    try:
        if not idx or not idx.get("vectors"):
            return []
        qtoks = tokenize(query)
        if not qtoks:
            return []
        idf = idx.get("idf") or {}
        docs = idx.get("docs") or []
        vectors = idx.get("vectors") or []
        mb = mood_band(mood)
        scored = []
        for vec in vectors:
            di = vec["i"]
            if di >= len(docs):
                continue
            doc = docs[di]
            if (not allow_money) and doc.get("src") in MONEY_SRCS:
                continue
            s = 0.0
            tf = vec["tf"]
            for t in qtoks:
                if t in tf:
                    s += tf[t] * idf.get(t, 1.0)
            if s <= 0:
                continue
            if mb and doc.get("mood") == mb:
                s *= 1.25
            dated = doc.get("date", "")
            if dated:
                try:
                    from datetime import date as _d
                    dd = _d.fromisoformat(dated[:10])
                    age = max(0, (_d.today() - dd).days)
                    s *= math.exp(-age / 90.0) + 0.15
                except Exception:
                    pass
            s += 0.25 * _feedback_boost_for(doc, fb)
            scored.append((s, di))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        out = []
        for s, di in scored[:max(1, int(k))]:
            d = dict(docs[di])
            d["score"] = round(s, 3)
            out.append(d)
        return out
    except Exception:
        return []


# ---------------------------------------------------------------------------
# feedback / training store
# ---------------------------------------------------------------------------

def load_feedback():
    obj = _read_json(_FB)
    if isinstance(obj, list):
        return obj
    return []


def save_feedback(fb):
    _write_json(_FB, fb)


def record_feedback(fb, rec):
    fb = list(fb or [])
    fb.insert(0, dict(rec))
    del fb[300:]
    save_feedback(fb)
    return fb


def _bucket_match(rec, mb, page):
    if mb and rec.get("mood_band") not in (mb, "any", "", None):
        return False
    if page and rec.get("page") not in (page, "any", "", None):
        return False
    return True


def is_suppressed(fb, mood_band_val, page, feature):
    if not fb or not feature:
        return False
    g_like = g_dis = 0
    b_like = b_dis = 0
    for rec in fb:
        feats = rec.get("features") or []
        if feature not in feats:
            continue
        kind = rec.get("kind", "")
        if kind in ("like", "prefer"):
            g_like += 1
        elif kind == "dislike":
            g_dis += 1
        if _bucket_match(rec, mood_band_val, page):
            if kind in ("like", "prefer"):
                b_like += 1
            elif kind == "dislike":
                b_dis += 1
    if b_dis >= b_like + 2 and b_dis >= 2:
        return True
    if g_dis >= g_like + 3 and g_dis >= 3:
        return True
    return False


def complaint_notes(fb, mood_band_val, page, limit=3):
    if not fb:
        return []
    out = []
    for rec in fb:
        if rec.get("kind") != "dislike":
            continue
        note = (rec.get("note") or "").strip()
        if not note:
            continue
        if _bucket_match(rec, mood_band_val, page):
            out.append(note)
        if len(out) >= limit:
            break
    return out


def feedback_summary(fb):
    n_like = sum(1 for r in fb if r.get("kind") in ("like", "prefer"))
    n_dis = sum(1 for r in fb if r.get("kind") == "dislike")
    return {"likes": n_like, "dislikes": n_dis, "total": len(fb or [])}


def learned_suppressions(fb, pages, moods=("low", "mid", "high", "none")):
    out = []
    for page in pages:
        for mb in moods:
            for feat in FEATURES:
                if is_suppressed(fb, mb, page, feat):
                    out.append({"page": page, "mood_band": mb,
                                "feature": feat})
    return out


def reset_feedback():
    save_feedback([])
    return []


# ---------------------------------------------------------------------------
# nightly reflection - longitudinal patterns, cached once per day
# ---------------------------------------------------------------------------

def _reflect_compute(stores):
    from datetime import date as _d, timedelta as _td
    today = _d.today()
    journal = stores.get("journal") or {}
    spirit = stores.get("spiritual") or {}
    clients = stores.get("clients") or []
    vault = stores.get("vault") or {}

    moods = []
    for o in range(6, -1, -1):
        e = journal.get((today - _td(days=o)).isoformat())
        if isinstance(e, dict) and e.get("mood"):
            moods.append(e["mood"])
    vals = []
    for m in moods:
        if m in MOOD_LOW:
            vals.append(0)
        elif m in MOOD_MID:
            vals.append(2)
        elif m in MOOD_HIGH:
            vals.append(4)
    slope = (vals[-1] - vals[0]) if len(vals) >= 2 else 0
    low_streak = 0
    for m in reversed(moods):
        if m in MOOD_LOW:
            low_streak += 1
        else:
            break

    lesson_tokens = {}
    lesson_bigrams = {}
    for o in range(29, -1, -1):
        e = journal.get((today - _td(days=o)).isoformat())
        if not isinstance(e, dict):
            continue
        les = e.get("lesson") or ""
        toks = tokenize(les)
        for t in toks:
            lesson_tokens[t] = lesson_tokens.get(t, 0) + 1
        for bg in _bigrams(toks):
            lesson_bigrams[bg] = lesson_bigrams.get(bg, 0) + 1
    recurring_lessons = sorted(lesson_bigrams.items(),
                               key=lambda kv: kv[1], reverse=True)[:3]
    recurring_lessons = [b for b, c in recurring_lessons if c >= 2]

    win_tokens = {}
    for o in range(13, -1, -1):
        e = journal.get((today - _td(days=o)).isoformat())
        if not isinstance(e, dict):
            continue
        for t in tokenize(e.get("win") or ""):
            win_tokens[t] = win_tokens.get(t, 0) + 1
    top_wins = [t for t, c in sorted(win_tokens.items(),
                                     key=lambda kv: kv[1],
                                     reverse=True)[:3]]

    act_energy = {}
    act_count = {}
    word_with_energy = 0
    word_total = 0
    for d, e in spirit.items():
        if not isinstance(e, dict):
            continue
        mins = float(e.get("minutes", 0) or 0)
        depth = int(e.get("depth", 0) or 0)
        acts = e.get("acts") or []
        felt = (e.get("felt") or "").strip()
        pres = 25.0 if (mins > 0 or felt or e.get("word") or acts) else 0.0
        en = int(max(0, min(100, round(
            pres + min(mins / 60.0, 1.0) * 25.0
            + (max(0, min(depth, 5)) / 5.0) * 25.0
            + min(len(acts) / 3.0, 1.0) * 15.0
            + min(len(felt) / 20.0, 1.0) * 10.0))))
        if e.get("word"):
            word_total += 1
            if en >= 70:
                word_with_energy += 1
        for a in acts:
            act_energy[a] = act_energy.get(a, 0) + en
            act_count[a] = act_count.get(a, 0) + 1
    energy_sources = []
    for a in act_energy:
        if act_count.get(a, 0) >= 1:
            energy_sources.append(
                (a, int(round(act_energy[a] / act_count[a]))))
    energy_sources.sort(key=lambda pair: pair[1], reverse=True)
    energy_sources = energy_sources[:3]
    word_lift = None
    if word_total >= 3:
        word_lift = int(round(100.0 * word_with_energy / word_total))

    term = set()
    from . import data as _D
    try:
        term = set(_D.terminal_ids())
    except Exception:
        term = set(("paid", "returned", "lost"))
    promised = 0
    kept = 0
    for c in clients:
        if not isinstance(c, dict):
            continue
        nd = c.get("next_date", "")
        if not nd or nd >= today.isoformat():
            continue
        if c.get("stage") in term:
            continue
        promised += 1
        for h in (c.get("history") or []):
            ts = (h.get("ts") or "")[:10]
            if ts and ts >= nd:
                kept += 1
                break
    promise_rate = int(round(100.0 * kept / promised)) if promised else None

    bills = vault.get("bills") or []
    on_time = 0
    total_b = 0
    for b in bills:
        if not isinstance(b, dict):
            continue
        due = b.get("due", "")
        if not due:
            continue
        total_b += 1
        if b.get("paid") and (b.get("paid_date") or "") <= due:
            on_time += 1
    bill_rate = int(round(100.0 * on_time / total_b)) if total_b else None

    return {
        "date": today.isoformat(),
        "mood_slope_7": slope,
        "low_streak": low_streak,
        "recurring_lessons": recurring_lessons,
        "top_wins": top_wins,
        "energy_sources": energy_sources,
        "word_lift": word_lift,
        "promise_rate": promise_rate,
        "bill_on_time_rate": bill_rate,
    }


def reflect(stores):
    try:
        from datetime import date as _d
        cached = _read_json(_REFL)
        if isinstance(cached, dict) and cached.get("date") == _d.today().isoformat():
            return cached
        r = _reflect_compute(stores)
        _write_json(_REFL, r)
        return r
    except Exception:
        return _read_json(_REFL) or {}


def top_pattern(refl, voice, mb):
    if not refl:
        return None
    if mb == "low":
        if refl.get("low_streak", 0) >= 2:
            return ("You've had " + str(refl["low_streak"])
                    + " heavy days in a row - that's a season, not a "
                    "verdict. Be gentle with the next hour.")
        if refl.get("recurring_lessons"):
            return ("A line you keep teaching yourself: '"
                    + str(refl["recurring_lessons"][0])
                    + "'. It's worth hearing again today.")
    if voice == "spirit":
        if refl.get("energy_sources"):
            a, e = refl["energy_sources"][0]
            return ("When you sit with Him, " + str(a)
                    + " is where your energy tends to land ("
                    + str(e) + "/100).")
        if refl.get("word_lift") is not None:
            return ("Days you catch a word, "
                    + str(refl["word_lift"])
                    + "% of the time your energy is high. The word works.")
    if voice in ("sales", "morning"):
        if refl.get("top_wins"):
            return ("Lately you keep winning at: "
                    + ", ".join(refl["top_wins"])
                    + ". That's your edge showing up.")
    if voice == "money":
        if refl.get("bill_on_time_rate") is not None:
            return ("Bills paid on time: "
                    + str(refl["bill_on_time_rate"])
                    + "% - that rate is the quiet engine of your runway.")
    if refl.get("promise_rate") is not None and voice in ("sales", "focus"):
        return ("You keep " + str(refl["promise_rate"])
                + "% of the calls you promise. The rest is just the next dial.")
    return None


# ---------------------------------------------------------------------------
# small public conveniences
# ---------------------------------------------------------------------------

def index_size(idx):
    try:
        return len((idx or {}).get("docs") or [])
    except Exception:
        return 0


def rebuild(stores):
    idx = _build(stores)
    save_index(idx)
    return idx
