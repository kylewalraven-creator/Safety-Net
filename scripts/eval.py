#!/usr/bin/env python3
"""Safety Net eval harness — measured correctness, not vibes.

Scores the reconciliation engine against the hand-authored ground truth on each
hero case (`expected_closure_state` / `expected_escalation`) and runs an
automated **verbatim-citation validator**: every quote the model cites must be an
exact substring of the source report it points to, or it counts as a
hallucination. Runs **offline from `data/cache/`** by default (no key needed), so
the numbers are reproducible on stage; pass ``--live`` to reconcile with the API.

Exit code is non-zero if any gate fails, so this doubles as a CI/pre-demo gate.

    python scripts/eval.py            # offline, from cache
    python scripts/eval.py --live     # reconcile live (needs ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import argparse
import re
import sys

from safety_net.client import has_api_key
from safety_net.models import ClosureState, HeroCase, RecommendationOutcome
from safety_net.sweep import load_hero_cases, run_hero_case

# Closure states that mean "we surfaced this to a human" (a positive).
SURFACED_STATES = {ClosureState.ESCALATE, ClosureState.OPEN_OVERDUE}

# Smart-quote / dash folding so a "verbatim" quote isn't failed by typography.
_FOLD = {ord("’"): "'", ord("‘"): "'", ord("“"): '"', ord("”"): '"', ord("–"): "-", ord("—"): "-"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.translate(_FOLD)).strip().lower()


def _citation_report(case: HeroCase, outcomes: list[RecommendationOutcome]) -> tuple[int, int, int, list[str]]:
    """Validate every axis-evidence quote against its source report body.

    Returns (exact, normalized_only, invalid, failures)."""
    id_to_text = {r.report_id: r.full_text for r in case.reports}
    exact = normalized = invalid = 0
    failures: list[str] = []
    for outcome in outcomes:
        result = outcome.reconciliation
        if result is None:
            continue
        for assessment in result.candidate_assessments:
            for axis_name in (
                "modality_adequacy", "anatomic_coverage", "finding_acknowledgment",
                "temporal_adequacy", "terminal_event",
            ):
                axis = getattr(assessment.axes, axis_name)
                for ev in axis.evidence:
                    src = id_to_text.get(ev.source_id)
                    if src is not None and ev.quote in src:
                        exact += 1
                    elif src is not None and _norm(ev.quote) in _norm(src):
                        normalized += 1
                    else:
                        invalid += 1
                        failures.append(f"{case.case_id}/{assessment.study_id}/{axis_name}: {ev.quote[:70]!r}")
    return exact, normalized, invalid, failures


def main() -> int:
    ap = argparse.ArgumentParser(description="Safety Net eval harness")
    ap.add_argument("--live", action="store_true", help="reconcile via the API instead of cache")
    args = ap.parse_args()

    use_cache = not args.live
    if args.live and not has_api_key():
        print("--live requires ANTHROPIC_API_KEY; falling back to cache.")
        use_cache = True

    cases = load_hero_cases()
    tp = fp = fn = tn = 0          # surfacing confusion matrix
    status_correct = status_total = 0
    cite_exact = cite_norm = cite_invalid = 0
    all_failures: list[str] = []

    print("Safety Net eval  (" + ("cache" if use_cache else "live") + ")")
    print("=" * 60)
    for case in cases:
        outcomes = run_hero_case(case, draft=False, use_cache=use_cache)
        primary = outcomes[0].reconciliation if outcomes else None
        actual_state = primary.closure_state if primary else None
        surfaced = any(
            o.reconciliation and (o.reconciliation.escalation.required
                                  or o.reconciliation.closure_state in SURFACED_STATES)
            for o in outcomes
        )

        # Status accuracy vs ground truth.
        exp_state = case.expected_closure_state
        state_ok = exp_state is None or actual_state == exp_state
        if exp_state is not None:
            status_total += 1
            status_correct += int(state_ok)

        # Surfacing confusion matrix vs expected_escalation.
        exp_surface = bool(case.expected_escalation)
        if exp_surface and surfaced:
            tp += 1
        elif exp_surface and not surfaced:
            fn += 1
        elif not exp_surface and surfaced:
            fp += 1
        else:
            tn += 1

        # Citation grounding.
        ex, nm, inv, fails = _citation_report(case, outcomes)
        cite_exact += ex; cite_norm += nm; cite_invalid += inv; all_failures += fails

        mark = "✓" if (state_ok and (surfaced == exp_surface) and inv == 0) else "✗"
        print(f"  [{mark}] {case.case_id:8} expected={exp_state.value if exp_state else '—':11} "
              f"got={actual_state.value if actual_state else 'none':11} "
              f"surfaced={surfaced!s:5} cites={ex + nm}/{ex + nm + inv} valid")

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    cite_total = cite_exact + cite_norm + cite_invalid

    print("=" * 60)
    print(f"  status accuracy : {status_correct}/{status_total}")
    print(f"  precision       : {precision:.2f}  (TP={tp} FP={fp})   — false alarms in front of a clinician")
    print(f"  recall          : {recall:.2f}  (TP={tp} FN={fn})")
    print(f"  citations valid : {cite_total - cite_invalid}/{cite_total}  "
          f"({cite_exact} exact, {cite_norm} normalized, {cite_invalid} hallucinated)")
    if all_failures:
        print("  citation failures:")
        for f in all_failures:
            print("   -", f)

    # Gates: perfect status, zero false positives, zero hallucinated citations.
    ok = (status_correct == status_total) and fp == 0 and cite_invalid == 0
    print("=" * 60)
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
