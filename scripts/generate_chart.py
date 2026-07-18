#!/usr/bin/env python3
"""Generate the 14-day synthetic discharge chart (the whole-chart pivot's long pole).

Authors one coherent admission per ``02-synthetic-data-spec.md``:
64-year-old man, acute complicated sigmoid diverticulitis with a pericolonic
abscess -> CT-guided percutaneous drain -> IV antibiotics -> mid-stay fever
spike + transient creatinine bump -> discharge Day 14 on oral antibiotics.

Five planted dots (the eval oracle): H1 lung nodule, H_SUPPRESS colonoscopy
follow-up, H4 held apixaban, H2 pending blood cultures, H3 creatinine trend.

The two live heroes (H4, H_SUPPRESS) and the H1 bridge use the PINNED verbatim
strings below EXACTLY — paraphrasing them breaks citation validation and the
equivalence demo. Generation self-validates: every pinned string must be an
exact substring of its carrier note, and apixaban / nodule / "colonoscopy"
must appear NOWHERE in the three discharge closure documents.

Emits:
  data/chart/chart.json     the ChartBundle (Note schema)
  data/chart/manifest.json  the GroundTruth oracle (doc 02 manifest)
  data/chart/chart.txt      a human-readable dump
"""

from __future__ import annotations

import datetime as _dt
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from safety_net.models import (  # noqa: E402
    ChartBundle,
    GroundTruth,
    Note,
    NoteType,
    Patient,
    PlantedItem,
    Risk,
    ThreadStatus,
)

CHART_DIR = _ROOT / "data" / "chart"

# ---------------------------------------------------------------------------
# Admission constants
# ---------------------------------------------------------------------------

CHART_ID = "chart_div_4471"
PATIENT_ID = "PT-DIV-4471"
PATIENT_NAME = "Robert Hensley"
AGE = 64
SEX = "male"
ADMIT = _dt.date(2026, 6, 22)  # Day 1
ADMISSION_REASON = "Acute complicated sigmoid diverticulitis with pericolonic abscess"


def d(day: int) -> str:
    """ISO date for a hospital day (Day 1 == admit date)."""
    return (ADMIT + _dt.timedelta(days=day - 1)).isoformat()


def ts(day: int, hhmm: str) -> str:
    return f"{d(day)}T{hhmm}:00"


DISCHARGE_DATE = d(14)

# ===========================================================================
# PINNED VERBATIM STRINGS — copied EXACTLY from 02-synthetic-data-spec.md.
# DO NOT EDIT. En-dash (–) and degree sign (°) are intentional and
# must match the doc-03 few-shot excerpts byte-for-byte.
# ===========================================================================

PIN_H1_CT_IMPRESSION = (
    "IMPRESSION:\n"
    "1. Acute sigmoid diverticulitis with a 4.2 cm pericolonic abscess, "
    "amenable to percutaneous drainage.\n"
    "2. Incidental 9 mm solid nodule in the left lower lobe at the lung base. "
    "Recommend follow-up chest CT in 3 months to document stability, per "
    "Fleischner Society guidelines."
)

PIN_DISCHARGE_FOLLOWUP = (
    "FOLLOW-UP:\n"
    "1. Colorectal surgery in 2 weeks for drain site evaluation.\n"
    "2. Primary care physician within 1 week.\n"
    "3. Complete the remaining oral antibiotic course as prescribed."
)

PIN_SUPPRESS_GI_REC = (
    "RECOMMENDATIONS:\n"
    "Given the complicated diverticulitis, recommend outpatient colonoscopy in "
    "6–8 weeks after full recovery to exclude an underlying malignancy or "
    "stricture."
)

PIN_SUPPRESS_PCP_CLOSURE = (
    "Please arrange for the patient to undergo lower endoscopy with "
    "gastroenterology in approximately two months, once he has recovered from "
    "this episode, to evaluate the colon following complicated diverticulitis."
)

PIN_H4_HOME_MEDS = (
    "HOME MEDICATIONS: apixaban 5 mg twice daily (for paroxysmal atrial "
    "fibrillation); lisinopril 10 mg daily; atorvastatin 40 mg daily."
)

