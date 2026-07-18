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

from .client import call_json, MODEL_HAIKU
from .models import ExtractionResult, Recommendation, Report, Study
from .prompts import EXTRACTION_SYSTEM


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
