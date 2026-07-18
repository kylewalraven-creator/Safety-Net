"""Thin FastMCP wrapper exposing the sweep/reconcile capability as tools.

Deliberately a thin adapter: each tool parses its input into the core models,
calls the corresponding core function, and returns a plain dict. No logic that
belongs in the core modules lives here. This server is a credibility exhibit
and is kept OFF the live demo path — the UI calls the core Python directly.
"""

from __future__ import annotations

from fastmcp import FastMCP

from . import actions as _actions
from . import extract as _extract
from . import reconcile as _reconcile
from . import sweep as _sweep
from .models import (
    ActionDraft,
    Candidate,
    Recommendation,
    ReconciliationResult,
    Report,
)

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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
