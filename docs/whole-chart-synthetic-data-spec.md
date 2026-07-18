# Safety Net Whole-Chart — Synthetic Data Spec + Ground Truth

This is the critical path. It pins the **exact strings** for the two live hero threads (so citation validation is deterministic) and the ground-truth manifest (so the eval harness has an oracle). Generate the two heroes verbatim as specified; generate secondaries and filler to guidance.

**Realism bar:** a former Nuance CEO reads this. Dosing, timelines, terminology, and the clinical arc must be plausible. When in doubt, keep it conservative and standard-of-care.

---

## The admission spine

**64-year-old male, admitted Day 1 for acute complicated sigmoid diverticulitis with a pericolonic abscess.** Course: CT abd/pelvis confirms abscess → IR percutaneous drain → IV antibiotics → slow recovery with a fever spike mid-stay and transient renal bump → discharged Day 14 on oral antibiotics. Services involved: hospitalist (primary), interventional radiology, gastroenterology (consult), and radiology. This spine naturally hosts every planted dot.

**Note manifest (~20 notes; author to feel real):**
- Day 1: H&P (hospitalist), medication reconciliation, CT abd/pelvis order + prelim, IR procedure note (drain placement)
- Days 2–13: daily hospitalist progress notes; daily labs (CBC, BMP); nursing notes as filler
- Day 2: CT abd/pelvis final report *(hosts H1)*
- Day 4: GI consult note *(hosts H_SUPPRESS recommendation)*
- Day 5: micro result — abscess fluid culture
- Day 11: fever spike progress note + blood cultures drawn *(hosts H2)*
- Day 14: discharge summary (problem list + med list + Follow-up section), discharge addendum, PCP letter *(host the suppress-closure and the H1/H4 absences)*

---

## PRECOMPUTED (Safety Net bridge) — H1: orphaned incidental (→ UNCONFIRMED / escalate)

**Plant in the Day 2 CT report `body`, exactly:**
> IMPRESSION:
> 1. Acute sigmoid diverticulitis with a 4.2 cm pericolonic abscess, amenable to percutaneous drainage.
> 2. Incidental 9 mm solid nodule in the left lower lobe at the lung base. Recommend follow-up chest CT in 3 months to document stability, per Fleischner Society guidelines.

**Discharge summary Day 14 — Follow-up section, exactly (note the ABSENCE of any nodule/lung item):**
> FOLLOW-UP:
> 1. Colorectal surgery in 2 weeks for drain site evaluation.
> 2. Primary care physician within 1 week.
> 3. Complete the remaining oral antibiotic course as prescribed.

The nodule must appear **nowhere** in the discharge summary, addendum, or PCP letter. Agent cites the CT impression (presence) + the discharge Follow-up section (absence_context).

---

## LIVE HERO — H_SUPPRESS: apparent gap actually closed (→ CONFIRMED_ADDRESSED / suppress)

**Plant in the Day 4 GI consult `body`, exactly:**
> RECOMMENDATIONS:
> Given the complicated diverticulitis, recommend outpatient colonoscopy in 6–8 weeks after full recovery to exclude an underlying malignancy or stricture.

**Do NOT list "colonoscopy" in the discharge summary's structured Follow-up section** (above — it only has surgery / PCP / antibiotics). A naive structured-field check therefore flags the GI rec as dropped.

**Plant the closure in the PCP letter Day 14, exactly (differently worded — the word "colonoscopy" must NOT appear):**
> Please arrange for the patient to undergo lower endoscopy with gastroenterology in approximately two months, once he has recovered from this episode, to evaluate the colon following complicated diverticulitis.

Equivalence the agent must reason through: *lower endoscopy ≈ colonoscopy*, *approximately two months ≈ 6–8 weeks*, *evaluate the colon following complicated diverticulitis ≈ exclude underlying malignancy/stricture*. There is **no lexical overlap on "colonoscopy"**, forcing genuine semantic reasoning. Correct output: `CONFIRMED_ADDRESSED`, cited to the PCP letter → lands in `cleared`, not `findings`.

---

## LIVE HERO (primary escalate) — H4: held anticoagulant never restarted (→ UNCONFIRMED / escalate)

The primary live escalate hero — see the hero-selection rationale in the iteration doc. Highest, most acute stakes; demonstrates cross-domain acknowledgment reasoning that sits outside the radiology-follow-up incumbents' scope and can't be caught by order/recommendation-matching (there is no order or recommendation — only an unclosed loop).

**Med reconciliation Day 1 `body`, include exactly:**
> HOME MEDICATIONS: apixaban 5 mg twice daily (for paroxysmal atrial fibrillation); lisinopril 10 mg daily; atorvastatin 40 mg daily.

