"""Free-tier, multi-provider LLM router with automatic failover.

Replaces the single DigitalOcean managed-agent pipe with a resilient fan-out
across OpenAI-compatible free tiers: Groq, Gemini, OpenRouter, Cerebras,
GitHub Models, and plain OpenAI. Each provider carries its own model list, a
circuit breaker with cooldown, and latency tracking; the router is sticky on
success and walks the chain on failure. Three transports are tried under each
provider (openai SDK -> httpx -> stdlib urllib), so it functions even with no
extra packages installed. If every provider is down or unconfigured, callers
get (None, None) and the companion falls back to its offline voice.

Configuration is read from st.secrets["llm"] (see README / secrets template).
Module-level health state persists across Streamlit reruns because imported
modules are cached in sys.modules.
"""
from __future__ import annotations

import json
import time

# Default OpenAI-compatible base URLs per provider.
_BASES = {
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "openrouter": "https://openrouter.ai/api/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "github": "https://models.inference.ai.azure.com",
    "openai": "https://api.openai.com/v1",
}
_DEFAULT_MODELS = {
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
    "gemini": ["gemini-2.0-flash", "gemini-1.5-flash-latest"],
    "openrouter": [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "deepseek/deepseek-chat:free",
    ],
    "cerebras": ["llama-3.3-70b", "llama3.1-8b"],
    "github": ["gpt-4o-mini", "meta-llama-3.3-70b-instruct",
               "meta-llama-3.1-8b-instant"],
    "openai": ["gpt-4o-mini"],
}
_PRIORITY = ["groq", "gemini", "openrouter", "cerebras", "github", "openai"]
_COOLDOWN = 90.0
_FAIL_LIMIT = 3

# provider -> {"fails": int, "cool": float, "last_ms": int, "model": str}
_HEALTH = {}


def _secrets_llm():
    try:
        import streamlit as st
        s = st.secrets["llm"]
        return s
    except Exception:
        return None


def _get(s, key, default=None):
    try:
        v = s[key]
        if v is None:
            return default
        return v
    except Exception:
        return default


def _provider_specs():
    """Return ordered list of provider dicts that have a key configured."""
    s = _secrets_llm()
    if s is None:
        return []
    default = str(_get(s, "default_provider", "") or "").strip().lower()
    order = list(_PRIORITY)
    if default in order:
        order.remove(default)
        order.insert(0, default)
    elif default:
        order.insert(0, default)
    specs = []
    for name in order:
        key = str(_get(s, name + "_key", "") or "").strip()
        if not key:
            continue
        base = str(_get(s, name + "_base", "") or _BASES.get(name, "")).strip()
        models = _get(s, name + "_models", None)
        if isinstance(models, str):
            models = [models]
        if not models:
            models = list(_DEFAULT_MODELS.get(name, []))
        models = [str(m).strip() for m in models if str(m).strip()]
        if not models:
            continue
        specs.append({"name": name, "key": key, "base": base,
                      "models": models})
    return specs


def has_providers():
    try:
        return len(_provider_specs()) > 0
    except Exception:
        return False


def _is_cooled(name):
    h = _HEALTH.get(name)
    if not h:
        return False
    return (h.get("cool", 0.0) > time.time())


def _mark_fail(name):
    h = _HEALTH.setdefault(name, {"fails": 0, "cool": 0.0,
                                  "last_ms": 0, "model": ""})
    h["fails"] = int(h.get("fails", 0)) + 1
    if h["fails"] >= _FAIL_LIMIT:
        h["cool"] = time.time() + _COOLDOWN


def _mark_ok(name, model, ms):
    _HEALTH[name] = {"fails": 0, "cool": 0.0, "last_ms": int(ms),
                     "model": model}


def health_summary():
    out = {}
    for name, h in _HEALTH.items():
        out[name] = {"last_ms": int(h.get("last_ms", 0)),
                     "model": str(h.get("model", "")),
                     "cooled": bool(h.get("cool", 0.0) > time.time())}
    return out


# ---- transports: each returns the assistant text or None ----

def _extract(data):
    try:
        choices = data.get("choices") or []
        if choices:
            msg = choices[0].get("message") or {}
            content = msg.get("content")
            if content:
                return str(content).strip()
    except Exception:
        pass
    return None


def _call_openai(base, key, model, messages, temperature, max_tokens):
    try:
        import openai
    except Exception:
        return None
    try:
        kw = {"api_key": key}
        if base:
            kw["base_url"] = base
        client = openai.OpenAI(**kw)
        r = client.chat.completions.create(
            model=model, messages=messages,
            temperature=temperature, max_tokens=max_tokens)
        return _extract({"choices": [{"message": {"content":
                   r.choices[0].message.content}}]})
    except Exception:
        return None


def _call_httpx(base, key, model, messages, temperature, max_tokens):
    try:
        import httpx
    except Exception:
        return None
    url = base.rstrip("/") + "/chat/completions"
    headers = {"Authorization": "Bearer " + key,
               "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    try:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, headers=headers,
                               content=json.dumps(payload))
            if resp.status_code >= 400:
                return None
            return _extract(resp.json())
    except Exception:
        return None


def _call_urllib(base, key, model, messages, temperature, max_tokens):
    url = base.rstrip("/") + "/chat/completions"
    headers = {"Authorization": "Bearer " + key,
               "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    try:
        from urllib import request as _req
        req = _req.Request(url, data=json.dumps(payload).encode("utf-8"),
                           headers=headers, method="POST")
        with _req.urlopen(req, timeout=45.0) as resp:
            raw = resp.read().decode("utf-8")
        return _extract(json.loads(raw))
    except Exception:
        return None


def _attempt(spec, model, messages, temperature, max_tokens):
    base = spec["base"]
    key = spec["key"]
    t0 = time.time()
    text = _call_openai(base, key, model, messages, temperature, max_tokens)
    if text is None:
        text = _call_httpx(base, key, model, messages, temperature, max_tokens)
    if text is None:
        text = _call_urllib(base, key, model, messages, temperature, max_tokens)
    ms = (time.time() - t0) * 1000.0
    if text:
        return text, int(ms)
    return None, int(ms)


def chat(messages, temperature=0.7, max_tokens=240, prefer=None):
    """Try providers in order; return (text, "provider/model") or (None, None)."""
    specs = _provider_specs()
    if not specs:
        return None, None
    ordered = list(specs)
    if prefer:
        ordered = [s for s in ordered if s["name"] == prefer] \
            + [s for s in ordered if s["name"] != prefer]
    for spec in ordered:
        name = spec["name"]
        if _is_cooled(name):
            continue
        for model in spec["models"]:
            text, ms = _attempt(spec, model, messages, temperature, max_tokens)
            if text:
                _mark_ok(name, model, ms)
                return text, name + "/" + model
            _mark_fail(name)
            if _is_cooled(name):
                break
    return None, None
