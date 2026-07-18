"""Thin FastMCP wrapper exposing the sweep/reconcile capability as tools.

Deliberately a thin adapter: each tool parses its input into the core models,
calls the corresponding core function, and returns a plain dict. No logic that
belongs in the core modules lives here. This server is a credibility exhibit
and is kept OFF the live demo path — the UI calls the core Python directly.
"""

from __future__ import annotations

from fastmcp import FastMCP

from . import actions as _actions
from . import chart_review as _chart_review
from . import eval_harness as _eval
from . import extract as _extract
from . import reconcile as _reconcile
from . import sweep as _sweep
from .models import (
    ActionDraft,
    Candidate,
    ChartBundle,
    ExtractedSignal,
    Note,
    Recommendation,
    ReconciliationResult,
    Report,
    Thread,
)
from .timeline import build_threads as _build_threads

mcp = FastMCP("safety-net")


@mcp.tool
def list_reports() -> list[dict]:
    """List the backlog reports (heroes + filler) with light metadata."""
    return [
        {
            "report_id": r.report_id,
            "patient_id": r.patient_id,
            "date": r.date,
            "modality": r.modality,
            "specialty": r.specialty,
        }
        for r in _sweep.backlog_reports()
    ]


@mcp.tool
def list_hero_cases() -> list[dict]:
    """List the hand-authored hero cases."""
    return [
        {"case_id": c.case_id, "title": c.title, "patient_name": c.patient_name}
        for c in _sweep.load_hero_cases()
    ]


@mcp.tool
def run_hero_case(case_id: str, use_cache: bool = True) -> list[dict]:
    """Run the full pipeline for one hero case; returns per-recommendation
    outcomes. Uses cached responses by default so it works offline."""
    cases = {c.case_id: c for c in _sweep.load_hero_cases()}
    if case_id not in cases:
        raise ValueError(f"Unknown case_id: {case_id!r}")
    outcomes = _sweep.run_hero_case(cases[case_id], use_cache=use_cache)
    return [o.model_dump(mode="json") for o in outcomes]


@mcp.tool
def extract(report: dict) -> dict:
    """Extract recommendations + study object from one report."""
    result = _extract.extract_report(Report.model_validate(report))
    return result.model_dump(mode="json")


@mcp.tool
def reconcile(recommendation: dict, candidates: list[dict], as_of_date: str) -> dict:
    """Reconcile one recommendation against candidate studies (Opus)."""
    result = _reconcile.reconcile(
        Recommendation.model_validate(recommendation),
        [Candidate.model_validate(c) for c in candidates],
        as_of_date,
    )
    return result.model_dump(mode="json")


@mcp.tool
def draft_action(recommendation: dict, reconciliation: dict) -> dict:
    """Draft outreach for an escalate/open-overdue recommendation (Opus)."""
    action = _actions.draft_action(
        Recommendation.model_validate(recommendation),
        ReconciliationResult.model_validate(reconciliation),
    )
    return action.model_dump(mode="json")


@mcp.tool
def approve_action(action: dict, approver: str) -> dict:
    """Human-in-the-loop approval; returns the approved action + audit event."""
    approved, event = _actions.approve_action(
        ActionDraft.model_validate(action), approver
    )
    return {"action": approved.model_dump(mode="json"), "audit": event.model_dump(mode="json")}


# ======================================================================
# WHOLE-CHART REVIEW TOOLS — the pivot's capability, exposed as thin tools.
# Off the live demo path (the UI calls core Python directly); this is the
# credibility exhibit: the same engine runs over MCP with no EHR integration.
# ======================================================================


@mcp.tool
def review_chart(use_cache: bool = True) -> dict:
    """Run the whole-chart discharge review; returns the ChartReviewResult
    (summary_line, ranked surfaced findings, cleared). Offline via the committed
    cache by default; set use_cache=false to run Haiku+Opus live."""
    bundle = _chart_review.load_chart()
    result = _chart_review.run_review(bundle, use_cache=use_cache)
    return result.model_dump(mode="json")


@mcp.tool
def evaluate_chart(use_cache: bool = True) -> dict:
    """Run the eval harness against the ground-truth manifest; returns the
    live-set gate result + EvalSummary (precision/recall, per-item, suppression
    traces)."""
    result, summary, passed = _eval.run_and_evaluate(use_cache=use_cache)
    return {
        "passed_gate": passed,
        "summary_line": result.summary_line,
        "eval": summary.model_dump(mode="json"),
    }


@mcp.tool
def extract_chart_signals(note: dict) -> list[dict]:
    """Extract the atomic signals from one note (Haiku, live)."""
    signals = _extract.extract_signals(Note.model_validate(note))
    return [s.model_dump(mode="json") for s in signals]


@mcp.tool
def build_chart_threads(signals: list[dict]) -> list[dict]:
    """Group extracted signals into threads by entity (deterministic, no LLM)."""
    sigs = [ExtractedSignal.model_validate(s) for s in signals]
    return [t.model_dump(mode="json") for t in _build_threads(sigs)]


@mcp.tool
def reconcile_chart_thread(thread: dict, signals: list[dict], chart: dict) -> dict:
    """Reconcile one thread against the discharge documentation (Opus, live)."""
    bundle = ChartBundle.model_validate(chart)
    sigs = {s["signal_id"]: ExtractedSignal.model_validate(s) for s in signals}
    finding = _reconcile.reconcile_thread(Thread.model_validate(thread), sigs, bundle)
    return finding.model_dump(mode="json")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