PIN_H4_HOLD = "Apixaban held on admission in anticipation of percutaneous drain placement."

PIN_H4_DISCHARGE_MEDS = (
    "DISCHARGE MEDICATIONS:\n"
    "1. Ciprofloxacin 500 mg by mouth twice daily to complete a 10-day course.\n"
    "2. Metronidazole 500 mg by mouth three times daily to complete a 10-day course.\n"
    "3. Acetaminophen 650 mg by mouth every 6 hours as needed for pain.\n"
    "4. Continue home lisinopril 10 mg daily and atorvastatin 40 mg daily."
)

PIN_H2_BCX = "Blood cultures x2 drawn for temperature to 38.9°C. Result: pending."

# H3 creatinine series (each value individually uncritical; the slope is the signal).
CR = {1: "0.9", 3: "1.2", 5: "1.6", 8: "1.4", 12: "1.1"}


def _bmp_line(day: int, na: str, k: str, cr: str, bun: str, gluc: str) -> str:
    return (
        f"BASIC METABOLIC PANEL (Day {day}):\n"
        f"Sodium {na} mmol/L; Potassium {k} mmol/L; Creatinine {cr} mg/dL; "
        f"BUN {bun} mg/dL; Glucose {gluc} mg/dL."
    )


def _cbc_line(day: int, wbc: str, hgb: str, plt: str) -> str:
    return (
        f"COMPLETE BLOOD COUNT (Day {day}):\n"
        f"WBC {wbc} K/uL; Hemoglobin {hgb} g/dL; Platelets {plt} K/uL."
    )


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


