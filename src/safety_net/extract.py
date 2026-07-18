"""Haiku bulk extraction.

Given a finished report, return the follow-up recommendations it states (as
contract-compliant ``Recommendation`` objects) plus the report itself as a
``Study`` that could later serve as a candidate for an earlier recommendation.

The model performs the *semantic* extraction (finding, site, modality,
timeframe, urgency, verbatim text). This module attaches the *deterministic*
identity/linkage fields from the report, so IDs are stable and never invented
by the model.
"""

from __future__ import annotations

import json
import re

from .client import call_json, MODEL_HAIKU
from .models import (
    ChartBundle,
    ExtractedSignal,
    ExtractionResult,
    Note,
    Recommendation,
    Report,
    SignalType,
    Study,
)
from .prompts import EXTRACTION_SYSTEM, WHOLE_CHART_EXTRACTION_SYSTEM


def _format_report(report: Report) -> str:
    return json.dumps(
        {
            "report_id": report.report_id,
            "date": report.date,
            "modality": report.modality,
            "specialty": report.specialty,
            "full_text": report.full_text,
        },
        indent=2,
    )


def _clean(value: object, default: str = "") -> str:
    text = str(value).strip() if value is not None else ""
    return text or default


def _build_recommendation(report: Report, idx: int, item: dict) -> Recommendation:
    return Recommendation(
        id=f"{report.report_id}-rec-{idx + 1}",
        source_id=report.report_id,
        report_date=report.date,
        finding=_clean(item.get("finding")),
        anatomic_site=_clean(item.get("anatomic_site")),
        recommended_modality=_clean(item.get("recommended_modality"), "unspecified"),
        recommended_timeframe=_clean(item.get("recommended_timeframe"), "unspecified"),
        urgency_tier=_clean(item.get("urgency_tier"), "routine"),
        original_text=_clean(item.get("original_text")),
    )


def _build_study(report: Report, study_obj: dict) -> Study:
    return Study(
        study_id=report.report_id,
        patient_id=report.patient_id,
        report_id=report.report_id,
        date=report.date,
        modality=_clean(study_obj.get("modality"), report.modality),
        anatomic_coverage=_clean(study_obj.get("anatomic_coverage")),
        impression_text=_clean(study_obj.get("impression_text")),
        full_text=report.full_text,
    )


def extract_report(report: Report, *, temperature: float = 0.0) -> ExtractionResult:
    """Extract recommendations + the study object from a single report."""
    data = call_json(
        MODEL_HAIKU,
        EXTRACTION_SYSTEM,
        _format_report(report),
        max_tokens=1536,
        temperature=temperature,
    )
    raw_recs = data.get("recommendations") or []
    recommendations = [
        _build_recommendation(report, i, item)
        for i, item in enumerate(raw_recs)
        if isinstance(item, dict) and _clean(item.get("finding"))
    ]
    study = _build_study(report, data.get("study") or {})
    return ExtractionResult(recommendations=recommendations, study=study)


def extract_reports(reports: list[Report], *, temperature: float = 0.0) -> list[ExtractionResult]:
    """Extract over a backlog of reports (bulk, cheap)."""
    return [extract_report(r, temperature=temperature) for r in reports]


# ======================================================================
# WHOLE-CHART EXTRACTION — widened from "recommendation" to the signal
# taxonomy (Stage 1 of the whole-chart pipeline). Same discipline as above:
# the model does the semantic extraction; this module attaches the
# deterministic identity/source fields and enforces the verbatim-substring
# rule (reject anything whose excerpt is not an exact substring of the note).
# ======================================================================


# Notes whose content is the CLOSURE context, not a source of new threads. The
# reconciler reads these directly for every thread (absence / reworded closure),
# so mining them for signals only spawns spurious "already-addressed" threads.
_DISCHARGE_NOTE_TYPES = {"discharge_summary", "discharge_addendum", "pcp_letter"}

# Deterministic entity canonicalization — a backstop to the prompt's rules, so
# live extraction drift (a size suffix, a med-status suffix) doesn't fragment a
# thread or dodge the ground-truth key. The prompt is the primary mechanism.
_MEASURE_SUFFIX = re.compile(
    r"_[0-9]+(?:[_.][0-9]+)?_?(?:mm|cm|ml|mcg|mg|kg|g|cc|units?)$"
)
_MED_STATUS_SUFFIX = re.compile(
    r"_(?:restart(?:ed)?|resumption|resumed|resume|hold|held|discontinued|"
    r"discontinuation|stopped)$"
)


def canonicalize_entity(entity: str) -> str:
    """Normalize an extracted entity key so events about the same thing thread
    together and match the canonical manifest keys. Lowercases, snake-cases, and
    strips trailing size (``_9mm``) and medication-status (``_restart``) suffixes.
    Deliberately conservative — it does not strip clinical qualifiers."""
    e = (entity or "").strip().lower()
    e = re.sub(r"[\s\-/]+", "_", e)
    e = re.sub(r"[^a-z0-9_]", "", e)
    e = re.sub(r"_+", "_", e).strip("_")
    prev = None
    while prev != e and e:
        prev = e
        e = _MEASURE_SUFFIX.sub("", e).strip("_")
        e = _MED_STATUS_SUFFIX.sub("", e).strip("_")
    return e


def _format_note(note: Note) -> str:
    return json.dumps(
        {
            "note_id": note.note_id,
            "day": note.day,
            "author_role": note.author_role,
            "note_type": note.note_type.value,
            "body": note.body,
        },
        indent=2,
    )


def extract_signals(note: Note, *, temperature: float = 0.0) -> list[ExtractedSignal]:
    """Extract the atomic signals from a single note (Haiku).

    Every returned signal is guaranteed to have a ``verbatim_excerpt`` that is an
    exact substring of ``note.body`` — non-matching signals are dropped (the same
    anti-hallucination discipline the reconciler and harness enforce)."""
    data = call_json(
        MODEL_HAIKU,
        WHOLE_CHART_EXTRACTION_SYSTEM,
        _format_note(note),
        max_tokens=2048,
        temperature=temperature,
    )
    raw_signals = data.get("signals") or []
    signals: list[ExtractedSignal] = []
    for i, item in enumerate(raw_signals):
        if not isinstance(item, dict):
            continue
        excerpt = _clean(item.get("verbatim_excerpt"))
        entity = canonicalize_entity(_clean(item.get("entity")))
        # Enforce the substring rule at the source: silence != a citation.
        if not excerpt or excerpt not in note.body or not entity:
            continue
        try:
            signal_type = SignalType(_clean(item.get("signal_type")))
        except ValueError:
            continue
        signals.append(
            ExtractedSignal(
                signal_id=f"{note.note_id}-sig-{i + 1}",
                source_note_id=note.note_id,
                day=note.day,
                signal_type=signal_type,
                entity=entity,
                summary=_clean(item.get("summary")),
                verbatim_excerpt=excerpt,
            )
        )
    return signals


def extract_chart(bundle: ChartBundle, *, temperature: float = 0.0) -> list[ExtractedSignal]:
    """Bulk-extract signals across the admission notes.

    The discharge documents (summary, addendum, PCP letter) are skipped: they are
    the CLOSURE context the reconciler reads against every thread, not a source of
    new threads. Mining them only manufactures spurious "already-addressed"
    threads (e.g. a reworded follow-up), which is noise, not a fallen thread."""
    signals: list[ExtractedSignal] = []
    for note in bundle.notes:
        if note.note_type.value in _DISCHARGE_NOTE_TYPES:
            continue
        signals.extend(extract_signals(note, temperature=temperature))
    return signals
