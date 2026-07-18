#!/usr/bin/env python3
"""Author the deterministic offline cache for the whole-chart review.

This environment has no ANTHROPIC_API_KEY, so the live Haiku/Opus calls can't be
made here. This script authors the artifacts those calls WOULD produce — the
Stage-1 ``ExtractedSignal``s and the Stage-3 ``Finding``s — so the pipeline, the
eval harness, and the UI run deterministically offline (Safety Net's exact
offline-cache posture). With a key, ``python -m safety_net.chart_review
--write-cache`` regenerates these from the real models.

The two live heroes (H4 apixaban, H_SUPPRESS colonoscopy) reuse the doc-03
few-shot anchors verbatim, so the cache and the live few-shot agree exactly.
H1/H2/H3 are authored to the contract. Every excerpt is validated here as an
exact substring of its source note, so a bad citation fails generation loudly.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from safety_net.models import ExtractedSignal, Finding  # noqa: E402

CHART = _ROOT / "data" / "chart" / "chart.json"
DOC03 = _ROOT / "docs" / "whole-chart-reasoning-prompt.md"
CACHE = _ROOT / "data" / "chart" / "cache"


def load_notes() -> dict[str, str]:
    bundle = json.loads(CHART.read_text(encoding="utf-8"))
    return {n["note_id"]: n["body"] for n in bundle["notes"]}


def load_anchor_findings() -> tuple[dict, dict]:
    """The escalate (H4) + suppress (H_SUPPRESS) anchors, straight from doc 03."""
    blocks = re.findall(
        r"```[a-zA-Z]*\n(.*?)```", DOC03.read_text(encoding="utf-8"), flags=re.DOTALL
    )
    escalate = json.loads(blocks[1])
    suppress = json.loads(blocks[2])
    escalate["finding_id"] = "f_apixaban"
    suppress["finding_id"] = "f_colonoscopy_followup"
    return escalate, suppress


# ---- Signals (what Haiku would extract) — the 5 planted entities ------

SIGNALS = [
    # apixaban (2 events)
    ("n_medrec_d1", 1, "med_recon_gap", "apixaban",
     "Home anticoagulant apixaban for paroxysmal AFib, listed on admission.",
     "apixaban 5 mg twice daily (for paroxysmal atrial fibrillation)"),
    ("n_hold_d1", 1, "med_recon_gap", "apixaban",
     "Apixaban held on admission for the percutaneous drain.",
     "Apixaban held on admission in anticipation of percutaneous drain placement."),
    # pulmonary nodule (1 event)
    ("n_ct_d2", 2, "incidental_finding", "pulmonary_nodule_lll",
     "Incidental 9 mm LLL pulmonary nodule with a Fleischner 3-month CT recommendation.",
     "Incidental 9 mm solid nodule in the left lower lobe at the lung base. "
     "Recommend follow-up chest CT in 3 months to document stability, per "
     "Fleischner Society guidelines."),
    # colonoscopy follow-up (1 event)
    ("n_gi_d4", 4, "consult_recommendation", "colonoscopy_followup",
     "GI recommends outpatient colonoscopy in 6-8 weeks post-diverticulitis.",
     "Given the complicated diverticulitis, recommend outpatient colonoscopy in "
     "6–8 weeks after full recovery to exclude an underlying malignancy or stricture."),
    # blood cultures pending (1 event)
    ("n_micro_d11", 11, "pending_result", "blood_culture_d11",
     "Day 11 blood cultures drawn for a fever spike; result pending.",
     "Blood cultures x2 drawn for temperature to 38.9°C. Result: pending."),
    # creatinine series (5 events)
    ("n_labs_d1", 1, "trend", "creatinine_series", "Creatinine 0.9 (baseline).",
     "Creatinine 0.9 mg/dL"),
    ("n_labs_d3", 3, "trend", "creatinine_series", "Creatinine 1.2 (rising).",
     "Creatinine 1.2 mg/dL"),
    ("n_labs_d5", 5, "trend", "creatinine_series", "Creatinine 1.6 (peak).",
     "Creatinine 1.6 mg/dL"),
    ("n_labs_d8", 8, "trend", "creatinine_series", "Creatinine 1.4 (improving).",
     "Creatinine 1.4 mg/dL"),
    ("n_labs_d12", 12, "trend", "creatinine_series", "Creatinine 1.1 (near baseline).",
     "Creatinine 1.1 mg/dL"),
]


def build_signals() -> list[dict]:
    out = []
    for i, (nid, day, stype, entity, summary, excerpt) in enumerate(SIGNALS):
        out.append(
            {
                "signal_id": f"{nid}-sig-1",
                "source_note_id": nid,
                "day": day,
                "signal_type": stype,
                "entity": entity,
                "summary": summary,
                "verbatim_excerpt": excerpt,
            }
        )
    return out


# ---- Authored H1 / H2 / H3 findings (to the contract) ----------------

H1 = {
    "finding_id": "f_pulmonary_nodule_lll",
    "thread_id": "t_pulmonary_nodule_lll",
    "title": "Incidental 9 mm left-lower-lobe pulmonary nodule reported Day 2 never reaches the discharge follow-up plan",
    "risk": "High",
    "status": "UNCONFIRMED",
    "connection": "The Day 2 CT abdomen/pelvis, obtained for the diverticular abscess, incidentally reported a 9 mm solid nodule at the left lung base with an explicit Fleischner recommendation for a 3-month follow-up chest CT. That recommendation sits in the tail of a radiology impression focused on the abdomen; the Day 14 discharge Follow-up section lists colorectal surgery, PCP, and antibiotics but never mentions the nodule or a chest CT. A single-pass discharge review reasoning forward from the diverticulitis problem would not surface a lung finding buried in an abdominal CT report.",
    "timeline": [
        {"day": 2, "note_type": "radiology_report", "source_note_id": "n_ct_d2",
         "excerpt": "Incidental 9 mm solid nodule in the left lower lobe at the lung base. Recommend follow-up chest CT in 3 months to document stability, per Fleischner Society guidelines.",
         "evidence_kind": "presence"},
        {"day": 14, "note_type": "discharge_summary", "source_note_id": "n_dc_d14",
         "excerpt": "FOLLOW-UP:\n1. Colorectal surgery in 2 weeks for drain site evaluation.\n2. Primary care physician within 1 week.\n3. Complete the remaining oral antibiotic course as prescribed.",
         "evidence_kind": "absence_context"},
    ],
    "question": "Was the incidental 9 mm left-lower-lobe pulmonary nodule intentionally omitted from the discharge plan, or does it need a scheduled 3-month follow-up chest CT and PCP notification per the Fleischner recommendation?",
    "suggested_action": {
        "kind": "addendum", "target": "discharge summary",
        "draft_text": "Add to the discharge Follow-up plan: incidental 9 mm left lower lobe pulmonary nodule noted on the Day 2 CT with a Fleischner recommendation for a follow-up chest CT in 3 months. Schedule the interval chest CT, notify the PCP, and document tracking so the study is completed.",
        "citation_note_id": "n_ct_d2"},
    # 0.94 (matches live Opus, which scored the nodule higher than apixaban) so the
    # clear-cut dropped-Fleischner-rec leads the surfaced list, per clinical review.
    "confidence": 0.94,
}

H2 = {
    "finding_id": "f_blood_culture_d11",
    "thread_id": "t_blood_culture_d11",
    "title": "Blood cultures drawn for the Day 11 fever spike are still pending at discharge with no follow-up plan",
    "risk": "Medium",
    "status": "PENDING_AT_DISCHARGE",
    "connection": "On Day 11 the patient spiked to 38.9°C and two blood cultures were drawn; the microbiology record reads 'pending.' No later note reports a final culture result, and the discharge summary states the fever resolved but never addresses the outstanding cultures or assigns anyone to follow them up. The result is a live microbiology thread leaving the hospital unowned.",
    "timeline": [
        {"day": 11, "note_type": "micro_result", "source_note_id": "n_micro_d11",
         "excerpt": "Blood cultures x2 drawn for temperature to 38.9°C. Result: pending.",
         "evidence_kind": "presence"},
        {"day": 14, "note_type": "discharge_summary", "source_note_id": "n_dc_d14",
         "excerpt": "He had a single fever spike on hospital Day 11 that resolved with continued therapy.",
         "evidence_kind": "absence_context"},
    ],
    "question": "What did the Day 11 blood cultures ultimately grow, and who is responsible for reviewing the finalized result after discharge if they turn positive?",
    "suggested_action": {
        "kind": "pcp_message", "target": "PCP",
        "draft_text": "Two blood cultures drawn on hospital Day 11 for a fever to 38.9°C were still pending at discharge. Please ensure the finalized blood culture result is reviewed; if positive, reassess the need for further evaluation or a change in antibiotic therapy.",
        "citation_note_id": "n_micro_d11"},
    "confidence": 0.85,
}

H3 = {
    "finding_id": "f_creatinine_series",
    "thread_id": "t_creatinine_series",
    "title": "Creatinine rose 0.9 to 1.6 mid-stay and only partially recovered, but no AKI is acknowledged or followed up at discharge",
    "risk": "Medium",
    "status": "UNCONFIRMED",
    "connection": "Serial metabolic panels show creatinine climbing from a Day 1 baseline of 0.9 to a peak of 1.6 on Day 5 (an ~1.8x rise consistent with acute kidney injury) and settling to 1.1 by Day 12 — still above baseline. Each single value looks unremarkable in isolation, so the slope is only visible across the stay. The discharge diagnoses omit acute kidney injury and the Follow-up section arranges no outpatient renal recheck, so the renal trajectory leaves the hospital unacknowledged.",
    "timeline": [
        {"day": 1, "note_type": "lab_result", "source_note_id": "n_labs_d1",
         "excerpt": "Creatinine 0.9 mg/dL", "evidence_kind": "presence"},
        {"day": 5, "note_type": "lab_result", "source_note_id": "n_labs_d5",
         "excerpt": "Creatinine 1.6 mg/dL", "evidence_kind": "presence"},
        {"day": 12, "note_type": "lab_result", "source_note_id": "n_labs_d12",
         "excerpt": "Creatinine 1.1 mg/dL", "evidence_kind": "presence"},
        {"day": 14, "note_type": "discharge_summary", "source_note_id": "n_dc_d14",
         "excerpt": "DISCHARGE DIAGNOSES:\n1. Acute complicated sigmoid diverticulitis with pericolonic abscess, status post CT-guided percutaneous drainage.\n2. Paroxysmal atrial fibrillation (chronic).\n3. Hypertension.\n4. Hyperlipidemia.",
         "evidence_kind": "absence_context"},
    ],
    "question": "Should the mid-stay acute kidney injury (creatinine peak 1.6, not back to the 0.9 baseline at discharge) be documented and an outpatient creatinine recheck arranged with the PCP?",
    "suggested_action": {
        "kind": "pcp_message", "target": "PCP",
        "draft_text": "During admission the patient's creatinine rose from a baseline of 0.9 to 1.6 mg/dL and improved to 1.1 by discharge, still above baseline. This transient acute kidney injury was not documented in the discharge diagnoses. Please recheck a basic metabolic panel at the post-discharge visit to confirm return to baseline.",
        "citation_note_id": "n_labs_d5"},
    "confidence": 0.75,
}


def validate_excerpts(findings: list[dict], signals: list[dict], notes: dict[str, str]) -> None:
    # Every signal excerpt must be an exact substring of its source note.
    for s in signals:
        body = notes[s["source_note_id"]]
        if s["verbatim_excerpt"] not in body:
            raise AssertionError(f"signal excerpt not a substring of {s['source_note_id']}: {s['entity']}")
    # Every timeline excerpt (presence AND absence_context) must be a real substring.
    for f in findings:
        for ev in f["timeline"]:
            body = notes[ev["source_note_id"]]
            if ev["excerpt"] not in body:
                raise AssertionError(
                    f"{f['thread_id']} {ev['evidence_kind']} excerpt not a substring of {ev['source_note_id']}"
                )


def main() -> int:
    notes = load_notes()
    escalate, suppress = load_anchor_findings()
    findings = [escalate, suppress, H1, H2, H3]
    signals = build_signals()

    validate_excerpts(findings, signals, notes)
    # Round-trip through the models to guarantee schema-validity.
    parsed_findings = [Finding.model_validate(f) for f in findings]
    parsed_signals = [ExtractedSignal.model_validate(s) for s in signals]

    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "signals.json").write_text(
        json.dumps([s.model_dump(mode="json") for s in parsed_signals], indent=2), encoding="utf-8"
    )
    (CACHE / "findings.json").write_text(
        json.dumps([f.model_dump(mode="json") for f in parsed_findings], indent=2), encoding="utf-8"
    )
    print(f"Wrote {len(parsed_signals)} signals -> data/chart/cache/signals.json")
    print(f"Wrote {len(parsed_findings)} findings -> data/chart/cache/findings.json")
    print("All signal + timeline excerpts validate as exact substrings. Cache OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
