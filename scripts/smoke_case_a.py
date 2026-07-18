#!/usr/bin/env python3
"""Smoke test: reconcile Case A end to end and print the result.

Confirms Case A produces an ESCALATE-with-question outcome — never a silent
close. Runs live if an API key is present; otherwise falls back to a cached
response if one exists. Exits non-zero if the outcome is not escalate+question.
"""

from __future__ import annotations

import pathlib
import sys

_SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_SRC))

from safety_net.client import has_api_key  # noqa: E402
from safety_net.models import ClosureState  # noqa: E402
from safety_net.sweep import (  # noqa: E402
    format_outcome,
    load_hero_cases,
    read_cache,
    run_hero_case,
)


def main() -> int:
    cases = {c.case_id: c for c in load_hero_cases()}
    if "case_a" not in cases:
        print("Case A not found in data/heroes/.", file=sys.stderr)
        return 2
    case = cases["case_a"]

    use_cache = not has_api_key()
    if use_cache and read_cache("case_a") is None:
        print(
            "No API key and no cached Case A response. Add ANTHROPIC_API_KEY to "
            ".env (Opus + Haiku access) and re-run, or populate data/cache/ first.",
            file=sys.stderr,
        )
        return 2

    mode = "cache" if use_cache else "live"
    print(f"Reconciling Case A ({mode})...\n")
    outcomes = run_hero_case(case, draft=True, use_cache=use_cache)

    if not outcomes:
        print("No recommendations were extracted from Case A.", file=sys.stderr)
        return 1

    for outcome in outcomes:
        print(format_outcome(outcome))
        print()

    # Assert the hero behavior: escalate + a specific question, never a silent close.
    primary = outcomes[0]
    result = primary.reconciliation
    ok = (
        result is not None
        and result.closure_state == ClosureState.ESCALATE
        and result.escalation.required
        and bool((result.escalation.question or "").strip())
    )
    if ok:
        print("SMOKE TEST PASSED: Case A escalated with a specific question "
              "(not a silent close).")
        return 0

    got = result.closure_state.value if result else "<none>"
    print(f"SMOKE TEST FAILED: expected closure_state=escalate with a question; "
          f"got closure_state={got}.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
