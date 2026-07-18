"""Opus reconciliation — the reasoning core.

Given one open recommendation and its candidate later studies, run the
five-axis reasoning via the verbatim system prompt and return a
contract-compliant ``ReconciliationResult``, with a verbatim citation behind
every determination. Ambiguous / unconfirmed cases escalate; they are never
silently closed — that rule lives in the system prompt and is preserved here.
"""

from __future__ import annotations

from .client import call_json, MODEL_OPUS
from .models import (
    Candidate,
    Recommendation,
    ReconciliationInput,
    ReconciliationResult,
)
from .prompts import RECONCILIATION_SYSTEM


def reconcile(
    recommendation: Recommendation,
    candidates: list[Candidate],
    as_of_date: str,
    *,
    temperature: float = 0.0,
) -> ReconciliationResult:
    """Reconcile one recommendation against its candidate studies."""
    payload = ReconciliationInput(
        recommendation=recommendation,
        candidates=list(candidates),
        as_of_date=as_of_date,
    )
    data = call_json(
        MODEL_OPUS,
        RECONCILIATION_SYSTEM,
        payload.model_dump_json(indent=2),
        max_tokens=4096,
        temperature=temperature,
    )
    result = ReconciliationResult.model_validate(data)
    # Defensive: the emitted recommendation_id must echo the input id so the
    # state machine and UI can key on it reliably.
    if result.recommendation_id != recommendation.id:
        result.recommendation_id = recommendation.id
    return result
