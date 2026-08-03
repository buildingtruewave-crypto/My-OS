"""PULSE brain - offline, trainable, retrieval-augmented intelligence.
Pure standard library plus our own util (no Streamlit import), so no host or
version can break it, and every public function fails open. Privacy:
money-sourced documents are indexed but only retrievable when the caller
passes allow_money=True. Enforced at search time, not by trust.
"""
from __future__ import annotations

import hashlib
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
_SEM_DIM = 512
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


def _ngrams(text):
    toks = tokenize(text)
    out = list(toks)
    for i in range(len(toks) - 1):
        out.append(toks[i] + " " + toks[i + 1])
    return out


def _dim(t):
    h = hashlib.md5(t.encode("utf-8")).hexdigest()[:8]
    return int(h, 16) % _SEM_DIM


def _sem_vector(text):
    counts = {}
    for t in _ngrams(text):
        counts[t] = counts.get(t, 0) + 1
    vec = {}
    for t, w in counts.items():
        d = _dim(t)
        vec[d] = vec.get(d, 0.0) + float(w)
    norm = math.sqrt(sum(v * v for v in vec.values())) or 0.0
    if norm <= 0:
        return [], 0.0
    sparse = [[d, round(w, 4)] for d, w in vec.items()]
    return sparse, round(norm, 4)


