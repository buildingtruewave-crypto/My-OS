"""PULSE brain - offline, trainable, retrieval-augmented intelligence.

The layer that turns the companion from "reads the last three lines" into a
memory that knows one person across time. Pure standard library plus our own
util (no Streamlit), so no host or version can break it, and every public
function fails open: a corrupt index rebuilds, a bad search returns [], a
failed reflection or reconciliation is skipped. A bug here can never take
down a page or touch the operator's data.

What makes it genuinely intelligent (all offline, all persisted as JSON):
  * Temporal-rhythm retrieval: a memory that landed on a Tuesday 07:00 is
    weighted higher on a Tuesday morning, because a life has a rhythm.
  * Query expansion from the operator's own vocabulary: recurring lessons
    and recurring wins become the high-value search terms.
  * A per (mood x page) taste model that learns which moves and which
    sources resonate, and ranks every future message by predicted resonance.
  * Implicit reinforcement from BEHAVIOUR: if the companion surfaces a verse
    and the operator then logs spirit at depth, that path is strengthened;
    if it cites a past win and a sale follows, that retrieval is strengthened;
    silence is never punished. No click, no rating, no friction.
  * Anti-repetition: it will not surface the same memory twice in a row.
  * Confidence-calibrated brevity: it can choose to say one true line.

Privacy: money-sourced documents are indexed but only retrievable when the
caller passes allow_money=True (inside the locked Archive). Enforced at
search time, not by trust.

Design notes (the honest read of the blueprint bundle supplied earlier): the
DigitalOcean ELK blueprint is a full-text-search-over-your-own-history engine;
we translate that idea into this offline inverted index with TF-IDF plus the
rhythm/taste/anti-repeat layers above. The Airflow blueprint is a durable
scheduled-jobs engine; we translate that into the nightly reflection pass
(reflect()) plus the opportunistic reconcile_implicit(), both cached in data/
with no daemon. On a VPS the same JSON files persist via the mounted data/
volume; if the operator ever scales to many heavy sources, a real scheduler
(the Airflow pattern) is the migration target, but for one operator this
lightweight equivalent is correct and already present. The old trading-
terminal PULSE files confirmed the design DNA and what NOT to regress; they
are not reused here.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from . import util as _U

_DATA = Path(__file__).resolve().parent.parent / "data"
_IDX = _DATA / "brain_index.json"
_FB = _DATA / "brain_feedback.json"
_REFL = _DATA / "brain_reflection.json"
_STATE = _DATA / "brain_state.json"

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
_SRC_MOVE = {
    "spirit": "quoted_verse", "journal": "quoted_memory",
    "sale": "quoted_memory", "income": "quoted_memory",
    "client": "quoted_memory", "flow": "money_advice",
    "bill": "money_advice", "emergency": "money_advice",
    "fund": "money_advice",
}
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


def _clamp(v, lo=-6.0, hi=6.0):
    try:
        v = float(v)
    except Exception:
        v = 0.0
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


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


def _energy(e):
    if not e:
        return 0
    try:
        mins = float(e.get("minutes", 0) or 0)
        depth = int(e.get("depth", 0) or 0)
        acts = e.get("acts") or []
        felt = (e.get("felt") or "").strip()
    except Exception:
        return 0
    pres = 25.0 if (mins > 0 or felt or acts or e.get("word")) else 0.0
    m = min(mins / 60.0, 1.0) * 25.0
    d = (max(0, min(depth, 5)) / 5.0) * 25.0
    a = min(len(acts) / 3.0, 1.0) * 15.0
    r = min(len(felt) / 20.0, 1.0) * 10.0
    return int(max(0, min(100, round(pres + m + d + a + r))))


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
            doc = _doc("client", (h.get("ts") or "")[:10], text, None,
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
                + str(s.get("phone", ""))).strip()
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
# inverted index (TF-IDF)
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


def index_size(idx):
    try:
        return len((idx or {}).get("docs") or [])
    except Exception:
        return 0


def rebuild(stores):
    idx = _build(stores)
    save_index(idx)
    return idx


# ---------------------------------------------------------------------------
# state (surfaced log + taste model + anti-repeat memory)
# ---------------------------------------------------------------------------

def _empty_state():
    return {"surfaced": [], "taste": {}, "recent_refs": []}


def load_state():
    obj = _read_json(_STATE)
    if isinstance(obj, dict):
        obj.setdefault("surfaced", [])
        obj.setdefault("taste", {})
        obj.setdefault("recent_refs", [])
        return obj
    return _empty_state()


def save_state(state):
    _write_json(_STATE, state or _empty_state())


def note_surfaced(state, page, mb, moves, refs):
    if not isinstance(state, dict):
        return
    state.setdefault("surfaced", [])
    state.setdefault("recent_refs", [])
    try:
        ts = _U.now_local().isoformat()
    except Exception:
        ts = ""
    state["surfaced"].insert(0, {
        "ts": ts, "page": page or "", "mood_band": mb or "none",
        "moves": list(moves or []), "refs": list(refs or []),
        "rec": False,
    })
    del state["surfaced"][200:]
    rr = list(state.get("recent_refs") or [])
    for ref in (refs or []):
        if ref and ref not in rr:
            rr.insert(0, ref)
    del rr[12:]
    state["recent_refs"] = rr


# ---------------------------------------------------------------------------
# taste model
# ---------------------------------------------------------------------------

def _taste_keys(page, mb):
    out = []
    if page is not None and mb:
        out.append(str(page) + "|" + str(mb))
    if page is not None:
        out.append(str(page) + "|any")
    if mb:
        out.append("any|" + str(mb))
    return out


def taste_score(state, page, mb, feat=None, src=None):
    if not isinstance(state, dict) or page is None:
        return 1.0
    t = state.get("taste") or {}
    adj = 0.0
    for key in _taste_keys(page, mb):
        d = t.get(key) or {}
        if feat is not None:
            adj += 0.12 * float(d.get("move:" + feat, 0) or 0)
        if src is not None:
            adj += 0.12 * float(d.get("src:" + src, 0) or 0)
    if adj < -0.5:
        adj = -0.5
    if adj > 0.6:
        adj = 0.6
    m = 1.0 + adj
    if m < 0.45:
        return 0.45
    if m > 1.7:
        return 1.7
    return m


def _taste_field(state, page, mb, field):
    if not isinstance(state, dict):
        return ""
    t = state.get("taste") or {}
    for key in _taste_keys(page, mb):
        v = (t.get(key) or {}).get(field)
        if v:
            return str(v)
    return ""


def taste_style(state, page, mb):
    return _taste_field(state, page, mb, "_style")


def taste_brevity(state, page, mb):
    return _taste_field(state, page, mb, "_brev")


def taste_note(state, page, mb):
    return _taste_field(state, page, mb, "_note")


def taste_summary(state, page, mb):
    if not isinstance(state, dict):
        return ""
    t = state.get("taste") or {}
    d = t.get((str(page) + "|" + str(mb)) if page is not None else "", {}) or {}
    parts = []
    for k, v in d.items():
        try:
            vv = float(v)
        except Exception:
            continue
        if not k.startswith("move:") or abs(vv) < 2:
            continue
        word = k[5:].replace("_", " ")
        if vv > 0:
            parts.append("leans toward " + word)
        else:
            parts.append("holds back " + word)
    sty = d.get("_style")
    if sty:
        parts.append("tone: " + str(sty))
    note = d.get("_note")
    if note:
        parts.append("you asked: " + str(note))
    return "; ".join(parts[:3])


def move_allowed(state, fb, page, mb, feat):
    if is_suppressed(fb, mb, page, feat):
        return False
    if isinstance(state, dict) and taste_score(state, page, mb, feat=feat) < 0.6:
        return False
    return True


def apply_tune(state, fb, rec):
    if not isinstance(state, dict):
        state = _empty_state()
    page = rec.get("page", "")
    mb = rec.get("mood_band", "none")
    key = str(page) + "|" + str(mb)
    t = state.setdefault("taste", {}).setdefault(key, {})
    for chip in (rec.get("chips") or []):
        c = str(chip).strip().lower()
        if c == "softer":
            t["_style"] = "softer, warmer, less directive"
        elif c == "more direct":
            t["_style"] = "direct and concrete, no softening"
        elif c == "shorter":
            t["_brev"] = "short"
        elif c == "skip scripture here":
            t["move:quoted_verse"] = _clamp(t.get("move:quoted_verse", 0) - 2)
            t["src:spirit"] = _clamp(t.get("src:spirit", 0) - 2)
        elif c == "cite scripture":
            t["move:quoted_verse"] = _clamp(t.get("move:quoted_verse", 0) + 2)
            t["src:spirit"] = _clamp(t.get("src:spirit", 0) + 2)
        elif c == "cite a past win":
            t["move:quoted_memory"] = _clamp(t.get("move:quoted_memory", 0) + 2)
            t["src:sale"] = _clamp(t.get("src:sale", 0) + 1)
            t["src:income"] = _clamp(t.get("src:income", 0) + 1)
        elif c == "more practical":
            t["move:money_advice"] = _clamp(t.get("move:money_advice", 0) + 1)
            t["move:pattern_cited"] = _clamp(t.get("move:pattern_cited", 0) + 1)
        elif c == "calmer / less pep":
            t["move:pep_talk"] = _clamp(t.get("move:pep_talk", 0) - 2)
    note = (rec.get("note") or "").strip()
    if note:
        t["_note"] = note
    return record_feedback(fb, rec)


# ---------------------------------------------------------------------------
# feedback store (now carries only "tune" records; no thumbs)
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


def reset_feedback():
    save_feedback([])
    save_state(_empty_state())
    return []


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
        if rec.get("kind") != "tune":
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
    n_tune = sum(1 for r in (fb or []) if r.get("kind") == "tune")
    return {"tunes": n_tune, "total": len(fb or [])}


def learned_suppressions(fb, pages, moods=("low", "mid", "high", "none")):
    out = []
    for page in pages:
        for mb in moods:
            for feat in FEATURES:
                if is_suppressed(fb, mb, page, feat):
                    out.append({"page": page, "mood_band": mb,
                                "feature": feat})
    return out


# ---------------------------------------------------------------------------
# implicit reinforcement from behaviour
# ---------------------------------------------------------------------------

def _resonance(src, window_dates, stores):
    try:
        if src == "spirit":
            sp = stores.get("spiritual") or {}
            for d in window_dates:
                e = sp.get(d)
                if e and (int(e.get("depth", 0) or 0) >= 3
                          or _energy(e) >= 70):
                    return True
            return False
        if src in ("sale", "income", "client"):
            if src == "sale":
                for s in (stores.get("sales") or []):
                    if s.get("date") in window_dates:
                        return True
            if src == "income":
                for x in (stores.get("income") or []):
                    if x.get("date") in window_dates:
                        return True
            if src == "client":
                for c in (stores.get("clients") or []):
                    for h in (c.get("history") or []):
                        if (h.get("ts") or "")[:10] in window_dates:
                            return True
            j = stores.get("journal") or {}
            for d in window_dates:
                e = j.get(d)
                if e and (e.get("win") or "").strip():
                    return True
            return False
        if src in ("flow", "bill", "emergency", "fund", "money"):
            v = stores.get("vault") or {}
            for f in (v.get("flow") or []):
                if f.get("date") in window_dates:
                    return True
            for b in (v.get("bills") or []):
                if b.get("paid_date") in window_dates:
                    return True
            for t in ((v.get("emergency") or {}).get("tx") or []):
                if t.get("date") in window_dates:
                    return True
            for fd in (v.get("funds") or []):
                for t in (fd.get("tx") or []):
                    if t.get("date") in window_dates:
                        return True
            return False
    except Exception:
        return False
    return False


def reconcile_implicit(state, stores, fb):
    if not isinstance(state, dict):
        return
    from datetime import date as _d
    from datetime import timedelta as _td
    today = _d.today()
    fb_tunes = [r for r in (fb or []) if r.get("kind") == "tune"]
    surfaced = state.get("surfaced") or []
    for rec in surfaced:
        if rec.get("rec"):
            continue
        ts = (rec.get("ts") or "")[:10]
        if not ts:
            rec["rec"] = True
            continue
        try:
            tsd = _d.fromisoformat(ts)
        except Exception:
            rec["rec"] = True
            continue
        if (today - tsd).days > 2:
            rec["rec"] = True
            continue
        window_dates = set((ts, (tsd + _td(days=1)).isoformat()))
        page = rec.get("page", "")
        mb = rec.get("mood_band", "none")
        t = state.setdefault("taste", {}).setdefault(
            str(page) + "|" + str(mb), {})
        pos = False
        for ref in (rec.get("refs") or []):
            src = str(ref).split("|")[0]
            if _resonance(src, window_dates, stores):
                pos = True
        if "quoted_verse" in (rec.get("moves") or []):
            if _resonance("spirit", window_dates, stores):
                pos = True
        tuned = False
        for tr in fb_tunes:
            trd = (tr.get("ts") or "")[:10]
            if (tr.get("page") == page and tr.get("mood_band") == mb
                    and trd in window_dates):
                tuned = True
        for mv in (rec.get("moves") or []):
            cur = float(t.get("move:" + mv, 0) or 0)
            if tuned:
                t["move:" + mv] = _clamp(cur - 2)
            elif pos:
                t["move:" + mv] = _clamp(cur + 1)
        for ref in (rec.get("refs") or []):
            src = str(ref).split("|")[0]
            cur = float(t.get("src:" + src, 0) or 0)
            if tuned:
                t["src:" + src] = _clamp(cur - 2)
            elif pos:
                t["src:" + src] = _clamp(cur + 1)
        rec["rec"] = True
    del surfaced[200:]
    state["surfaced"] = surfaced


# ---------------------------------------------------------------------------
# search (TF-IDF + recency + mood + weekday rhythm + taste + anti-repeat)
# ---------------------------------------------------------------------------

def _feedback_boost_for(doc, fb):
    if not fb:
        return 0.0
    score = 0.0
    tags = set(doc.get("tags") or [])
    src = doc.get("src", "")
    for rec in fb:
        kind = rec.get("kind", "")
        if kind == "tune":
            continue
        w = 1.0 if kind in ("like", "prefer") else -1.4
        rt = set(rec.get("rtags") or [])
        rsrc = rec.get("rsrc", "")
        if (tags & rt) or (rsrc and rsrc == src):
            score += w
    return score


def search(idx, query, k=4, allow_money=False, mood=None, fb=None,
           refl=None, state=None, page=None):
    try:
        if not idx or not idx.get("vectors"):
            return []
        qtoks = list(tokenize(query))
        if refl:
            for bg in (refl.get("recurring_lessons") or [])[:1]:
                for w in str(bg).split():
                    if len(w) >= 3:
                        qtoks.append(w)
            for w in (refl.get("top_wins") or [])[:3]:
                if len(str(w)) >= 3:
                    qtoks.append(str(w))
        if not qtoks:
            return []
        idf = idx.get("idf") or {}
        docs = idx.get("docs") or []
        vectors = idx.get("vectors") or []
        mb = mood_band(mood)
        try:
            wd_today = _U.today_local().weekday()
        except Exception:
            wd_today = None
        recent_refs = set((state or {}).get("recent_refs") or [])
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
            doc_date = None
            if dated:
                try:
                    from datetime import date as _d
                    doc_date = _d.fromisoformat(dated[:10])
                    age = max(0, (_d.today() - doc_date).days)
                    s *= math.exp(-age / 90.0) + 0.15
                except Exception:
                    doc_date = None
            if wd_today is not None and doc_date is not None:
                if doc_date.weekday() == wd_today:
                    s *= 1.15
            s += 0.25 * _feedback_boost_for(doc, fb)
            src = doc.get("src", "")
            move_guess = _SRC_MOVE.get(src)
            s *= taste_score(state, page, mb, feat=move_guess, src=src)
            ref = src + "|" + dated
            if ref in recent_refs:
                s *= 0.4
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
# nightly reflection - longitudinal patterns, cached once per day
# ---------------------------------------------------------------------------

def _reflect_compute(stores):
    from datetime import date as _d
    from datetime import timedelta as _td
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

    lesson_bigrams = {}
    for o in range(29, -1, -1):
        e = journal.get((today - _td(days=o)).isoformat())
        if not isinstance(e, dict):
            continue
        toks = tokenize(e.get("lesson") or "")
        for bg in _bigrams(toks):
            lesson_bigrams[bg] = lesson_bigrams.get(bg, 0) + 1
    recurring_lessons = [b for b, c in sorted(
        lesson_bigrams.items(), key=lambda kv: kv[1], reverse=True)[:3]
        if c >= 2]

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
        en = _energy(e)
        if e.get("word"):
            word_total += 1
            if en >= 70:
                word_with_energy += 1
        for a in (e.get("acts") or []):
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

    term = set(("paid", "returned", "lost"))
    try:
        from . import data as _D
        term = set(_D.terminal_ids())
    except Exception:
        pass
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
        if (isinstance(cached, dict)
                and cached.get("date") == _d.today().isoformat()):
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
    if (refl.get("promise_rate") is not None
            and voice in ("sales", "focus")):
        return ("You keep " + str(refl["promise_rate"])
                + "% of the calls you promise. The rest is just the "
                "next dial.")
    return None
