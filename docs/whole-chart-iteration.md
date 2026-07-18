# Safety Net — Whole-Chart Review

**Evolution of Safety Net: from single-thread reconciliation to whole-chart dot-connecting at a critical moment.**

The name still fits (we catch what falls through). The reconciliation engine, evidence-grounding, action-drafting, and MCP wrapper carry over unchanged. This doc covers only what's new: the workflow, the signal taxonomy, the output contract, the demo, and the build.

**Critical moment (assumption):** hospital **discharge** from a 14-day admission. Most defensible — high cognitive load, time pressure, and the outpatient handoff is where threads die. Swappable for ICU transfer or a mid-stay checkpoint with minimal change.

**Reuse vs. new (DQ-safe: everything shown was built during the event):**

| Reused from Safety Net | Genuinely new |
|---|---|
| Haiku bulk extraction | Widened signal taxonomy (extraction schema) |
| Opus reconciliation engine | Entity-threading + temporal index (deterministic code) |
| Verbatim-citation validation | 14-day synthetic chart (the long pole) |
| Action drafting (human-approved) | Precision-tuned whole-chart reasoning prompt |
| Thin FastMCP wrapper (off demo path) | — |
| Reasoning-first UI shell | — |

The marginal engineering is modest. The risk is **data authoring and precision tuning**, not code.

---

## 1. Problem statement

Care on a multi-week admission is delivered by many specialists across time, each with a narrow view and a narrow window of attention. The chart accumulates signals faster than any one clinician integrates them. At the critical transition — discharge — the person writing the summary reasons *forward* from the active problem list, not *backward* across every note, result, consult, and med change from the whole stay.

So signals fall through. Not because anyone erred, but because **no one's job is to read the entire chart with equal attention at the moment it matters.** Three failure modes:

- **Orphaned findings** — something documented in one note (an imaging incidental, a passing path result) that belongs to a domain outside the discharging clinician's focus and never reaches the plan.
- **Trend-only signals** — each daily value is individually unremarkable; only the slope across days is dangerous (evolving AKI, occult bleed).
- **Dropped threads** — a consult recommendation, a held home med, a pending culture, a "will reassess" that no later note ever closes.

**What agents make newly possible:** an agent can read every note, result, order, med change, and consult across all 14 days with uniform attention and no specialty bias, at exactly the decision point, and reason about relationships between signals separated by days and domains. No human does this. It is not automating a workflow — it is a net-new safety layer that only exists because full-chart review at a decision point is now cheap.

**Relationship to Safety Net:** Safety Net was single-thread and retrospective (one recommendation → was it acted on). This is cross-domain and temporal at a live decision point (many uncoordinated signals → which are unreconciled at discharge). Safety Net is a special case of this.

**Demo line:** *"No clinician reads 14 days of chart end-to-end at discharge. We do — every note, every domain, every day — and we only speak up when a thread genuinely fell through, with the receipt."*
**Close line:** *"The chart had the answer the whole time. No one had read all of it. Now something has."*

---

## 2. Signal checklist — what the agent scans for across the full record

The agent does not flag *existence*. For every candidate it reasons: **is this reconciled/addressed by the discharge plan or a later note? If not, is the miss clinically meaningful? If yes → escalate with a specific question.**

**A. Orphaned incidental / secondary findings**
- Imaging incidentals in a report body, not on the problem list (lung/thyroid/adrenal nodule, incidental aneurysm, incidental mass).
- Pathology or cytology findings noted in passing.

**B. Results in limbo at discharge**
- Cultures pending (blood, urine, sputum, wound) with no documented follow-up plan.
- Pathology/cytology pending.
- Sensitivities that resulted *after* empiric therapy was chosen — was therapy narrowed/adjusted? (stewardship)
- Studies or consults ordered but not completed before discharge.

**C. Trends visible only across time (point-normal, trend-abnormal)**
- Rising creatinine / falling GFR (evolving AKI).
- Drifting sodium, potassium, calcium.
- Downtrending hemoglobin (occult bleed) — each drop "not critical," the slope is.
- Late-stay rising WBC or lactate (brewing infection).
- Net fluid balance / weight trend (volume overload).
- Recurrent low-grade fevers.