**Day 1 procedure/progress note, include exactly:**
> Apixaban held on admission in anticipation of percutaneous drain placement.

**Discharge med list Day 14 — include exactly (apixaban is OMITTED while the other home meds are continued, so the miss reads as oversight, not decision):**
> DISCHARGE MEDICATIONS:
> 1. Ciprofloxacin 500 mg by mouth twice daily to complete a 10-day course.
> 2. Metronidazole 500 mg by mouth three times daily to complete a 10-day course.
> 3. Acetaminophen 650 mg by mouth every 6 hours as needed for pain.
> 4. Continue home lisinopril 10 mg daily and atorvastatin 40 mg daily.

Apixaban must appear **nowhere** in the discharge summary, addendum, or PCP letter. Agent cites the med rec + the hold note (presence) and the discharge med list (absence_context). Restarting apixaban would be the expected loop closure; its absence with no rationale, while the other home meds are continued, = UNCONFIRMED.

**Consistency note:** lisinopril and atorvastatin are continued throughout the stay (not held), so they close cleanly and do not read as additional dropped threads. Only apixaban is held, and only apixaban is dropped.

---

## SECONDARY — H2: blood cultures pending at discharge (→ PENDING_AT_DISCHARGE / escalate)

**Day 11 progress note + micro result, include exactly:**
> Blood cultures x2 drawn for temperature to 38.9°C. Result: pending.

No later result note. Discharge documents do not mention the pending cultures or a follow-up plan. Correct output: `PENDING_AT_DISCHARGE`.

---

## SECONDARY — H3: creatinine trend / unacknowledged AKI (→ UNCONFIRMED / escalate)

**Daily BMP creatinine values, exactly (each individually uncritical; the slope is the signal):**
`Day 1: 0.9 → Day 3: 1.2 → Day 5: 1.6 → Day 8: 1.4 → Day 12: 1.1 mg/dL`

Discharge summary problem list does **not** list AKI and Follow-up does not mention a renal recheck. Correct output: `UNCONFIRMED` (renal trajectory unacknowledged; outpatient recheck not arranged). Optional add: note prophylactic enoxaparin continued at standard dose through the Day 5 Cr 1.6 window for a renal-dosing angle.

---

## Ground-truth manifest (the eval oracle)

The harness scores against this table. `surfaced` is the pass/fail expectation.

| planted_id | entity | note_type carriers | expected status | expected risk | surfaced | live? |
|---|---|---|---|---|---|---|
| H1_nodule | `pulmonary_nodule_lll` | radiology_report(d2) + discharge_summary(d14) | UNCONFIRMED | High | YES | precompute (bridge) |
| H_SUPPRESS_colo | `colonoscopy_followup` | consult_note(d4) + pcp_letter(d14) | CONFIRMED_ADDRESSED | — | **NO (cleared)** | **live** |
| H4_apixaban | `apixaban` | med_reconciliation(d1) + progress(d1) + discharge_summary(d14) | UNCONFIRMED | High | YES | **live (primary escalate)** |
| H2_bcx | `blood_culture_d11` | micro_result(d11) + discharge_summary(d14) | PENDING_AT_DISCHARGE | Medium | YES | precompute |
| H3_aki | `creatinine_series` | lab_result(d1..d12) + discharge_summary(d14) | UNCONFIRMED | Medium | YES | precompute |

**Live-set success gate:** H4 surfaces as UNCONFIRMED/High with valid citations; H_SUPPRESS does NOT surface (CONFIRMED_ADDRESSED, cited to PCP letter); H1 also surfaces (UNCONFIRMED/High) in the full sweep; **precision = 1.0** (zero false positives).

---

## Filler + consistency rules (do not skip — this is what keeps eval interpretable)

1. **Filler must be clean.** Any symptom, abnormal value, or recommendation raised in a filler note MUST be resolved/closed within filler notes. Do not accidentally create unreconciled threads — they become unplanned findings that read as false positives (or unexpected true positives) and corrupt precision/recall.
2. **Internal consistency.** Vitals, labs, abx days, and the diverticulitis arc must cohere across all 14 days. Drain output should trend down; WBC should trend down (except the Day 11 spike); temp normalizes by discharge.
3. **No unintended dots.** Do not plant a second incidental, a second held med, etc., unless it's in the manifest above.
4. **Plausible specifics.** Real drug doses, real timelines (Fleischner 3-month for a 9 mm solid nodule is correct; post-complicated-diverticulitis colonoscopy at 6–8 weeks is correct). A domain expert will check.
5. **The live heroes (H4, H_SUPPRESS) and H1 use their pinned strings verbatim** — do not paraphrase, or citation validation and the suppress-equivalence demo break.
