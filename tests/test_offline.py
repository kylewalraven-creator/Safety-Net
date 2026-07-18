"""Offline tests — exercise the deterministic core and the UI without any API
key. Runnable under pytest, or directly: ``python tests/test_offline.py``."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from safety_net import sweep  # noqa: E402
from safety_net.client import extract_json_block  # noqa: E402
from safety_net.models import (  # noqa: E402
    Axes,
    Candidate,
    CandidateAssessment,
    ClosureState,
    Confidence,
    CoverageAxis,
    Escalation,
    Evidence,
    ModalityAxis,
    PassFailUnclear,
    ModalityResult,
    Recommendation,
    ReconciliationResult,
    RecommendationOutcome,
    Study,
    TemporalAxis,
    TemporalResult,
    TerminalEventAxis,
    TerminalResult,
    TerminalType,
    Verdict,
)
from safety_net.prompts import RECONCILIATION_SYSTEM  # noqa: E402


def _load_ui():
    spec = importlib.util.spec_from_file_location("ui_render", ROOT / "ui" / "render.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_models_roundtrip_worked_examples():
    examples = [
        json.loads(line.strip())
        for line in RECONCILIATION_SYSTEM.splitlines()
        if line.strip().startswith('{"recommendation_id"')
    ]
    assert len(examples) == 2
    a = ReconciliationResult.model_validate(examples[0])
    b = ReconciliationResult.model_validate(examples[1])
    assert a.closure_state is ClosureState.ESCALATE
    assert a.escalation.required and a.escalation.question
    assert a.candidate_assessments[0].verdict is Verdict.UNCONFIRMED
    assert (
        a.candidate_assessments[0].axes.finding_acknowledgment.result
        is PassFailUnclear.FAIL
    )
    assert b.closure_state is ClosureState.SUPERSEDED
    assert not b.escalation.required


def test_anatomic_overlap():
    assert sweep.anatomic_overlap("left upper lobe", "chest")
    assert sweep.anatomic_overlap("right middle lobe", "skull base to mid-thigh")
    assert not sweep.anatomic_overlap("left upper lobe", "abdomen and pelvis")


def test_timeframe_and_overdue():
    assert sweep.timeframe_to_days("6 months") == 180
    assert sweep.timeframe_to_days("3-6 months") == 180
    assert sweep.timeframe_to_days("2 weeks") == 14
    assert sweep.timeframe_to_days("short-interval") is None
    # Case A: Oct 2024 + 6mo, as of mid-2026 -> overdue by naive date logic.
    assert sweep.is_overdue("2024-10-08", "6 months", "2026-07-18")
    # A recent rec well within its window -> not overdue.
    assert not sweep.is_overdue("2026-06-01", "6 months", "2026-07-18")


def test_match_candidates_case_a():
    rec = Recommendation(
        id="A-R1-rec-1", source_id="A-R1", report_date="2024-10-08",
        finding="9 mm left upper lobe nodule", anatomic_site="left upper lobe",
        recommended_modality="CT chest", recommended_timeframe="6 months",
        urgency_tier="routine", original_text="Recommend follow-up CT chest in 6 months.",
    )
    source = Study(
        study_id="A-R1", patient_id="PT-A-2213", report_id="A-R1", date="2024-10-08",
        modality="CT chest", anatomic_coverage="chest", impression_text="nodule",
        full_text="...",
    )
    later = Study(
        study_id="A-R2", patient_id="PT-A-2213", report_id="A-R2", date="2025-03-18",
        modality="CT chest", anatomic_coverage="chest", impression_text="no PE",
        full_text="...",
    )
    other_patient = Study(
        study_id="X", patient_id="OTHER", report_id="X", date="2025-05-01",
        modality="CT chest", anatomic_coverage="chest", impression_text="",
        full_text="...",
    )
    candidates = sweep.match_candidates(rec, "PT-A-2213", [source, later, other_patient])
    ids = [c.id for c in candidates]
    assert ids == ["A-R2"]  # source excluded, other patient excluded, later included


def test_opus_omits_temperature():
    from safety_net.client import MODEL_HAIKU, MODEL_OPUS, _request_params

    # Opus 4.8 rejects temperature -> must never appear, even if passed.
    assert "temperature" not in _request_params(MODEL_OPUS, "s", "u", 128, 0.0)
    # Haiku accepts it when provided.
    assert _request_params(MODEL_HAIKU, "s", "u", 128, 0.0)["temperature"] == 0.0
    # None is always omitted.
    assert "temperature" not in _request_params(MODEL_HAIKU, "s", "u", 128, None)


def test_extract_json_block():
    assert json.loads(extract_json_block('```json\n{"a": 1}\n```')) == {"a": 1}
    assert json.loads(extract_json_block('prefix {"a": {"b": 2}} suffix')) == {"a": {"b": 2}}
    # Braces inside strings must not confuse the scanner.
    assert json.loads(extract_json_block('{"q": "a } b { c"}')) == {"q": "a } b { c"}


def test_highlight_tolerates_whitespace_and_smart_quotes():
    ui = _load_ui()
    source = "IMPRESSION:\nNo acute pulmonary embolism. Mild bronchial wall thickening."
    # Quote uses collapsed whitespace and would otherwise fail an exact match.
    out = ui.highlight(source, ["No acute pulmonary embolism."])
    assert "<mark>No acute pulmonary embolism.</mark>" in out


def _synthetic_case_a_outcome() -> RecommendationOutcome:
    rec = Recommendation(
        id="A-R1-rec-1", source_id="A-R1", report_date="2024-10-08",
        finding="solid 9 mm nodule in the left upper lobe", anatomic_site="left upper lobe",
        recommended_modality="CT chest", recommended_timeframe="6 months",
        urgency_tier="routine",
        original_text="Recommend follow-up CT chest in 6 months to assess for interval change.",
    )
    cand = Candidate(
        id="A-R2", report_date="2025-03-18", modality="CT angiogram chest (PE protocol)",
        anatomic_coverage="chest",
        impression_text="No acute pulmonary embolism. Mild bronchial wall thickening compatible with bronchitis. No pleural effusion.",
        full_text="...",
    )
    axes = Axes(
        modality_adequacy=ModalityAxis(
            result=ModalityResult.PASS, reason="Chest CT can assess a nodule.",
            evidence=[Evidence(source_id="A-R2", quote="CT ANGIOGRAM, CHEST (PE PROTOCOL)")],
        ),
        anatomic_coverage=CoverageAxis(
            result=PassFailUnclear.PASS, reason="Images the chest.",
            evidence=[Evidence(source_id="A-R2", quote="CHEST")],
        ),
        finding_acknowledgment=CoverageAxis(
            result=PassFailUnclear.FAIL, reason="Silent on the left upper lobe nodule.",
            evidence=[Evidence(source_id="A-R2", quote="No acute pulmonary embolism. Mild bronchial wall thickening compatible with bronchitis. No pleural effusion.")],
        ),
        temporal_adequacy=TemporalAxis(
            result=TemporalResult.ON_TIME, reason="Within the 6-month window.",
            evidence=[Evidence(source_id="A-R2", quote="2025-03-18")],
        ),
        terminal_event=TerminalEventAxis(
            result=TerminalResult.ABSENT, type=TerminalType.NONE,
            reason="No resolution, biopsy, or documented decision.", evidence=[],
        ),
    )
    result = ReconciliationResult(
        recommendation_id="A-R1-rec-1",
        candidate_assessments=[CandidateAssessment(
            study_id="A-R2", verdict=Verdict.UNCONFIRMED, axes=axes,
            confidence=Confidence.HIGH,
            rationale="A capable chest CT was performed in-window but never mentions the nodule.",
        )],
        closure_state=ClosureState.ESCALATE,
        escalation=Escalation(
            required=True,
            question="A chest CT was performed on 2025-03-18 but does not mention the 9 mm left-upper-lobe nodule from 2024-10-08 — was the nodule reassessed? Confirm / Deny.",
        ),
    )
    return RecommendationOutcome(
        recommendation=rec, patient_id="PT-A-2213", candidates=[cand],
        reconciliation=result, overdue=True, action=None,
    )


def test_ui_renders_case_a_escalation_and_highlight():
    ui = _load_ui()
    case = next(c for c in sweep.load_hero_cases() if c.case_id == "case_a")
    html = ui.build_html([(case, [_synthetic_case_a_outcome()], None)], report_count=8)
    assert "<mark>" in html  # citation highlighted in the source text
    assert "UNCONFIRMED" in html
    assert "ESCALATE" in html
    assert "was the nodule reassessed" in html


def _run_all() -> int:
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"  [✓] {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  [✗] {fn.__name__}: {exc!r}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
