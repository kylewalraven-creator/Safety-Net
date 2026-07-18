"""Offline tests for the whole-chart pivot — no API key required.

Exercises the genuinely-new code (threading, grounding/surfacing, the eval
harness) and the deterministic offline pipeline against the committed cache and
ground-truth manifest. Runnable under pytest, or directly:
``python tests/test_whole_chart.py``.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from safety_net import chart_review, eval_harness, extract  # noqa: E402
from safety_net.grounding import apply_surfacing, validate_citations  # noqa: E402
from safety_net.models import (  # noqa: E402
    ABSTAIN_THRESHOLD,
    TOP_N,
    ChartReviewResult,
    ExtractedSignal,
    Finding,
    Note,
    Risk,
    SignalType,
    ThreadStatus,
)
from safety_net.timeline import build_threads  # noqa: E402


# ---- threading (deterministic, new) ----------------------------------


def _sig(sid, nid, day, entity, stype=SignalType.TREND, excerpt="x"):
    return ExtractedSignal(
        signal_id=sid, source_note_id=nid, day=day, signal_type=stype,
        entity=entity, summary="", verbatim_excerpt=excerpt,
    )


def test_threading_groups_by_entity_and_sorts():
    signals = [
        _sig("s3", "n3", 5, "creatinine_series"),
        _sig("s1", "n1", 1, "creatinine_series"),
        _sig("s2", "n2", 3, "creatinine_series"),
        _sig("sa", "na", 1, "apixaban", SignalType.MED_RECON_GAP),
    ]
    threads = build_threads(signals)
    by_entity = {t.entity: t for t in threads}
    assert set(by_entity) == {"creatinine_series", "apixaban"}
    cr = by_entity["creatinine_series"]
    assert cr.thread_id == "t_creatinine_series"
    assert cr.event_signal_ids == ["s1", "s2", "s3"]  # sorted by day
    assert cr.first_day == 1 and cr.last_day == 5
    assert by_entity["apixaban"].signal_type is SignalType.MED_RECON_GAP


def test_single_event_thread_is_valid():
    threads = build_threads([_sig("s1", "n1", 2, "pulmonary_nodule_lll",
                                  SignalType.INCIDENTAL_FINDING)])
    assert len(threads) == 1 and threads[0].first_day == threads[0].last_day == 2


# ---- extraction enforces the verbatim-substring rule -----------------


def test_extraction_drops_nonsubstring_excerpt(monkeypatch):
    note = Note(note_id="n_hold_d1", day=1, timestamp="2026-06-22T10:00:00",
                author_role="hospitalist", note_type="progress_note",
                body="Apixaban held on admission in anticipation of percutaneous drain placement.")

    def fake_call_json(*a, **k):
        return {"signals": [
            {"signal_type": "med_recon_gap", "entity": "apixaban", "summary": "held",
             "verbatim_excerpt": "Apixaban held on admission in anticipation of percutaneous drain placement."},
            {"signal_type": "med_recon_gap", "entity": "apixaban", "summary": "fabricated",
             "verbatim_excerpt": "apixaban resumed at discharge"},  # NOT in the note -> dropped
            {"signal_type": "not_a_real_type", "entity": "x", "summary": "y",
             "verbatim_excerpt": "Apixaban held"},  # bad enum -> dropped
        ]}

    monkeypatch.setattr(extract, "call_json", fake_call_json)
    signals = extract.extract_signals(note)
    assert len(signals) == 1
    assert signals[0].verbatim_excerpt in note.body
    assert signals[0].entity == "apixaban"


# ---- grounding / surfacing -------------------------------------------


def _finding(entity, status, conf, risk=Risk.HIGH, excerpt="Apixaban held on admission in anticipation of percutaneous drain placement.", note="n_hold_d1"):
    return Finding(
        finding_id=f"f_{entity}", thread_id=f"t_{entity}", title=entity, risk=risk,
        status=status, connection="c",
        timeline=[{"day": 1, "note_type": "progress_note", "source_note_id": note,
                   "excerpt": excerpt, "evidence_kind": "presence"}],
        question="q?", confidence=conf,
    )


def test_grounding_suppresses_addressed_abstains_and_caps():
    bundle = chart_review.load_chart()
    # Each finding cites DISTINCT evidence (a different note+excerpt) so the dedup
    # pass leaves them all and the TOP_N cap is exercised for real.
    findings = [
        _finding("addressed", ThreadStatus.CONFIRMED_ADDRESSED, 0.9,
                 excerpt="Acetaminophen 650 mg by mouth every 6 hours as needed for pain.", note="n_dc_d14"),
        _finding("lowconf", ThreadStatus.UNCONFIRMED, 0.30,
                 excerpt="Creatinine 1.2 mg/dL", note="n_labs_d3"),           # -> abstain/cleared
        _finding("a", ThreadStatus.UNCONFIRMED, 0.95,
                 excerpt="Apixaban held on admission in anticipation of percutaneous drain placement.", note="n_hold_d1"),
        _finding("b", ThreadStatus.UNCONFIRMED, 0.94,
                 excerpt="lisinopril 10 mg daily", note="n_medrec_d1"),
        _finding("c", ThreadStatus.UNCONFIRMED, 0.93,
                 excerpt="outpatient colonoscopy in 6", note="n_gi_d4"),
        _finding("d", ThreadStatus.UNCONFIRMED, 0.92,
                 excerpt="Blood cultures x2 drawn for temperature", note="n_micro_d11"),
        _finding("e", ThreadStatus.UNCONFIRMED, 0.91,
                 excerpt="Creatinine 1.6 mg/dL", note="n_labs_d5"),           # 5th -> capped
    ]
    res = apply_surfacing(findings, bundle)
    assert len(res.surfaced) == TOP_N == 4
    assert all(f.surfaced for f in res.surfaced)
    entities_cleared = {f.thread_id for f in res.cleared}
    assert "t_addressed" in entities_cleared and "t_lowconf" in entities_cleared
    assert "t_e" in entities_cleared  # capped beyond TOP_N
    # abstention recorded
    assert any(tid == "t_lowconf" for tid, _ in res.abstentions)


def test_grounding_rejects_bad_citation():
    bundle = chart_review.load_chart()
    bad = _finding("bogus", ThreadStatus.UNCONFIRMED, 0.9, excerpt="text that is not in the note")
    res = apply_surfacing([bad], bundle)
    assert not res.surfaced and len(res.rejected) == 1


# ---- full offline pipeline + harness gate ----------------------------


def test_offline_pipeline_matches_manifest():
    bundle = chart_review.load_chart()
    result = chart_review.run_review(bundle, use_cache=True)
    surfaced = {f.thread_id: f for f in result.findings}
    cleared = {f.thread_id: f for f in result.cleared}
    # 4 surfaced heroes, 1 suppressed look-alike.
    assert set(surfaced) == {
        "t_apixaban", "t_pulmonary_nodule_lll", "t_blood_culture_d11", "t_creatinine_series",
    }
    assert "t_colonoscopy_followup" in cleared
    assert surfaced["t_apixaban"].status is ThreadStatus.UNCONFIRMED
    assert surfaced["t_apixaban"].risk is Risk.HIGH
    assert cleared["t_colonoscopy_followup"].status is ThreadStatus.CONFIRMED_ADDRESSED


def test_harness_gate_passes():
    bundle = chart_review.load_chart()
    gt = chart_review.load_ground_truth()
    result = chart_review.run_review(bundle, use_cache=True)
    checked, passed, failed, failures = eval_harness.validate_all_citations(result, bundle)
    assert failed == 0 and checked == passed and checked > 0, failures
    summary = eval_harness.score(result, gt, bundle)
    assert summary.precision == 1.0
    assert summary.recall == 1.0
    ok, _lines = eval_harness.check_live_gate(result, gt, bundle, summary)
    assert ok


def test_suppress_cited_to_pcp_letter():
    bundle = chart_review.load_chart()
    result = chart_review.run_review(bundle, use_cache=True)
    hs = next(f for f in result.cleared if f.thread_id == "t_colonoscopy_followup")
    note_ids = {ev.source_note_id for ev in hs.timeline}
    assert "n_pcp_d14" in note_ids  # equivalence closure cited to the PCP letter
    assert all(ev.excerpt in bundle.note_by_id(ev.source_note_id).body for ev in hs.timeline)


def test_reconcile_thread_wiring_and_payload(monkeypatch):
    """De-risk the live path (no key here): the reconcile wiring must build a
    payload containing the thread events + all three discharge documents, and
    parse the model's JSON into a Finding with the thread_id echoed and a stable
    finding_id assigned."""
    from safety_net import reconcile as rec

    bundle = chart_review.load_chart()
    signals = {s.signal_id: s for s in _cache_signals()}
    thread = next(t for t in build_threads(list(signals.values()), bundle)
                  if t.entity == "apixaban")

    captured = {}

    def fake_call_json(model, system, user, **k):
        captured["system"] = system
        captured["user"] = user
        return {  # a minimal valid Finding (no finding_id/surfaced — pipeline sets them)
            "thread_id": "WRONG_should_be_overwritten", "title": "t", "risk": "High",
            "status": "UNCONFIRMED", "connection": "c",
            "timeline": [{"day": 1, "note_type": "progress_note", "source_note_id": "n_hold_d1",
                          "excerpt": "Apixaban held on admission in anticipation of percutaneous drain placement.",
                          "evidence_kind": "presence"}],
            "question": "q?", "suggested_action": None, "confidence": 0.9,
        }

    monkeypatch.setattr(rec, "call_json", fake_call_json)
    finding = rec.reconcile_thread(thread, signals, bundle)
    assert finding.thread_id == "t_apixaban"          # echoed from the input thread
    assert finding.finding_id == "f_apixaban"         # pipeline-assigned
    # Payload carries the discharge closure docs the reasoner needs for equivalence/absence.
    assert '"discharge_summary"' in captured["user"] and '"pcp_letter"' in captured["user"]
    assert "n_hold_d1" in captured["user"]            # the thread's source note body
    assert captured["system"].startswith("You are a diagnostic-safety reconciliation reasoner")


def test_canonicalize_entity_collapses_live_drift():
    from safety_net.extract import canonicalize_entity as c
    assert c("pulmonary_nodule_lll_9mm") == "pulmonary_nodule_lll"   # size suffix
    assert c("apixaban_restart") == "apixaban"                       # med-status suffix
    assert c("Apixaban") == "apixaban"                               # case
    assert c("blood_culture_d11") == "blood_culture_d11"             # day suffix preserved
    assert c("creatinine_series") == "creatinine_series"             # unchanged


def test_extract_chart_skips_discharge_documents(monkeypatch):
    bundle = chart_review.load_chart()
    seen: list[str] = []

    def fake_extract_signals(note, **k):
        seen.append(note.note_type.value)
        return []

    monkeypatch.setattr(extract, "extract_signals", fake_extract_signals)
    extract.extract_chart(bundle)
    # The discharge documents are closure context, not thread sources.
    assert "discharge_summary" not in seen
    assert "discharge_addendum" not in seen
    assert "pcp_letter" not in seen
    assert "progress_note" in seen and "radiology_report" in seen  # during-stay mined


def test_harness_matches_by_excerpt_when_entity_drifts():
    """The live failure mode: extraction names an entity differently. The harness
    must still match the dot by its pinned evidence excerpt, not count it FP."""
    bundle = chart_review.load_chart()
    gt = chart_review.load_ground_truth()
    result = chart_review.run_review(bundle, use_cache=True)
    nod = next(f for f in result.findings if f.thread_id == "t_pulmonary_nodule_lll")
    nod.thread_id = "t_pulmonary_nodule_lll_9mm"  # simulate a size-suffixed variant
    nod.finding_id = "f_pulmonary_nodule_lll_9mm"
    summary = eval_harness.score(result, gt, bundle)
    h1 = next(pi for pi in summary.per_item if pi.planted_id == "H1_nodule")
    assert h1.outcome == "TP"                      # matched by excerpt, not missed
    assert summary.precision == 1.0                # and not double-counted as an FP
    assert not any(pi.outcome == "FP" for pi in summary.per_item)


def test_dedup_collapses_split_thread_and_restores_precision():
    """Reproduce the live failure: extraction split the nodule into two entities
    (pulmonary_nodule_lll + chest_ct_followup), both citing the nodule sentence.
    The duplicate was an FP and crowded creatinine out of TOP_N. Dedup must
    collapse it -> precision 1.0, creatinine surfaces."""
    bundle = chart_review.load_chart()
    gt = chart_review.load_ground_truth()

    def F(tid, conf, status, risk, note, excerpt, extra=None):
        tl = [{"day": 2, "note_type": "radiology_report", "source_note_id": note,
               "excerpt": excerpt, "evidence_kind": "presence"}]
        if extra:
            tl.append(extra)
        return Finding.model_validate({
            "finding_id": f"f_{tid[2:]}", "thread_id": tid, "title": tid, "risk": risk,
            "status": status, "connection": "c", "timeline": tl, "question": "q?",
            "confidence": conf,
        })

    nod = "Incidental 9 mm solid nodule in the left lower lobe at the lung base."
    findings = [
        F("t_chest_ct_followup", 0.94, "UNCONFIRMED", "High", "n_ct_d2", nod),      # dup
        F("t_pulmonary_nodule_lll", 0.93, "UNCONFIRMED", "High", "n_ct_d2", nod),   # dup
        F("t_apixaban", 0.90, "UNCONFIRMED", "High", "n_hold_d1",
          "Apixaban held on admission in anticipation of percutaneous drain placement."),
        F("t_blood_culture_d11", 0.82, "PENDING_AT_DISCHARGE", "High", "n_micro_d11",
          "Blood cultures x2 drawn for temperature to 38.9°C. Result: pending."),
        F("t_creatinine_series", 0.75, "UNCONFIRMED", "Medium", "n_labs_d5", "Creatinine 1.6 mg/dL"),
        F("t_colonoscopy_followup", 0.88, "CONFIRMED_ADDRESSED", "Low", "n_gi_d4",
          "outpatient colonoscopy in 6",
          extra={"day": 14, "note_type": "pcp_letter", "source_note_id": "n_pcp_d14",
                 "excerpt": "lower endoscopy with gastroenterology", "evidence_kind": "presence"}),
    ]
    res = apply_surfacing(findings, bundle)
    assert len(res.duplicates) == 1  # one nodule finding dropped as a duplicate
    surfaced_ids = {f.thread_id for f in res.surfaced}
    assert "t_creatinine_series" in surfaced_ids  # no longer crowded out of TOP_N
    nodule_surfaced = [f for f in res.surfaced if f.thread_id in ("t_chest_ct_followup", "t_pulmonary_nodule_lll")]
    assert len(nodule_surfaced) == 1  # exactly one nodule finding survives

    result = ChartReviewResult(chart_id=bundle.chart_id, summary_line="x",
                               findings=res.surfaced, cleared=res.cleared)
    summary = eval_harness.score(result, gt, bundle)
    assert summary.precision == 1.0
    assert summary.recall == 1.0
    assert not any(pi.outcome == "FP" for pi in summary.per_item)
    assert next(pi for pi in summary.per_item if pi.planted_id == "H3_aki").outcome == "TP"


def _cache_signals():
    import json
    from safety_net.models import ExtractedSignal
    data = json.loads((ROOT / "data" / "chart" / "cache" / "signals.json").read_text())
    return [ExtractedSignal.model_validate(d) for d in data]


def _run_all() -> int:
    import inspect
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in funcs:
        params = inspect.signature(fn).parameters
        if "monkeypatch" in params:
            # Minimal monkeypatch shim for standalone (non-pytest) runs.
            class _MP:
                def __init__(self): self._undo = []
                def setattr(self, obj, name, val):
                    self._undo.append((obj, name, getattr(obj, name)))
                    setattr(obj, name, val)
                def undo(self):
                    for obj, name, val in reversed(self._undo): setattr(obj, name, val)
            mp = _MP()
            try:
                fn(mp)
                print(f"  [OK] {fn.__name__}")
            except Exception as exc:  # noqa: BLE001
                failed += 1; print(f"  [XX] {fn.__name__}: {exc!r}")
            finally:
                mp.undo()
        else:
            try:
                fn(); print(f"  [OK] {fn.__name__}")
            except Exception as exc:  # noqa: BLE001
                failed += 1; print(f"  [XX] {fn.__name__}: {exc!r}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