**D. Medication reconciliation gaps**
- Inpatient-transient med (PPI, steroid, benzo, antipsychotic for delirium) silently carried onto the discharge list as chronic — prescribing cascade.
- Home med held for a procedure/bleed and never restarted (anticoagulant, beta-blocker, antihypertensive).
- Duplicate therapy across services (two agents, same class).
- Renally-cleared med not adjusted after renal function changed.
- New med needing monitoring (level, lab) with no plan.

**E. Consultant recommendations not closed**
- A consult rec ("outpatient TTE in 6 weeks," "GI follow-up for the polyp," "repeat imaging in 3 months") that never reaches the discharge plan.
- Consult signed off with a conditional/pending item.

**F. Dropped symptom / assessment threads**
- A symptom documented early (chest pain, syncope, new neuro complaint) attributed and never fully worked up.
- A "will monitor / will reassess" where the reassessment never happened.

**G. Cross-domain interactions**
- A new diagnosis in one domain that changes risk in another (new AFib → anticoagulation decision; new diabetes → med + follow-up implications).
- Procedure/med interactions (anticoagulation started before a planned procedure; contrast given as renal function worsened).

**H. Care-continuity / disposition gaps**
- Follow-up appointment recommended but not scheduled/documented.
- Time-sensitive follow-up with no mechanism to ensure it happens (the original Safety Net thread, now one signal among many).

**I. Documentation contradictions**
- Discharge problem list omits a problem active throughout progress notes.
- Allergy contradicted by a med given.
- One note says "resolved," another says "active."

---

## 3. "Connect the dots" output format

Reasoning-first, ranked, and **sparse** — this is where we either respect or violate the dashboard anti-project. Extends the frozen Safety Net JSON contract.

**Per finding:**
- **`title`** — one line naming the dot ("Incidental 9 mm lung nodule reported Day 3, never surfaced in discharge plan").
- **`risk`** — High / Medium / Low, scored on **consequence of the miss**, not finding severity alone. (A benign-looking nodule that needs tracking can be High because the miss breaks continuity; a documented-and-addressed critical finding is not surfaced at all.)
- **`connection`** — the reasoning: which ≥2 events across time/domain connect, and why no single view catches it. **This is the hero content the demo dwells on.**
- **`timeline`** — the ordered events that constitute the thread, each with: `day`, `note_type`, `source_id`, and a **verbatim excerpt** (the anti-hallucination anchor). E.g., Day 3 CT report excerpt → Day 14 discharge problem-list excerpt showing absence.
- **`status`** — `CONFIRMED_ADDRESSED` / `UNCONFIRMED` / `CONTRADICTED` / `PENDING_AT_DISCHARGE` (extends the Safety Net enum).
- **`question`** — the specific, human-answerable escalation ("Was the 9 mm nodule intentionally omitted, or does it need a 3-month follow-up CT and a scheduled appointment?"). Never "review the chart."
- **`suggested_action`** — the draftable artifact (addendum line, PCP message, order text). One gets human-approved live.
- **`confidence`** — 0–1, with the abstain threshold applied downstream.