def build_notes() -> list[Note]:
    notes: list[Note] = []

    def add(note_id, day, hhmm, author_role, note_type, body):
        notes.append(
            Note(
                note_id=note_id,
                day=day,
                timestamp=ts(day, hhmm),
                author_role=author_role,
                note_type=note_type,
                body=body,
            )
        )

    # ---- Day 1 -----------------------------------------------------------
    # Admission H&P — no dedicated H&P type in the frozen NoteType vocab, so it
    # is filed as the initial progress_note (the closest allowed type).
    add(
        "n_hp_d1", 1, "08:30", "hospitalist", "progress_note",
        "HISTORY AND PHYSICAL — ADMISSION\n"
        "Hospital Day 1. Hospitalist admission.\n\n"
        "CHIEF COMPLAINT: Left lower quadrant abdominal pain and fever.\n\n"
        "HISTORY OF PRESENT ILLNESS: Mr. Robert Hensley is a 64-year-old man "
        "with a history of paroxysmal atrial fibrillation, hypertension, and "
        "hyperlipidemia who presents with three days of progressive left lower "
        "quadrant pain, subjective fevers, and decreased appetite. He denies "
        "chest pain, shortness of breath, hematochezia, or melena. In the "
        "emergency department he was febrile to 38.6°C with left lower "
        "quadrant tenderness. A CT of the abdomen and pelvis was ordered.\n\n"
        "PAST MEDICAL HISTORY: Paroxysmal atrial fibrillation; hypertension; "
        "hyperlipidemia.\n\n"
        "HOME MEDICATIONS: apixaban, lisinopril, atorvastatin (see medication "
        "reconciliation).\n\n"
        "ASSESSMENT AND PLAN:\n"
        "1. Acute diverticulitis, likely complicated — await CT; start "
        "empiric intravenous antibiotics; interventional radiology as indicated.\n"
        "2. Paroxysmal atrial fibrillation — rate controlled; anticoagulation "
        "addressed in the peri-procedure note given anticipated intervention.\n"
        "3. Hypertension — continue home lisinopril.\n"
        "4. Hyperlipidemia — continue home atorvastatin.",
    )
    add(
        "n_medrec_d1", 1, "09:15", "pharmacist", "med_reconciliation",
        "MEDICATION RECONCILIATION — ADMISSION\n"
        "Completed by pharmacy.\n"
        f"{PIN_H4_HOME_MEDS}\n"
        "Allergies: no known drug allergies.\n"
        "Reconciliation note: Home lisinopril and atorvastatin to be continued "
        "inpatient. Apixaban addressed separately in the peri-procedure holding "
        "note given planned drainage.",
    )
    add(
        "n_hold_d1", 1, "10:00", "hospitalist", "progress_note",
        "PERI-PROCEDURE ANTICOAGULATION NOTE\n"
        "Hospital Day 1.\n"
        f"{PIN_H4_HOLD} Last dose was the evening prior to admission. Mechanical "
        "venous thromboembolism prophylaxis with sequential compression devices "
        "is in place. Anticoagulation to be reassessed after the drainage "
        "procedure.",
    )
    # Preliminary CT read — filed as radiology_report (the final report is d2).
    add(
        "n_radorder_d1", 1, "10:30", "hospitalist", "radiology_report",
        "CT ABDOMEN/PELVIS — ORDER AND PRELIMINARY READ\n"
        "Hospital Day 1.\n"
        "Indication: left lower quadrant pain, fever, leukocytosis; evaluate for "
        "diverticulitis/abscess.\n"
        "PRELIMINARY: Sigmoid diverticulitis with a pericolonic fluid collection "
        "concerning for abscess. Final report to follow. Interventional radiology "
        "consulted for possible drainage.",
    )
    add(
        "n_ir_d1", 1, "14:20", "interventional_radiologist", "procedure_note",
        "INTERVENTIONAL RADIOLOGY — PROCEDURE NOTE\n"
        "Hospital Day 1.\n"
        "Procedure: CT-guided percutaneous catheter drainage of pericolonic "
        "abscess.\n"
        "An 8 French pigtail catheter was placed into the pericolonic collection "
        "under CT guidance. Approximately 45 mL of purulent fluid was aspirated "
        "and sent for culture. The catheter was secured and placed to gravity "
        "drainage. The patient tolerated the procedure well without immediate "
        "complication.",
    )
    add(
        "n_labs_d1", 1, "06:00", "laboratory", "lab_result",
        _cbc_line(1, "15.2", "13.8", "240") + "\n"
        + _bmp_line(1, "137", "4.1", CR[1], "18", "110"),
    )

    # ---- Day 2 -----------------------------------------------------------
    add(
        "n_ct_d2", 2, "11:00", "radiologist", "radiology_report",
        "CT ABDOMEN AND PELVIS WITH CONTRAST — FINAL REPORT\n"
        "Hospital Day 2.\n"
        "HISTORY: Left lower quadrant pain, fever, leukocytosis.\n"
        "TECHNIQUE: Contrast-enhanced CT of the abdomen and pelvis.\n"
        "FINDINGS: Sigmoid diverticulosis with focal wall thickening and "
        "pericolonic fat stranding consistent with acute diverticulitis. There "
        "is a 4.2 cm rim-enhancing pericolonic fluid collection consistent with "
        "an abscess. A percutaneous drainage catheter is in place with the tip "
        "within the collection. No free intraperitoneal air. The liver, spleen, "
        "pancreas, adrenal glands, and kidneys are unremarkable. Visualized lung "
        "bases demonstrate a small nodule as described below.\n"
        f"{PIN_H1_CT_IMPRESSION}",
    )
    add(
        "n_prog_d2", 2, "08:00", "hospitalist", "progress_note",
        "HOSPITALIST PROGRESS NOTE — Hospital Day 2.\n"
        "SUBJECTIVE: Improved pain after drainage. Tolerating clear liquids.\n"
        "OBJECTIVE: Afebrile overnight. Drain with 40 mL serosanguineous-purulent "
        "output. Abdomen soft, less tender.\n"
        "ASSESSMENT/PLAN: Complicated sigmoid diverticulitis, status post "
        "percutaneous drain. Continue intravenous ceftriaxone and metronidazole. "
        "Await final CT read and abscess fluid cultures. Continue home lisinopril "
        "and atorvastatin.",
    )

    # ---- Day 3 -----------------------------------------------------------
    add(
        "n_labs_d3", 3, "06:00", "laboratory", "lab_result",
        _cbc_line(3, "12.8", "13.5", "245") + "\n"
        + _bmp_line(3, "138", "4.0", CR[3], "24", "104"),
    )
    add(
        "n_prog_d3", 3, "08:10", "hospitalist", "progress_note",
        "HOSPITALIST PROGRESS NOTE — Hospital Day 3.\n"
        "SUBJECTIVE: Continued improvement. Pain well controlled.\n"
        "OBJECTIVE: Afebrile. Drain output decreasing (25 mL). Abdomen soft.\n"
        "ASSESSMENT/PLAN: Diverticulitis improving on intravenous antibiotics. "
        "Creatinine mildly up from admission, attributed to reduced oral intake; "
        "encourage fluids. Continue current regimen.",
    )

    # ---- Day 4 -----------------------------------------------------------
    add(
        "n_gi_d4", 4, "13:30", "gastroenterologist", "consult_note",
        "GASTROENTEROLOGY CONSULT NOTE\n"
        "Hospital Day 4.\n"
        "Reason for consult: complicated sigmoid diverticulitis, advise on "
        "management and follow-up.\n"
        "ASSESSMENT: Acute complicated sigmoid diverticulitis with pericolonic "
        "abscess, responding to percutaneous drainage and intravenous "
        "antibiotics. No indication for urgent endoscopy during the acute "
        "inflammatory phase.\n"
        f"{PIN_SUPPRESS_GI_REC}",
    )

    # ---- Day 5 -----------------------------------------------------------
    add(
        "n_labs_d5", 5, "06:00", "laboratory", "lab_result",
        _cbc_line(5, "10.5", "13.4", "250") + "\n"
        + _bmp_line(5, "138", "4.0", CR[5], "30", "100"),
    )
    add(
        "n_micro_d5", 5, "12:00", "microbiology_lab", "micro_result",
        "MICROBIOLOGY — CULTURE RESULT\n"
        "Source: Pericolonic abscess fluid (collected Day 1).\n"
        "GRAM STAIN: Many polymorphonuclear leukocytes; mixed gram-negative rods "
        "and gram-positive cocci.\n"
        "CULTURE: Escherichia coli and Bacteroides fragilis isolated.\n"
        "SUSCEPTIBILITIES: Escherichia coli susceptible to ciprofloxacin. "
        "Bacteroides fragilis susceptible to metronidazole.",
    )
    add(
        "n_prog_d5", 5, "08:05", "hospitalist", "progress_note",
        "HOSPITALIST PROGRESS NOTE — Hospital Day 5.\n"
        "SUBJECTIVE: Feeling better. Appetite returning.\n"
        "OBJECTIVE: Afebrile. Drain output 15 mL. Abdomen benign.\n"
        "ASSESSMENT/PLAN: Abscess fluid culture grew Escherichia coli and "
        "Bacteroides fragilis, both susceptible to the planned oral step-down of "
        "ciprofloxacin and metronidazole; current coverage is appropriate and no "
        "change is needed. Creatinine 1.6 today; likely prerenal from poor intake "
        "— continue intravenous fluids and monitor. Antibiotics do not "
        "require renal dose adjustment at this level.",
    )

    # ---- Day 8 -----------------------------------------------------------
    add(
        "n_labs_d8", 8, "06:00", "laboratory", "lab_result",
        _cbc_line(8, "8.9", "13.3", "255") + "\n"
        + _bmp_line(8, "139", "4.2", CR[8], "25", "98"),
    )
    add(
        "n_prog_d8", 8, "08:15", "hospitalist", "progress_note",
        "HOSPITALIST PROGRESS NOTE — Hospital Day 8.\n"
        "SUBJECTIVE: No complaints. Ambulating in halls.\n"
        "OBJECTIVE: Afebrile. Drain output minimal (8 mL). Abdomen soft, "
        "nontender.\n"
        "ASSESSMENT/PLAN: Diverticulitis resolving. Creatinine improving with "
        "hydration. Plan continued intravenous antibiotics with transition to "
        "oral prior to discharge. Continue home lisinopril and atorvastatin.",
    )

    # ---- Day 11 ----------------------------------------------------------
    add(
        "n_labs_d11", 11, "06:00", "laboratory", "lab_result",
        _cbc_line(11, "13.5", "13.2", "260") + "\n"
        + _bmp_line(11, "138", "4.1", "1.2", "20", "102"),
    )
    add(
        "n_prog_d11", 11, "16:40", "hospitalist", "progress_note",
        "HOSPITALIST PROGRESS NOTE — Hospital Day 11.\n"
        "SUBJECTIVE: Reports feeling warm this afternoon.\n"
        "OBJECTIVE: Temperature spike to 38.9°C. Otherwise hemodynamically "
        "stable. Abdomen soft; drain site clean.\n"
        "ASSESSMENT/PLAN: Single fever spike. Blood cultures drawn; continue "
        "current antibiotics and monitor closely for recurrence.",
    )
    add(
        "n_micro_d11", 11, "17:30", "microbiology_lab", "micro_result",
        "MICROBIOLOGY — PRELIMINARY\n"
        "Source: Blood culture x2 (peripheral).\n"
        f"{PIN_H2_BCX}",
    )

    # ---- Day 12 ----------------------------------------------------------
    add(
        "n_labs_d12", 12, "06:00", "laboratory", "lab_result",
        _cbc_line(12, "9.8", "13.3", "258") + "\n"
        + _bmp_line(12, "139", "4.0", CR[12], "18", "99"),
    )
    add(
        "n_prog_d12", 12, "08:20", "hospitalist", "progress_note",
        "HOSPITALIST PROGRESS NOTE — Hospital Day 12.\n"
        "SUBJECTIVE: Feels back to baseline. No recurrent fevers.\n"
        "OBJECTIVE: Afebrile for 24 hours. White count normalized. Drain output "
        "negligible; interventional radiology to remove catheter today.\n"
        "ASSESSMENT/PLAN: Clinically recovered. Transition to oral antibiotics "
        "planned. Anticipate discharge in the next 1–2 days.",
    )

    # ---- Day 13 ----------------------------------------------------------
    add(
        "n_prog_d13", 13, "08:25", "hospitalist", "progress_note",
        "HOSPITALIST PROGRESS NOTE — Hospital Day 13.\n"
        "SUBJECTIVE: No complaints. Eating well, ambulating independently.\n"
        "OBJECTIVE: Afebrile. Drain removed yesterday; site clean and dry.\n"
        "ASSESSMENT/PLAN: Transitioned to oral ciprofloxacin and metronidazole "
        "and tolerating. Plan discharge tomorrow with outpatient follow-up. "
        "Continue home lisinopril and atorvastatin.",
    )

    # ---- Day 14 (discharge) ---------------------------------------------
    add(
        "n_dc_d14", 14, "11:00", "hospitalist", "discharge_summary",
        "DISCHARGE SUMMARY\n"
        f"Patient: {PATIENT_NAME}    MRN: {PATIENT_ID}\n"
        f"Admitted: {d(1)}    Discharged: {d(14)}\n\n"
        "DISCHARGE DIAGNOSES:\n"
        "1. Acute complicated sigmoid diverticulitis with pericolonic abscess, "
        "status post CT-guided percutaneous drainage.\n"
        "2. Paroxysmal atrial fibrillation (chronic).\n"
        "3. Hypertension.\n"
        "4. Hyperlipidemia.\n\n"
        "HOSPITAL COURSE:\n"
        "Mr. Hensley is a 64-year-old man who presented with left lower quadrant "
        "pain and fever and was found to have acute sigmoid diverticulitis with a "
        "4.2 cm pericolonic abscess. Interventional radiology placed a "
        "percutaneous drain on Day 1 with return of purulent fluid. He was "
        "treated with intravenous antibiotics with gradual clinical improvement; "
        "abscess fluid culture grew enteric flora susceptible to the chosen "
        "regimen, and coverage was confirmed appropriate. He had a single fever "
        "spike on hospital Day 11 that resolved with continued therapy. The drain "
        "was removed once output was minimal. He tolerated a regular diet and was "
        "ambulating independently at discharge. He is discharged in stable "
        "condition to complete an oral antibiotic course.\n\n"
        f"{PIN_H4_DISCHARGE_MEDS}\n\n"
        f"{PIN_DISCHARGE_FOLLOWUP}",
    )
    add(
        "n_add_d14", 14, "11:30", "hospitalist", "discharge_addendum",
        "DISCHARGE SUMMARY — ADDENDUM\n"
        "Clarification regarding the hospital course: the percutaneous drain was "
        "removed on hospital Day 12 after output fell below 10 mL over 24 hours "
        "and a repeat limited ultrasound showed near-complete resolution of the "
        "collection. The Day 11 temperature elevation resolved without recurrence, "
        "and the patient remained afebrile for 48 hours prior to discharge.",
    )
    add(
        "n_pcp_d14", 14, "12:00", "hospitalist", "pcp_letter",
        "Dear Doctor,\n\n"
        "Thank you for your continued care of Mr. Robert Hensley, a 64-year-old "
        "man discharged today following a two-week admission for acute "
        "complicated sigmoid diverticulitis with a pericolonic abscess. His "
        "course was managed with CT-guided percutaneous drainage and intravenous "
        "antibiotics, transitioning to an oral regimen at discharge "
        "(ciprofloxacin and metronidazole to complete a 10-day course). He "
        "improved steadily and was afebrile and tolerating a regular diet at "
        "discharge.\n\n"
        "Please see him in your office within one week to review his recovery and "
        "antibiotic course. He will also follow up with colorectal surgery in two "
        "weeks for drain site evaluation.\n\n"
        f"{PIN_SUPPRESS_PCP_CLOSURE}\n\n"
        "His home lisinopril and atorvastatin were continued without change. "
        "Please continue to manage his blood pressure and lipids as an "
        "outpatient.\n\n"
        "Warm regards,\n"
        "Hospitalist Service",
    )

    return notes


