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
    findings = [
        _finding("addressed", ThreadStatus.CONFIRMED_ADDRESSED, 0.9),          # -> cleared
        _finding("lowconf", ThreadStatus.UNCONFIRMED, 0.30),                   # -> abstain/cleared
        _finding("a", ThreadStatus.UNCONFIRMED, 0.95),                         # -> surfaced
        _finding("b", ThreadStatus.UNCONFIRMED, 0.94),
        _finding("c", ThreadStatus.UNCONFIRMED, 0.93),
        _finding("d", ThreadStatus.UNCONFIRMED, 0.92),
        _finding("e", ThreadStatus.UNCONFIRMED, 0.91),                         # 5th -> capped
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
