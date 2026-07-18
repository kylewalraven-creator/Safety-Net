"""Eval harness — the self-verification gate (Stage 7).

Two checks, both must pass on the live set (build plan §Eval harness spec):

  A. Verbatim-citation validator — every ``presence`` timeline excerpt in every
     finding (surfaced AND cleared) is an exact substring of its cited note.
     Any miss is a hard fail (and should have been rejected upstream).

  B. Ground-truth scorer — compares each planted item's surfaced/status against
     the doc-02 manifest, computes precision/recall, and flags any surfaced
     finding that isn't a planted dot as a false positive.

The live-set gate encodes the definition of done: H4 surfaces UNCONFIRMED/High,
H1 surfaces, H_SUPPRESS is suppressed (CONFIRMED_ADDRESSED, cited to the PCP
letter), precision == 1.0, and every citation validates. ``main`` runs the
review from cache, scores it, writes the run log, and exits non-zero if the gate
fails — so the build self-verifies.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .grounding import validate_citations
from .models import (
    Abstention,
    ChartBundle,
    ChartReviewResult,
    EvalSummary,
    Finding,
    GroundTruth,
    PerItem,
    Risk,
    SuppressionTrace,
    ThreadStatus,
)

RUN_LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "chart" / "run_log.json"


# ---------------------------------------------------------------------------
# A. Citation validation
# ---------------------------------------------------------------------------


def validate_all_citations(
    result: ChartReviewResult, bundle: ChartBundle
) -> tuple[int, int, int, list[str]]:
    """Validate every presence excerpt across findings + cleared. Returns
    (checked, passed, failed, failure_descriptions)."""
    checked = passed = 0
    failures: list[str] = []
    for f in list(result.findings) + list(result.cleared):
        for c in validate_citations(f, bundle):
            checked += 1
            if c.ok:
                passed += 1
            else:
                failures.append(f"{f.thread_id}: {c.source_note_id} excerpt not a substring")
    return checked, passed, checked - passed, failures


# ---------------------------------------------------------------------------
# B. Ground-truth scorer
# ---------------------------------------------------------------------------


def _finding_by_thread(result: ChartReviewResult, thread_id: str) -> tuple[Finding | None, bool]:
    """Return (finding, surfaced?) searching surfaced then cleared."""
    for f in result.findings:
        if f.thread_id == thread_id:
            return f, True
    for f in result.cleared:
        if f.thread_id == thread_id:
            return f, False
    return None, False


def score(
    result: ChartReviewResult, gt: GroundTruth, bundle: ChartBundle
) -> EvalSummary:
    per_item: list[PerItem] = []
    tp = fp = fn = tn = 0
    planted_thread_ids = {f"t_{item.entity}" for item in gt.items}

    for item in gt.items:
        thread_id = f"t_{item.entity}"
        finding, surfaced = _finding_by_thread(result, thread_id)
        got_status = finding.status.value if finding else "MISSING"
        exp = item.expected_status.value

        if item.surfaced:  # expected to surface
            outcome = "TP" if surfaced else "FN"
            tp += 1 if surfaced else 0
            fn += 0 if surfaced else 1
        else:  # expected to be suppressed (H_SUPPRESS)
            outcome = "FP" if surfaced else "TN"
            fp += 1 if surfaced else 0
            tn += 1 if not surfaced else 0

        per_item.append(
            PerItem(
                planted_id=item.planted_id, expected_status=exp,
                got_status=got_status, outcome=outcome, entity=item.entity,
            )
        )

    # Any SURFACED finding that is not a planted dot is a false positive.
    for f in result.findings:
        if f.thread_id not in planted_thread_ids:
            fp += 1
            per_item.append(
                PerItem(planted_id=f"UNPLANTED:{f.thread_id}", expected_status="(none)",
                        got_status=f.status.value, outcome="FP", entity=f.thread_id[2:])
            )

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0

    suppression_traces = [
        SuppressionTrace(thread_id=f.thread_id, reason=f.cleared_reason or f.connection)
        for f in result.cleared
        if f.status is ThreadStatus.CONFIRMED_ADDRESSED
    ]
    abstentions = [
        Abstention(thread_id=f.thread_id, trigger=f.cleared_reason or "")
        for f in result.cleared
        if f.cleared_reason and f.cleared_reason.startswith("abstained")
    ]

    return EvalSummary(
        precision=precision, recall=recall, per_item=per_item,
        suppression_traces=suppression_traces, abstentions=abstentions,
    )


# ---------------------------------------------------------------------------
# Live-set gate (the definition of done)
# ---------------------------------------------------------------------------


def check_live_gate(
    result: ChartReviewResult, gt: GroundTruth, bundle: ChartBundle, summary: EvalSummary
) -> tuple[bool, list[str]]:
    """Return (passed, lines) verifying every definition-of-done condition."""
    lines: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        ok = ok and cond
        lines.append(f"  [{'PASS' if cond else 'FAIL'}] {label}")

    # 1. H4 surfaced, UNCONFIRMED, High.
    h4, h4_surf = _finding_by_thread(result, "t_apixaban")
    check(
        h4 is not None and h4_surf and h4.status is ThreadStatus.UNCONFIRMED and h4.risk is Risk.HIGH,
        "H4 apixaban surfaces as UNCONFIRMED / High",
    )
    # 1b. H1 also surfaces (UNCONFIRMED / High).
    h1, h1_surf = _finding_by_thread(result, "t_pulmonary_nodule_lll")
    check(
        h1 is not None and h1_surf and h1.status is ThreadStatus.UNCONFIRMED and h1.risk is Risk.HIGH,
        "H1 nodule surfaces in the sweep as UNCONFIRMED / High",
    )
    # 2. H_SUPPRESS NOT surfaced, CONFIRMED_ADDRESSED, cited to the PCP letter.
    hs, hs_surf = _finding_by_thread(result, "t_colonoscopy_followup")
    cited_pcp = bool(hs and any(ev.source_note_id == "n_pcp_d14" for ev in hs.timeline))
    check(
        hs is not None and not hs_surf and hs.status is ThreadStatus.CONFIRMED_ADDRESSED and cited_pcp,
        "H_SUPPRESS suppressed (cleared), CONFIRMED_ADDRESSED, cited to the PCP letter",
    )
    # 3. Precision == 1.0 (zero false positives).
    check(summary.precision == 1.0, f"precision == 1.0 on the surfaced set (got {summary.precision:.3f})")
    # 4. All presence citations validate.
    checked, passed, failed, _ = validate_all_citations(result, bundle)
    check(failed == 0, f"all presence citations validate ({passed}/{checked})")

    return ok, lines


# ---------------------------------------------------------------------------
# CLI — run the review, score, write the run log, gate.
# ---------------------------------------------------------------------------


def run_and_evaluate(*, use_cache: bool = True) -> tuple[ChartReviewResult, EvalSummary, bool]:
    from .chart_review import load_chart, load_ground_truth, run_review

    bundle = load_chart()
    gt = load_ground_truth()
    result = run_review(bundle, use_cache=use_cache)

    checked, passed, failed, failures = validate_all_citations(result, bundle)
    summary = score(result, gt, bundle)
    passed_gate, gate_lines = check_live_gate(result, gt, bundle, summary)
    summary.passed_gate = passed_gate
    if failures:
        summary.notes.extend(failures)

    # Attach the eval to run_meta + write the run log (the reliability exhibit).
    if result.run_meta is not None:
        result.run_meta.eval = summary
        result.run_meta.citation_validation.checked = checked
        result.run_meta.citation_validation.passed = passed
        result.run_meta.citation_validation.failed = failed
    RUN_LOG_PATH.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2), encoding="utf-8"
    )

    # Report.
    print("\n=== EVAL HARNESS ===")
    print(f"chart: {result.chart_id}   summary: {result.summary_line}")
    print(f"precision: {summary.precision:.3f}   recall: {summary.recall:.3f}")
    print(f"citations: {passed}/{checked} valid" + (f"  FAILURES: {failures}" if failures else ""))
    print("\nper-item:")
    for pi in summary.per_item:
        print(f"  {pi.outcome:3s}  {pi.planted_id:22s} expected={pi.expected_status:20s} got={pi.got_status}")
    print("\nsuppression traces (Q&A gold):")
    for st in summary.suppression_traces:
        print(f"  {st.thread_id}: {st.reason}")
    print("\nlive-set gate:")
    for line in gate_lines:
        print(line)
    print(f"\nGATE: {'PASS ✅' if passed_gate else 'FAIL ❌'}   (run log -> {RUN_LOG_PATH.name})")
    return result, summary, passed_gate


def main(argv: list[str] | None = None) -> int:
    _, _, passed = run_and_evaluate(use_cache=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