# ---------------------------------------------------------------------------
# Ground-truth manifest (doc 02)
# ---------------------------------------------------------------------------


def build_manifest() -> GroundTruth:
    return GroundTruth(
        chart_id=CHART_ID,
        items=[
            PlantedItem(
                planted_id="H1_nodule", entity="pulmonary_nodule_lll",
                note_types=["radiology_report", "discharge_summary"],
                expected_status=ThreadStatus.UNCONFIRMED, expected_risk=Risk.HIGH,
                surfaced=True, live="precompute",
            ),
            PlantedItem(
                planted_id="H_SUPPRESS_colo", entity="colonoscopy_followup",
                note_types=["consult_note", "pcp_letter"],
                expected_status=ThreadStatus.CONFIRMED_ADDRESSED, expected_risk=None,
                surfaced=False, live="live",
            ),
            PlantedItem(
                planted_id="H4_apixaban", entity="apixaban",
                note_types=["med_reconciliation", "progress_note", "discharge_summary"],
                expected_status=ThreadStatus.UNCONFIRMED, expected_risk=Risk.HIGH,
                surfaced=True, live="live",
            ),
            PlantedItem(
                planted_id="H2_bcx", entity="blood_culture_d11",
                note_types=["micro_result", "discharge_summary"],
                expected_status=ThreadStatus.PENDING_AT_DISCHARGE, expected_risk=Risk.MEDIUM,
                surfaced=True, live="precompute",
            ),
            PlantedItem(
                planted_id="H3_aki", entity="creatinine_series",
                note_types=["lab_result", "discharge_summary"],
                expected_status=ThreadStatus.UNCONFIRMED, expected_risk=Risk.MEDIUM,
                surfaced=True, live="precompute",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Validation — generation fails loudly on any drift
# ---------------------------------------------------------------------------

FORBIDDEN_IN_DISCHARGE = {
    "apixaban (H4 absence)": ["apixaban"],
    "nodule (H1 absence)": ["nodule", "lung", "pulmonary", "fleischner"],
    "colonoscopy (H_SUPPRESS equivalence)": ["colonoscopy"],
}


def validate(bundle: ChartBundle) -> None:
    by_id = {n.note_id: n for n in bundle.notes}

    def _in(note_id: str, pin: str, label: str) -> None:
        body = by_id[note_id].body
        if pin not in body:
            raise AssertionError(f"PINNED STRING MISSING in {note_id}: {label}")

    _in("n_ct_d2", PIN_H1_CT_IMPRESSION, "H1 CT impression")
    _in("n_dc_d14", PIN_DISCHARGE_FOLLOWUP, "discharge follow-up")
    _in("n_dc_d14", PIN_H4_DISCHARGE_MEDS, "H4 discharge meds")
    _in("n_gi_d4", PIN_SUPPRESS_GI_REC, "H_SUPPRESS GI rec")
    _in("n_pcp_d14", PIN_SUPPRESS_PCP_CLOSURE, "H_SUPPRESS PCP closure")
    _in("n_medrec_d1", PIN_H4_HOME_MEDS, "H4 home meds")
    _in("n_hold_d1", PIN_H4_HOLD, "H4 hold")
    _in("n_micro_d11", PIN_H2_BCX, "H2 blood cultures pending")

    # Creatinine series present in the lab notes.
    for day, val in CR.items():
        nid = f"n_labs_d{day}"
        if f"Creatinine {val} mg/dL" not in by_id[nid].body:
            raise AssertionError(f"Creatinine {val} missing from {nid}")

    # Forbidden strings must appear NOWHERE in the three closure documents.
    discharge_ids = ["n_dc_d14", "n_add_d14", "n_pcp_d14"]
    for nid in discharge_ids:
        low = by_id[nid].body.lower()
        for label, words in FORBIDDEN_IN_DISCHARGE.items():
            for w in words:
                if w in low:
                    raise AssertionError(
                        f"FORBIDDEN word {w!r} ({label}) found in {nid}"
                    )

    # The PCP letter closes the colonoscopy loop WITHOUT the word "colonoscopy".
    if "colonoscopy" in by_id["n_pcp_d14"].body.lower():
        raise AssertionError("PCP letter must not contain the word 'colonoscopy'")


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------


def human_dump(bundle: ChartBundle) -> str:
    p = bundle.patient
    lines = [
        f"CHART {bundle.chart_id} — {p.name} "
        f"({p.age}{p.sex[0].upper()}), {p.admission_reason}",
        f"Day {p.admit_day} ({d(1)}) — Day {p.discharge_day} ({DISCHARGE_DATE})  "
        f"({len(bundle.notes)} notes)",
        "=" * 78,
    ]
    for n in bundle.notes:
        lines.append("")
        lines.append(f"[{n.note_id}] Day {n.day}  {n.timestamp}  "
                     f"{n.note_type} / {n.author_role}")
        lines.append("-" * 78)
        lines.append(n.body)
    return "\n".join(lines) + "\n"


def main() -> int:
    bundle = ChartBundle(
        chart_id=CHART_ID,
        patient=Patient(
            age=AGE,
            sex=SEX,
            admit_day=1,
            discharge_day=14,
            patient_id=PATIENT_ID,
            name=PATIENT_NAME,
            admission_reason=ADMISSION_REASON,
        ),
        notes=build_notes(),
    )
    validate(bundle)
    manifest = build_manifest()

    CHART_DIR.mkdir(parents=True, exist_ok=True)
    (CHART_DIR / "chart.json").write_text(
        bundle.model_dump_json(indent=2), encoding="utf-8"
    )
    (CHART_DIR / "manifest.json").write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8"
    )
    (CHART_DIR / "chart.txt").write_text(human_dump(bundle), encoding="utf-8")

    print(f"Wrote {len(bundle.notes)} notes -> data/chart/chart.json")
    print(f"Wrote {len(manifest.items)} planted items -> data/chart/manifest.json")
    print("Wrote human dump -> data/chart/chart.txt")
    print("All pinned strings present; all forbidden strings absent. Validation OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
