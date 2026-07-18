# Safety Net — Reconciliation Agent: Build Spec & Demo Beat

## The wedge (why this wins)
Incumbents (Rad AI Continuity, Inflo Health, Nuance PowerScribe Follow-up Manager) **match orders and track appointments**: "was a chest CT done?" Safety Net reasons about **clinical equivalence and acknowledgment**: "was the nodule actually re-evaluated?" The gap between those two questions is the entire failure mode — and it's LLM-suited reasoning, not order-matching. That's the originality story, and it's aimed straight at Ricci.

## The reconciliation reasoning loop
Each stage is a visible MCP tool call so the agentic, multi-step nature is legible to judges.

1. **Extract (Haiku, bulk, cheap).** From every report, produce `recommendation` objects {finding, anatomic_site, recommended_modality, timeframe, urgency_tier, source_id/date} and `study` objects {modality, anatomic_coverage, date, impression_text}. This part is commoditized — keep it fast.
2. **Candidate match (cheap).** For each open recommendation, pull later studies with anatomic overlap within/near the window. Narrows the search space.
3. **Reconcile (Opus — the hero).** For each recommendation × candidate study, reason across five explicit axes:
   - **Modality adequacy** — is the study's modality sufficient/superior for *this finding*? (CT satisfies a nodule follow-up; CXR doesn't; PET/CT exceeds.) LLM clinical knowledge beats hard-coded rules here.
   - **Anatomic coverage** — did it actually image the target? (CT abdomen ≠ chest nodule.)
   - **Finding acknowledgment** — did the later report *address* the finding (measured / "stable" / "resolved" / "not seen")? Silence = weak/no evidence of true follow-up. **This is the crux.**
   - **Temporal adequacy** — within/near the recommended window? on-time / late / never.
   - **Terminal events** — any explicit closure: resolution, benign characterization, biopsy result, or a documented decision not to pursue.
   Output per pair: verdict ∈ {SATISFIES, SUPERSEDES, PARTIAL, UNCONFIRMED, INADEQUATE, NO_EVIDENCE} + **cited evidence spans** + confidence. `UNCONFIRMED` (a capable later study that never acknowledges the finding) is the escalation verdict — the crux of the demo.
4. **Resolve state.** Aggregate the per-pair verdicts into one closure-state (below).
5. **Draft action (human-in-loop).** For genuinely open/overdue findings: draft the outreach/order, a human approves, an audit entry is written. No autonomous action.

## Closure-state mapping
Emitted closure states: `completed / superseded / declined / overrode / open_overdue / escalate`. (`open` / `scheduled` are upstream lifecycle states from order/appointment data, not emitted by the reconciliation engine.)
- High-confidence SATISFIES/SUPERSEDES → completed / superseded.
- Documented decline/override → declined / overrode.
- PARTIAL/INADEQUATE, or NO_EVIDENCE past the window → **open + overdue**.
- Low-confidence or conflicting evidence, or no acknowledgment of the finding → verdict `UNCONFIRMED` → **escalate**.

## The escalation rule = your thesis (and your false-negative answer)
The agent **never silently closes on ambiguous evidence.** It emits `UNCONFIRMED` (→ `escalate`) with the specific human question, e.g.: *"Feb-2025 CT chest exists but never mentions the nodule — was it reassessed? Confirm / Deny."* Misses become **visible**, not lost. This reframes "what's your recall?" from a weakness into the point: the job isn't perfect extraction, it's converting an invisible process into an auditable one.

## The demo beat (~3 min, hero-forward, NOT a dashboard)
Two hand-authored patients create the money contrast: one that *looks closed but isn't*, one that *looks open but is closed*. Together they prove the reasoning cuts both ways — catches real misses **and** suppresses false alarms (the anti-alert-fatigue proof).

- **0:00–0:20 — Cold open.** "Here's a backlog of finished radiology reports. Somewhere in here, a lung-nodule follow-up fell through 14 months ago." Kick off the sweep; Haiku extraction streams (N recommendations found). Don't dwell — this is the commodity part.
- **0:20–1:40 — Hero beat (Case A: looks closed, isn't).** Show the Nov-2024 nodule recommendation. The agent finds a Feb-2025 CT chest and, instead of matching-and-closing, reasons on screen: modality ✓, coverage ✓, **acknowledgment ✗ (nodule never mentioned)** — with the exact source text highlighted — → **`UNCONFIRMED`, escalate.** The aha: a naive tracker closes this; Safety Net catches that the nodule was never actually re-evaluated. *This is the beat for Ricci.*
- **1:40–2:20 — Contrast beat (Case B: looks open, is closed).** A patient flagged "overdue" by date logic. The agent reasons: a later PET/CT (superior modality) characterized the nodule as benign → **superseded, no action.** Suppresses a false alert.
- **2:20–2:50 — Action beat.** Back to Case A: the agent drafts the patient/provider outreach; a human approves in one click; the audit entry flashes. (Autonomy gradient, made visible.)
- **2:50–3:00 — Close.** *"The report was right. The system around it failed. We built the system."*

## What goes on screen
- A **streaming reasoning trace**: recommendation → candidate → each axis resolving → verdict + confidence.
- **Evidence-span highlighting** in the source report for every verdict — verifiability is the thing Ricci will trust. Never a black box.
- **Visible MCP tool calls**, so judges scoring Technical Complexity see the multi-step agentic loop.
- Any aggregate/worklist view is a **2-second bookend at most** ("swept 50 reports → 3 truly open, 1 false alarm suppressed"). Never the centerpiece. This is how you dodge the "dashboard is the main feature" anti-project.

## Ruthless 6.5-hour build priority
**Must-have (the demo dies without it):**
1. Two hand-authored hero patients (~6–10 reports total) engineered to showcase the reasoning. *Do not* trust Synthea for the "CT-done-but-nodule-unmentioned" nuance — author it. (Built during the event = legitimate.)
2. Haiku extraction → recommendation/study objects.
3. **Opus reconciliation across the five axes, with evidence spans + confidence.** The core. Spend your prompt-engineering time here.
4. Closure-state resolution + the escalation rule.
5. MCP server exposing the tools (makes the loop legible and is on-theme).
6. Reasoning-trace surface with evidence highlighting + one draft-and-approve action.

**Cut / defer (do NOT let these eat the clock):**
- Broad specialty coverage — radiology only for the demo; assert generalization.
- Deep Synthea integration — hand-authored heroes + templated filler for the sweep visual.
- Any real dashboard/analytics beyond the 2-second bookend.
- FHIR/EHR integration, auth, multi-user, persistence.

**One change from earlier advice:** treat cross-specialty as a *spoken claim + architecture point* (and an optional stretch case), **not** a build target. The reconciliation-reasoning wedge out-differentiates breadth, and breadth eats your 6.5 hours. Lead with depth.

## Q&A, grounded in the loop (for Ricci)
- **"How is this different from PowerScribe Follow-up Manager / Rad AI?"** → They match orders and track appointments. We reason about clinical equivalence and acknowledgment — whether the nodule was re-evaluated, not just whether a chest CT happened. That distinction *is* the failure mode.
- **"What's your false-negative rate?"** → We don't silently close ambiguous cases — low-confidence reconciliations escalate with the specific question. The system makes misses visible; it isn't claiming perfect extraction.
- **"Isn't an LLM unreliable for clinical decisions?"** → It's not diagnosing. It's reasoning about document equivalence — did study B address finding A — with every verdict grounded in cited text a human verifies. A reconciliation engine with an audit trail, not an autonomous clinician.