def _sem_dot(qvec, qnorm, doc_sparse, doc_norm):
    if qnorm <= 0 or doc_norm <= 0 or not doc_sparse:
        return 0.0
    doc_map = {}
    for pair in doc_sparse:
        try:
            doc_map[int(pair[0])] = float(pair[1])
        except Exception:
            pass
    dot = 0.0
    for d, w in qvec:
        dv = doc_map.get(d)
        if dv:
            dot += w * dv
    if dot <= 0:
        return 0.0
    return dot / (qnorm * doc_norm)


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
# inverted index (TF-IDF) + semantic vectors
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
    vecs = []
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
        try:
            sparse, norm = _sem_vector(doc["text"])
        except Exception:
            sparse, norm = [], 0.0
        vecs.append({"v": sparse, "n": norm})
    idf = {}
    for t, d in df.items():
        idf[t] = math.log((n + 1.0) / (d + 1.0)) + 1.0
    return {
        "sig": _signature(stores), "docs": docs,
        "idf": idf, "vectors": vectors, "vecs": vecs,
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
    if idx is not None and idx.get("sig") == sig and "vecs" in idx:
        return idx
    idx = _build(stores)
    save_index(idx)
    return idx


def index_size(idx):
    try:
        return len((idx or {}).get("docs") or [])
    except Exception:
        return 0


def semantic_coverage(idx):
    try:
        vecs = (idx or {}).get("vecs") or []
        if not vecs:
            return 0.0
        have = sum(1 for v in vecs if v.get("n", 0) > 0)
        return round(100.0 * have / len(vecs), 1)
    except Exception:
        return 0.0


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


def taste_nudge_off(state, page, mb):
    return _taste_field(state, page, mb, "_nudge") == "off"


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


def taste_convergence(state):
    if not isinstance(state, dict):
        return 0.0
    t = state.get("taste") or {}
    vals = []
    for d in t.values():
        if not isinstance(d, dict):
            continue
        for k, v in d.items():
            if isinstance(k, str) and k.startswith("move:"):
                try:
                    vals.append(float(v))
                except Exception:
                    pass
    if len(vals) < 3:
        return 0.0
    mean = sum(vals) / len(vals)
    var = sum((x - mean) * (x - mean) for x in vals) / len(vals)
    sd = math.sqrt(var)
    c = 1.0 - (sd / 3.0)
    if c < 0:
        c = 0.0
    if c > 1:
        c = 1.0
    return round(100.0 * c, 1)


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
        elif c == "more playful / lighter":
            t["_style"] = ("light, playful, warm - a friend enjoying "
                           "the day with them, never a coach")
        elif c == "just flow - no reminders":
            t["_nudge"] = "off"
            t["move:pep_talk"] = _clamp(t.get("move:pep_talk", 0) - 2)
    note = (rec.get("note") or "").strip()
    if note:
        t["_note"] = note
    return record_feedback(fb, rec)


# ---------------------------------------------------------------------------
# feedback store (tune records only; no thumbs)
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
# search (lexical TF-IDF fused with semantic cosine + MMR diversity)
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


def _pairs_to_qvec(pairs):
    return [(int(p[0]), float(p[1])) for p in (pairs or [])]


def _mmr_pick(scored_with_vec, qvec, qnorm, vecs, k, lam=0.7):
    picked = []
    remaining = list(scored_with_vec)
    while remaining and len(picked) < k:
        best_i = -1
        best_val = -1e9
        for j, item in enumerate(remaining):
            s = item[0]
            di = item[1]
            div = 1.0
            for _, pdi, _ in picked:
                pv = vecs[pdi] if pdi < len(vecs) else {"v": [], "n": 0.0}
                cv = vecs[di] if di < len(vecs) else {"v": [], "n": 0.0}
                sim = _sem_dot(_pairs_to_qvec(pv.get("v", [])),
                               pv.get("n", 0.0), cv.get("v", []),
                               cv.get("n", 0.0))
                if sim > div:
                    div = sim
            val = lam * s + (1.0 - lam) * (1.0 - div)
            if val > best_val:
                best_val = val
                best_i = j
        if best_i < 0:
            break
        picked.append(remaining.pop(best_i))
    return picked


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
        vecs = idx.get("vecs") or []
        mb = mood_band(mood)
        try:
            wd_today = _U.today_local().weekday()
        except Exception:
            wd_today = None
        recent_refs = set((state or {}).get("recent_refs") or [])
        q_sparse, q_norm = _sem_vector(query)
        qvec = _pairs_to_qvec(q_sparse)
        lex_raw = {}
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
            lex_raw[di] = s
        lex_max = max(list(lex_raw.values()) + [1.0]) or 1.0
        scored = []
        for di, lex in lex_raw.items():
            if lex <= 0 and not vecs:
                continue
            doc = docs[di]
            lex_n = lex / lex_max if lex_max > 0 else 0.0
            cv = vecs[di] if di < len(vecs) else {"v": [], "n": 0.0}
            sem = _sem_dot(qvec, q_norm, cv.get("v", []),
                           cv.get("n", 0.0))
            if lex > 0 and sem > 0:
                combined = 0.6 * lex_n + 0.4 * sem
            elif lex > 0:
                combined = lex_n
            elif sem > 0:
                combined = sem
            else:
                continue
            if mb and doc.get("mood") == mb:
                combined *= 1.25
            dated = doc.get("date", "")
            doc_date = None
            if dated:
                try:
                    from datetime import date as _d
                    doc_date = _d.fromisoformat(dated[:10])
                    age = max(0, (_d.today() - doc_date).days)
                    combined *= math.exp(-age / 90.0) + 0.15
                except Exception:
                    doc_date = None
            if wd_today is not None and doc_date is not None:
                if doc_date.weekday() == wd_today:
                    combined *= 1.15
            combined += 0.25 * _feedback_boost_for(doc, fb)
            src = doc.get("src", "")
            move_guess = _SRC_MOVE.get(src)
            combined *= taste_score(state, page, mb, feat=move_guess,
                                    src=src)
            ref = src + "|" + dated
            if ref in recent_refs:
                combined *= 0.4
            scored.append((combined, di, cv))
        scored.sort(key=lambda item: item[0], reverse=True)
        picked = _mmr_pick(scored, qvec, q_norm, vecs, max(1, int(k)))
        out = []
        for combined, di, _cv in picked:
            d = dict(docs[di])
            d["score"] = round(combined, 3)
            out.append(d)
        return out
    except Exception:
        return []


# ---------------------------------------------------------------------------
# threads, nudges, self-note
# ---------------------------------------------------------------------------
def _threads_compute(stores, today):
    from datetime import timedelta as _td
    journal = stores.get("journal") or {}
    spirit = stores.get("spiritual") or {}
    occ = {}
    for o in range(13, -1, -1):
        d = (today - _td(days=o)).isoformat()
        e = journal.get(d)
        if isinstance(e, dict):
            text = " ".join(filter(None, [e.get("felt"), e.get("happened"),
                                          e.get("win"), e.get("lesson")]))
            for bg in _ngrams(text):
                occ.setdefault(bg, set()).add(d)
        se = spirit.get(d)
        if isinstance(se, dict):
            text = " ".join(filter(None, [se.get("felt"), se.get("word")]))
            for bg in _ngrams(text):
                occ.setdefault(bg, set()).add(d)
    threads = []
    for bg, dates in occ.items():
        if len(dates) >= 2:
            threads.append({"bigram": bg,
                            "dates": sorted(dates)})
    threads.sort(key=lambda t: len(t["dates"]), reverse=True)
    return threads[:6]


def thread_for(pkt, refl):
    if not refl:
        return None
    threads = refl.get("threads") or []
    if not threads:
        return None
    lj = pkt.get("last_journal") or {}
    hay = set(_ngrams(" ".join(filter(None, [
        lj.get("felt"), lj.get("happened"), pkt.get("mood_today")]))))
    pick = None
    for t in threads:
        if t["bigram"] in hay:
            pick = t
            break
    if pick is None:
        pick = threads[0]
    dates = pick.get("dates") or []
    shown = ", ".join(dates[-3:])
    return ("You've felt '" + str(pick["bigram"]) + "' before - on "
            + shown + ". You are not starting from zero.")


def next_move(pkt):
    out = []
    pb = pkt.get("pantry_bottleneck")
    if pb and pb.get("days", 99) <= 3:
        out.append("Pantry: " + str(pb.get("name", "a staple"))
                   + " is at " + str(pb.get("days", 0))
                   + " days - put it on today's shop list.")
    if pkt.get("bills_overdue_n", 0) > 0:
        out.append("Clear the oldest overdue bill before any fun top-up.")
    cdue = pkt.get("clients_due_n", 0)
    if cdue > 0 and pkt.get("mood_band") == "low":
        out.append(str(cdue) + " follow-up waits - open with the hottest, one call.")
    elif cdue > 0:
        out.append(str(cdue) + " follow-up waits today - that is revenue in your phone.")
    if not pkt.get("spirit_today_has") and pkt.get("hour", 12) < 12:
        out.append("Five silent minutes before the phone wakes up.")
    if pkt.get("commissions_due", 0) > 0:
        out.append("Chase the " + str(pkt.get("commissions_due", 0))
                   + " commission(s) due today.")
    return out[:2]


def self_note(refl):
    if not refl:
        return None
    parts = []
    rl = refl.get("recurring_lessons") or []
    if rl:
        parts.append("Over the last month you keep returning to '"
                     + str(rl[0]) + "'.")
    es = refl.get("energy_sources") or []
    if es:
        parts.append("Your energy tends to spike when you "
                     + str(es[0][0]) + ".")
    slope = refl.get("mood_slope_7", 0) or 0
    if slope > 0:
        parts.append("This week your mood has been lifting - notice what you did differently.")
    elif slope < 0:
        parts.append("This week has been heavy; that is a season, not a verdict.")
    if not parts:
        return None
    return " ".join(parts[:3])


def memory_health(idx, state, fb, refl):
    summ = feedback_summary(fb)
    return {
        "memories": index_size(idx),
        "semantic_pct": semantic_coverage(idx),
        "threads": len((refl or {}).get("threads") or []),
        "taste_convergence_pct": taste_convergence(state),
        "tunes": summ.get("tunes", 0),
    }


# ---------------------------------------------------------------------------
# nightly reflection (cached once per day)
# ---------------------------------------------------------------------------
def _bigrams_only(tokens):
    out = []
    for i in range(len(tokens) - 1):
        out.append(tokens[i] + " " + tokens[i + 1])
    return out


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
        for bg in _bigrams_only(toks):
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
        if c.get("stage") in term or c.get("ended"):
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
    threads = _threads_compute(stores, today)
    note = self_note({"recurring_lessons": recurring_lessons,
                      "energy_sources": energy_sources,
                      "mood_slope_7": slope})
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
        "threads": threads,
        "self_note": note,
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
