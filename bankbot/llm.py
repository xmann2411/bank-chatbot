"""Wrapper oko modela.

Dva moda:
  real       - ako je u .env postavljen ANTHROPIC_API_KEY, zove se pravi model
  simulirani - inače se odgovor složi pravilima i predlošcima (nlu.py, templates.py)

Svaki poziv ima i `simulate` funkciju. Ona se koristi u simuliranom modu,
ali i u pravom modu kad model ne odgovori (mreža, rate limit, odbijanje),
tako da bot uvijek nešto vrati.
"""

import json
import re
import sys

from . import audit
from .config import ANTHROPIC_API_KEY, MODEL

MODE = "real" if ANTHROPIC_API_KEY else "simulated"

# Modeli koji podržavaju server-side fallback kad sigurnosni filter odbije zahtjev.
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _call_real(system, messages, max_tokens):
    import anthropic

    kwargs = dict(model=MODEL, max_tokens=max_tokens, system=system, messages=messages)
    if not MODEL.startswith("claude-haiku"):
        # Chat ne treba duboko razmišljanje; niži effort = brži i jeftiniji odgovor.
        kwargs["output_config"] = {"effort": "low"}

    try:
        client = _get_client()
        if MODEL in _FALLBACK_MODELS:
            response = client.beta.messages.create(
                **kwargs, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
            )
        else:
            response = client.messages.create(**kwargs)
    except anthropic.APIError as e:
        print(f"   ! poziv modela nije uspio: {e}", file=sys.stderr)
        return None

    if response.stop_reason == "refusal":
        return None
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text or None


def ask(task, system, messages, simulate, max_tokens=16000):
    """Vraća tekst odgovora. `task` je samo oznaka za audit log."""
    text = None
    source = "simulated"
    if MODE == "real":
        text = _call_real(system, messages, max_tokens)
        source = "model" if text else "simulated_fallback"
    if text is None:
        text = simulate()
    audit.log("llm", task=task, source=source)
    return text


def parse_json(text):
    """Izvlači JSON objekt iz odgovora modela (i kad je u ```json blokovima)."""
    if isinstance(text, dict):
        return text
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def ask_json(task, system, messages, simulate, max_tokens=4000):
    """Kao ask(), ali očekuje JSON. Ako model vrati nešto neparsabilno, koristi simulate()."""
    result = None
    if MODE == "real":
        result = parse_json(_call_real(system, messages, max_tokens))
    source = "model" if result is not None else ("simulated_fallback" if MODE == "real" else "simulated")
    if result is None:
        result = simulate()
    audit.log("llm", task=task, source=source)
    return result
