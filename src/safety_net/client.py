"""Anthropic client setup and small Opus/Haiku call helpers.

The API key is read from the environment (``ANTHROPIC_API_KEY``), loaded from a
gitignored ``.env`` if present. Model IDs are settled and hard-coded — do not
substitute them.
"""

from __future__ import annotations

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()  # populate os.environ from a local .env, if one exists

# Settled model IDs — do not substitute.
MODEL_OPUS = "claude-opus-4-8"  # reconciliation + action-drafting
MODEL_HAIKU = "claude-haiku-4-5-20251001"  # bulk extraction

# Opus 4.8 rejects `temperature` (deprecated for this model → HTTP 400). It is
# omitted for these models even if a caller passes one, so the bug can't regress.
_NO_TEMPERATURE_MODELS = {MODEL_OPUS}

_client: anthropic.Anthropic | None = None


class MissingAPIKeyError(RuntimeError):
    """Raised when no Anthropic API key is available in the environment."""


def get_client() -> anthropic.Anthropic:
    """Return a cached Anthropic client, constructing it on first use."""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise MissingAPIKeyError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add a "
                "key with access to both Opus and Haiku."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def has_api_key() -> bool:
    """True if an API key is available (does not construct a client)."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _request_params(
    model: str, system: str, user: str, max_tokens: int, temperature: float | None
) -> dict:
    """Build messages.create kwargs, omitting `temperature` for models that
    reject it (Opus 4.8) or when it is None."""
    params: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    if temperature is not None and model not in _NO_TEMPERATURE_MODELS:
        params["temperature"] = temperature
    return params


def call_model(
    model: str,
    system: str,
    user: str,
    *,
    max_tokens: int = 2048,
    temperature: float | None = None,
) -> str:
    """Single-turn call; returns concatenated text output."""
    resp = get_client().messages.create(
        **_request_params(model, system, user, max_tokens, temperature)
    )
    return "".join(
        block.text for block in resp.content if getattr(block, "type", None) == "text"
    )


def call_opus(system: str, user: str, *, max_tokens: int = 4096) -> str:
    # Opus 4.8 does not accept `temperature`; rely on the model default.
    return call_model(MODEL_OPUS, system, user, max_tokens=max_tokens)


def call_haiku(
    system: str, user: str, *, max_tokens: int = 1536, temperature: float | None = 0.0
) -> str:
    return call_model(MODEL_HAIKU, system, user, max_tokens=max_tokens, temperature=temperature)


# ---------------------------------------------------------------------------
# Defensive JSON handling. The prompts demand raw JSON, but a model may wrap
# output in fences or add prose; strip defensively and retry once on failure.
# ---------------------------------------------------------------------------


def extract_json_block(text: str) -> str:
    """Return the first balanced ``{...}`` object in *text*, ignoring fences and
    surrounding prose. String contents are respected so braces inside quotes do
    not miscount."""
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model output.")
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("Unbalanced JSON object in model output.")


def call_json(
    model: str,
    system: str,
    user: str,
    *,
    max_tokens: int = 4096,
    temperature: float | None = None,
    retries: int = 1,
) -> dict:
    """Call the model and parse a single JSON object, retrying once with a
    corrective nudge if the first response does not parse."""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        this_user = user
        this_temp = temperature
        if attempt > 0:
            this_user = (
                user
                + "\n\nReturn ONLY the JSON object — no code fences, no commentary."
            )
            if this_temp is not None:
                this_temp = max(this_temp, 0.2)
        raw = call_model(model, system, this_user, max_tokens=max_tokens, temperature=this_temp)
        try:
            return json.loads(extract_json_block(raw))
        except (ValueError, json.JSONDecodeError) as e:  # noqa: PERF203
            last_err = e
    raise ValueError(
        f"Model did not return parseable JSON after {retries + 1} attempt(s): {last_err}"
    )
