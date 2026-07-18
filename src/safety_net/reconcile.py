"""Opus reconciliation — the reasoning core.

Given one open recommendation and its candidate later studies, run the
five-axis reasoning via the verbatim system prompt and return a
contract-compliant ``ReconciliationResult``, with a verbatim citation behind
every determination. Ambiguous / unconfirmed cases escalate; they are never
silently closed — that rule lives in the system prompt and is preserved here.
"""

from __future__ import annotations

import json

from .client import call_json, MODEL_OPUS
from .models import (
    Candidate,
    ChartBundle,
    ExtractedSignal,
    Finding,
    Recommendation,
    ReconciliationInput,
    ReconciliationResult,
    Thread,
)
from .prompts import RECONCILIATION_SYSTEM, WHOLE_CHART_REASONING_SYSTEM


def reconcile(
    recommendation: Recommendation,
    candidates: list[Candidate],
    as_of_date: str,
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
    )
    result = ReconciliationResult.model_validate(data)
    # Defensive: the emitted recommendation_id must echo the input id so the
    # state machine and UI can key on it reliably.
    if result.recommendation_id != recommendation.id:
        result.recommendation_id = recommendation.id
    return result


# ======================================================================
# WHOLE-CHART RECONCILIATION — Stage 3 (the reasoning hero). One Opus call per
# Thread with the doc-03 prompt: the thread's events (with verbatim note bodies)
# plus the three discharge closure documents. Opus decides whether the loop is
# closed (possibly reworded -> CONFIRMED_ADDRESSED), silently open (UNCONFIRMED),
# contradicted, or pending; every claim carries a verbatim citation.
# ======================================================================


def _build_thread_payload(
    thread: Thread,
    signals_by_id: dict[str, ExtractedSignal],
    bundle: ChartBundle,
) -> str:
    """Assemble the user-turn JSON: the thread's flagged events + the full
    verbatim bodies of their source notes + the discharge summary/addendum/PCP
    letter (so the reasoner can find a reworded closure or evidence an absence)."""
    events = []
    source_note_ids: list[str] = []
    for sid in thread.event_signal_ids:
        sig = signals_by_id.get(sid)
        if sig is None:
            continue
        src = bundle.note_by_id(sig.source_note_id)
        events.append(
            {
                "day": sig.day,
                "note_type": src.note_type.value if src is not None else "",
                "source_note_id": sig.source_note_id,
                "signal_type": sig.signal_type.value,
                "flagged_excerpt": sig.verbatim_excerpt,
                "summary": sig.summary,
            }
        )
        if sig.source_note_id not in source_note_ids:
            source_note_ids.append(sig.source_note_id)

    source_notes = []
    for nid in source_note_ids:
        note = bundle.note_by_id(nid)
        if note is not None:
            source_notes.append(
                {
                    "note_id": note.note_id,
                    "day": note.day,
                    "note_type": note.note_type.value,
                    "body": note.body,
                }
            )

    def _doc(note):
        return None if note is None else {"note_id": note.note_id, "body": note.body}

    payload = {
        "thread_id": thread.thread_id,
        "entity": thread.entity,
        "signal_type": thread.signal_type.value,
        "events": events,
        "source_notes": source_notes,
        "discharge_summary": _doc(bundle.discharge_summary),
        "discharge_addendum": _doc(bundle.discharge_addendum),
        "pcp_letter": _doc(bundle.pcp_letter),
    }
    return json.dumps(payload, indent=2)


def reconcile_thread(
    thread: Thread,
    signals_by_id: dict[str, ExtractedSignal],
    bundle: ChartBundle,
) -> Finding:
    """Reconcile one thread against the discharge documentation (Opus)."""
    data = call_json(
        MODEL_OPUS,
        WHOLE_CHART_REASONING_SYSTEM,
        _build_thread_payload(thread, signals_by_id, bundle),
        max_tokens=4096,
    )
    finding = Finding.model_validate(data)
    # Defensive: echo the input thread_id and assign a stable finding_id; the
    # model is told not to set surfaced/finding_id — the pipeline owns those.
    finding.thread_id = thread.thread_id
    finding.finding_id = f"f_{thread.entity}"
    return finding
