"""Opus action-drafting for escalate / open-overdue cases.

Produces the specific, human-answerable outreach a clinician reviews and
approves. Nothing is sent autonomously: ``draft_action`` returns a DRAFT, and
``approve_action`` is the explicit human-in-the-loop step that also emits an
append-only audit event.
"""

from __future__ import annotations

import datetime as _dt
import json

from .client import call_json, MODEL_OPUS
from .models import (
    ActionDraft,
    ActionStatus,
    ActionType,
    AuditEvent,
    ClosureState,
    Recommendation,
    ReconciliationResult,
)
from .prompts import ACTION_DRAFT_SYSTEM

# Closure states that warrant human outreach.
ESCALATABLE: set[ClosureState] = {ClosureState.ESCALATE, ClosureState.OPEN_OVERDUE}


def should_draft(reconciliation: ReconciliationResult) -> bool:
    """True if this reconciliation warrants a drafted action."""
    return reconciliation.closure_state in ESCALATABLE


def _format_input(recommendation: Recommendation, reconciliation: ReconciliationResult) -> str:
    return json.dumps(
        {
            "recommendation": recommendation.model_dump(),
            "closure_state": reconciliation.closure_state.value,
            "escalation_question": reconciliation.escalation.question,
            "assessments": [
                a.model_dump(mode="json") for a in reconciliation.candidate_assessments
            ],
        },
        indent=2,
    )


def draft_action(
    recommendation: Recommendation,
    reconciliation: ReconciliationResult,
    *,
    temperature: float = 0.2,
) -> ActionDraft:
    """Draft the outreach for a recommendation that could not be confirmed closed."""
    data = call_json(
        MODEL_OPUS,
        ACTION_DRAFT_SYSTEM,
        _format_input(recommendation, reconciliation),
        max_tokens=700,
        temperature=temperature,
    )
    try:
        action_type = ActionType(str(data.get("type", "")).strip())
    except ValueError:
        action_type = ActionType.PROVIDER_MESSAGE
    return ActionDraft(
        action_id=f"{recommendation.id}-action",
        rec_id=recommendation.id,
        type=action_type,
        draft_text=str(data.get("draft_text", "")).strip(),
        status=ActionStatus.DRAFT,
    )


def approve_action(
    action: ActionDraft,
    approver: str,
    *,
    detail: str | None = None,
) -> tuple[ActionDraft, AuditEvent]:
    """Human approval step: mark the draft approved and emit an audit event."""
    ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    approved = action.model_copy(
        update={"status": ActionStatus.APPROVED, "approver": approver, "ts": ts}
    )
    event = AuditEvent(
        ts=ts,
        actor=approver,
        action="approve_action",
        rec_id=action.rec_id,
        detail=detail or f"Approved {action.type.value} for {action.rec_id}",
    )
    return approved, event
