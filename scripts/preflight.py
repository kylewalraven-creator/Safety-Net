#!/usr/bin/env python3
"""Preflight check for Safety Net.

Verifies the environment is ready before a build/demo:
  - SDKs import and report versions (anthropic, pydantic, fastmcp)
  - the frozen models round-trip the contract's own worked examples (offline)
  - the reconciliation prompt on disk is verbatim from the docs
  - an API key is present
  - the settled model IDs resolve with a tiny live ping (Opus + Haiku)

Offline checks always run. Live checks are SKIPPED (not failed) when no API key
is available. Exit code is non-zero only if a runnable check FAILS.
"""

from __future__ import annotations

import json
import pathlib
import sys

# Make src/ importable without an install.
_SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_SRC))

_PASS, _FAIL, _SKIP = "PASS", "FAIL", "SKIP"
_results: list[tuple[str, str, str]] = []


def record(name: str, status: str, detail: str = "") -> None:
    _results.append((name, status, detail))
    symbol = {"PASS": "✓", "FAIL": "✗", "SKIP": "–"}[status]
    print(f"  [{symbol}] {name}: {status}" + (f" — {detail}" if detail else ""))


def _version(pkg: str) -> str:
    try:
        from importlib.metadata import version

        return version(pkg)
    except Exception:  # noqa: BLE001
        return "unknown"


def check_imports() -> None:
    for pkg in ("anthropic", "pydantic", "fastmcp"):
        try:
            __import__(pkg)
            record(f"import {pkg}", _PASS, f"v{_version(pkg)}")
        except Exception as exc:  # noqa: BLE001
            record(f"import {pkg}", _FAIL, str(exc))


def check_models_roundtrip() -> None:
    """Validate the two worked-example reconciliation objects from the frozen
    prompt against the Pydantic models — proves models match the contract."""
    try:
        from safety_net.models import ReconciliationResult
        from safety_net.prompts import RECONCILIATION_SYSTEM
    except Exception as exc:  # noqa: BLE001
        record("models import", _FAIL, str(exc))
        return
    record("models import", _PASS)

    examples = [
        line.strip()
        for line in RECONCILIATION_SYSTEM.splitlines()
        if line.strip().startswith('{"recommendation_id"')
    ]
    if not examples:
        record("worked-example round-trip", _FAIL, "no examples found in prompt")
        return
    for i, blob in enumerate(examples, 1):
        try:
            result = ReconciliationResult.model_validate(json.loads(blob))
            record(
                f"worked-example {i} round-trip",
                _PASS,
                f"closure_state={result.closure_state.value}",
            )
        except Exception as exc:  # noqa: BLE001
            record(f"worked-example {i} round-trip", _FAIL, str(exc))


def check_prompt_verbatim() -> None:
    """Confirm the on-disk reconciliation prompt matches the fenced block in
    docs/reconciliation-prompt.md exactly."""
    try:
        from safety_net.prompts import RECONCILIATION_SYSTEM

        doc = (
            pathlib.Path(__file__).resolve().parents[1]
            / "docs"
            / "reconciliation-prompt.md"
        ).read_text(encoding="utf-8")
        start = doc.index("```text")
        content_start = doc.index("\n", start) + 1
        end = doc.index("```", content_start)
        expected = doc[content_start:end]
        if RECONCILIATION_SYSTEM == expected:
            record("reconciliation prompt verbatim", _PASS)
        else:
            record("reconciliation prompt verbatim", _FAIL, "on-disk prompt differs from docs")
    except Exception as exc:  # noqa: BLE001
        record("reconciliation prompt verbatim", _FAIL, str(exc))


def check_hero_data() -> None:
    try:
        from safety_net.sweep import load_hero_cases

        cases = load_hero_cases()
        record("hero cases load", _PASS, f"{len(cases)} case(s): "
               + ", ".join(c.case_id for c in cases))
    except Exception as exc:  # noqa: BLE001
        record("hero cases load", _FAIL, str(exc))


def check_key_and_pings() -> None:
    from safety_net.client import MODEL_HAIKU, MODEL_OPUS, has_api_key

    if not has_api_key():
        record("ANTHROPIC_API_KEY", _SKIP, "not set — live pings skipped")
        record(f"ping {MODEL_OPUS}", _SKIP, "no key")
        record(f"ping {MODEL_HAIKU}", _SKIP, "no key")
        return
    record("ANTHROPIC_API_KEY", _PASS, "present")

    from safety_net.client import call_haiku, call_opus

    for name, fn in ((MODEL_OPUS, call_opus), (MODEL_HAIKU, call_haiku)):
        try:
            out = fn("You are a preflight probe. Reply with exactly: OK",
                     "Reply with exactly: OK", max_tokens=16)
            ok = "OK" in out.upper()
            record(f"ping {name}", _PASS if ok else _FAIL, repr(out.strip()[:40]))
        except Exception as exc:  # noqa: BLE001
            record(f"ping {name}", _FAIL, str(exc))


def main() -> int:
    print("Safety Net preflight\n" + "=" * 40)
    check_imports()
    check_models_roundtrip()
    check_prompt_verbatim()
    check_hero_data()
    check_key_and_pings()

    failed = [r for r in _results if r[1] == _FAIL]
    skipped = [r for r in _results if r[1] == _SKIP]
    print("=" * 40)
    print(f"{len(_results)} checks — "
          f"{len(_results) - len(failed) - len(skipped)} pass, "
          f"{len(failed)} fail, {len(skipped)} skip")
    if skipped and not failed:
        print("Offline checks passed. Live checks were skipped (no API key).")
    if failed:
        print("FAILURES:")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