**Top level:**
- **`summary`** — one line ("3 unreconciled threads across a 14-day stay"). This is the **2-second bookend**, not a dashboard.
- **`findings`** — ranked by `risk × confidence`, hard-capped at top N.
- **`cleared`** — what was considered and correctly suppressed, collapsed by default (surfaced only in Q&A — it's the noise-discipline proof).

The demo shows the summary for 2 seconds, then opens **one** finding's `connection` + `timeline` + `question`, then human-approves **one** `suggested_action`.

---

## 4. Demo hypotheses — the planted dots

Each is authored into the synthetic chart with known ground truth. Format: *what's in the chart → what a single-pass discharge view sees → what the agent connects.* **H4 (held anticoagulant) is the primary live hero; H_SUPPRESS is the mandatory second hero (proves precision); H1 stays in the sweep as the Safety Net bridge.** The rest are sweep depth and the Q&A bench.

**H1 — orphaned incidental (looks closed, isn't) — now precomputed sweep depth + Safety Net bridge.**
Admitted Day 1 for an unrelated problem (e.g., cellulitis or GI bleed). Day 3 CT abdomen/pelvis for abdominal pain; impression tail notes "incidental 9 mm pulmonary nodule at the lung base — recommend follow-up chest CT in 3 months." The admission focus resolves; Day 14 discharge problem list and follow-up section never mention it. *Single pass:* clean discharge. *Agent:* connects Day 3 report tail → absence in Day 14 plan → escalates (needs tracked 3-month CT + scheduled appointment + PCP notification). Cleanest, most legible *escalate* case — which is exactly why it's the sweep-depth bridge, not the headline (see Hero selection below): it rhymes with the original Safety Net thread and lands on the incumbent's home turf.

**H_SUPPRESS — HERO: apparent gap actually closed (looks open, is closed).**
An incidental or consult rec appears absent from the structured discharge problem list — **but** a discharge addendum or the PCP letter addresses it in different wording. *Naive keyword matching:* flags it as dropped (false positive). *Agent:* reads the addendum, recognizes semantic equivalence, **suppresses**, and cites where it was addressed. This is the false-positive-suppression proof and the direct answer to Ricci's "how is this not a keyword checker?"

**H2 — pending culture / stewardship gap.**
Day 10 blood culture drawn, empiric broad-spectrum started. Day 12 sensitivities show a narrow agent would cover it — OR the culture is still pending at discharge with no follow-up. Day 14 continues the broad regimen with no de-escalation note. *Single pass:* a reasonable-looking med list. *Agent:* micro-result timeline → discharge regimen → flags stewardship gap or pending-result-in-limbo. (Antimicrobial stewardship is a first-tier safety domain for a Nuance-era judge.)

**H3 — trend-only AKI + renal dosing.**
Creatinine 0.9 → 1.1 → 1.3 → 1.6 (Day 11) → partial improvement, no single value flagged critical. A renally-cleared med started Day 8 at standard dose was never adjusted through the worst window. *Single pass:* last value near-normal, nothing flagged. *Agent:* sees the slope + the med interaction → escalates.

**H4 — PRIMARY LIVE HERO: held anticoagulant never restarted (looks reconciled, isn't).**
Home apixaban (for paroxysmal AFib) held Day 1 for the percutaneous drain, never restarted; the discharge med list continues the other home meds but omits apixaban with no rationale — the patient goes home off stroke prevention. *Single pass:* a plausible-looking med list. *Agent:* admission med rec (Day 1) → held for procedure (Day 1) → absent at discharge, other home meds continued → escalates. This is the strongest live hero: it demonstrates the *new* cross-temporal, cross-domain capability (three documents across the stay), it sits entirely outside the radiology-follow-up incumbents' scope, and it can't be caught by order/recommendation-matching because there's no order or recommendation to match — only an unclosed loop. Highest, most acute stakes of the set.

**H5 — prescribing cascade.**
PPI / antipsychotic-for-delirium / steroid started for a transient reason, carried onto the discharge list as chronic, no taper or stop plan. *Single pass:* a plausible chronic med. *Agent:* transient start-indication → indefinite discharge continuation → flags for deprescribing.

**H6 — consultant recommendation dropped.**
Cardiology (or GI) consult Day 6 recommends "outpatient TTE in 6 weeks and cardiology follow-up" (or "GI follow-up / repeat colonoscopy for the incidental polyp"). Discharge plan doesn't carry it. *Single pass:* discharge summary looks complete. *Agent:* consult recommendation → absence in discharge follow-up → escalates. Explicit cross-specialty dot-connecting.

**H7 — downtrending hemoglobin / occult bleed.**
Hgb 11.5 → 10.8 → 10.1 → 9.4 across the stay, no single critical flag, no documented workup — possibly with an early melena mention that was attributed and dropped. *Single pass:* last value not alarming. *Agent:* slope + dropped symptom thread → flags outpatient GI workup + repeat CBC. Trend + dropped-thread combo.

**H8 — contradiction + missing cross-domain decision.**
New-onset AFib diagnosed Day 5, on the problem list in daily notes, missing from the discharge summary problem list — and the anticoagulation decision is never addressed. *Single pass:* discharge summary reads clean. *Agent:* documentation contradiction + unaddressed stroke-prevention decision (rhythm dx → anticoagulation) → escalates. High-stakes and very legible; strong secondary if H1 needs a swap.

**Hero selection (decided): H4 is the primary live escalate hero, not H1.** H1 (the orphaned nodule) is essentially the original Safety Net thread — a single dropped radiology-follow-up recommendation — so it shows the *old* capability on a bigger chart and lands on the exact turf Nuance's PowerScribe Follow-up Manager was built for; leading with it invites a "we already do that" from Ricci. H4 shows the *pivot's actual point*: cross-domain acknowledgment reasoning an order-matcher can't do (no order or recommendation to match — only an unclosed loop), with higher and more acute stakes (stroke prevention). H1 stays in the sweep as the deliberate "everything Safety Net did, plus more" bridge and a Q&A proof point.

**Trade-off:** H1 is marginally more instantly legible (no clinical-context beat). Mitigation: one sentence closes the gap — *"He came in on a blood thinner for his atrial fibrillation; it was held for his procedure and never restarted; he's going home unprotected and nothing flags it"* — which is arguably *more* visceral than a lung nodule for a lay round-1 panel.

**Recommended live set:** H4 (escalate) + H_SUPPRESS (suppress) + one human-approved action on H4 (approve clarifying/restarting apixaban). Precompute H1 (bridge) + H2/H3 as the visible sweep depth.

---

## 5. Evaluation criteria for the demo

**Success looks like:**
- Surfaces the hero dot(s) a single-pass discharge review misses, each with correct status and verbatim evidence.
- Correctly **suppresses** the look-alike (zero false positive on the addressed item).
- Every claim backed by a real excerpt (zero fabricated citations).
- Escalation questions are specific and human-answerable.
- Ranked and sparse (2–4 findings) — passes the "is this a dashboard?" test.

**How to judge usefulness/accuracy (mini ground truth):**
Because the data is hand-authored, the planted dots *are* ground truth. Score:
- **Precision** (surfaced findings that are real planted dots vs. noise) — **weight this highest; a false positive in front of Ricci is fatal.**
- **Recall** (planted dots surfaced) — secondary; a miss on a non-hero dot is survivable.
- **Evidence fidelity** — every citation must be a verbatim substring of a source note (automated substring check). Any non-match = hallucination = hard fail.
- **Status correctness** — CONFIRMED / UNCONFIRMED / PENDING / CONTRADICTED assigned correctly per planted item.
- **Actionability** — can a human answer the question without re-reading the whole chart.

**What to log (also the reliability exhibit for Ricci):**
- Per run: model + version, chart id, context size / token counts, per-stage latency (index, reason, draft).
- Per finding: raw model output, assigned status, confidence, citations + automated verbatim-match result (pass/fail), TP/FP/FN vs. ground truth.
- **Suppression events:** what was considered and cleared, and the equivalence reasoning trace — gold for Q&A.
- Abstentions and their trigger.
- A precision/recall summary line per run.

---

## 6. Edge cases and guardrails

- **False positives (top risk).** Precision-over-recall posture in the prompt; require ≥2 corroborating excerpts for any High-risk escalation; the suppress hero proves discipline; abstain below a confidence threshold rather than surface.
- **Missing context / closed-world assumption.** The agent sees only the provided chart. It must not assume anything not in evidence. If an item might be addressed somewhere not provided ("may be in an outside record"), it flags **UNCONFIRMED with a question**, never a definitive miss. State this assumption out loud in the demo.
- **Hallucination prevention via evidence quoting.** Every finding requires ≥1 verbatim excerpt, **automatically validated as a substring of a real source note before it enters the output.** Non-matching citations → finding dropped/suppressed. Same mechanism as Safety Net. The model reasons about **document equivalence, not clinical truth** — it never diagnoses.
- **When to abstain.** Below confidence threshold; when evidence is ambiguous/contradictory beyond resolution; when the "connection" needs clinical judgment beyond documentation reconciliation (e.g., "should this patient be anticoagulated?" → the agent flags the *unaddressed decision* and asks the human, it does not make the call).
- **Over-surfacing / noise.** Hard cap on findings shown (top N by risk × confidence); the rest collapse into `cleared`. The cap enforces the anti-dashboard discipline structurally, not by hope.
- **Severity miscalibration.** Risk = consequence of the miss, not finding severity alone.
- **Temporal correctness.** Never flag "pending at discharge" if a later-dated note resolves it. The index must respect timestamps; event ordering is load-bearing.
- **Scope creep into diagnosis.** Hard guardrail: the agent reconciles documentation and asks questions. It does not diagnose, prescribe, or decide. Say this in the demo — it is the Ricci-facing reliability answer.

---

## 7. Build plan — end to end

Framed as extending the existing engine. Dependencies and critical path called out.

**Step 0 — Fallback posture (5 min).** Keep Safety Net runnable as graceful-degradation. Branch, don't overwrite.

**Step 1 — Synthetic 14-day chart (CRITICAL PATH — start first, strongest writer).** Author one coherent admission with **H4** (primary hero) and **H_SUPPRESS** planted live, plus **H1** and believable filler (daily progress notes, labs, 1–2 consults, meds, imaging) so the chart reads real. Optionally plant H2/H3 for depth. Keep it internally consistent — a domain expert will check. **Freeze the note/event schema (extend the frozen JSON contract) in the first 15 minutes so Steps 2–8 parallelize.** Each note: `day`, `timestamp`, `author_role`, `note_type`, `body`.

**Step 2 — Chart indexing / ingestion (reuse extraction).** Load notes into a normalized event list. Use **Haiku** for bulk structured extraction of atomic events/results/meds/recommendations per note — reuse the Safety Net extractor, widen the schema from "recommendations" to "signals." Output: typed events with source pointers.

**Step 3 — Timeline reconstruction (NEW, small, deterministic).** Sort events by timestamp; group into threads by entity (this nodule, this med, this culture, this creatinine series); link earlier events to later events referencing the same entity. Lightweight entity-grouping + temporal sort — **not** a knowledge graph. Keep it in code, not LLM, for reliability.

**Step 4 — Reasoning (Opus — the hero, reuse reconciliation engine).** Per thread, Opus reasons whether it's reconciled/addressed by discharge. Extend the five-axis reconciliation to threads (acknowledged / addressed in plan / contradicted / pending). Opus returns status + confidence + verbatim excerpts + the specific question. Inputs: the thread's events + the discharge summary + relevant plan sections. Precision posture in the prompt.

**Step 5 — Evidence grounding / validation (reuse + automate).** Validate every citation is a verbatim substring of a real source note; drop/suppress the unvalidated. Rank by risk × confidence; apply the top-N cap and abstain threshold.

**Step 6 — Action drafting (reuse).** For the human-approved demo action on H4 (clarify/restart apixaban), Opus drafts the concrete artifact (addendum / med-rec correction) with citation. Human approves live.

**Step 7 — MCP wrapper (reuse).** Expose sweep + reconcile as thin FastMCP tools, **off the live demo path** — same decision as Safety Net. MCP is the credibility exhibit; the UI calls core Python directly on stage.

**Step 8 — Minimal UI / output (reuse shell).** Reasoning-first: ranked findings as a 2-second bookend, then click into the hero — timeline with excerpts, status, question, draftable action. **Not a dashboard.**

**Step 9 — Precompute the sweep.** Reconcile the two heroes live; precompute the rest for determinism on stage.

**Step 10 — Rehearse + Q&A.** 60-second video cut. Ricci answers: precision/noise (suppress hero + top-N cap); false-negatives (escalate-don't-close makes misses visible); LLM reliability (verbatim citation + document-equivalence-not-diagnosis); and the new one — **"why isn't this just a problem-list checker?"** → because it reasons about acknowledgment and equivalence *across time and domain* and correctly suppresses look-alikes, which a checker cannot.

**Critical path:** Step 1 (data) is the long pole and gates Steps 2–6; freeze its schema in the first 15 minutes so everything downstream builds in parallel against the contract. The only new code is Step 3 + widened schemas — small. The real work is data authoring and prompt precision tuning.
