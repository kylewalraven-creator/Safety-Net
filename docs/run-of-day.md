# Safety Net — Hackathon Run-of-Day

**Clock:** build runs **10:30 AM → 5:00 PM** (6.5 hrs). Submission (public repo + 1-min video + both teammates added) is due **at 5:00 PM**, not after. R1 judging 5:00–6:45, dinner 6:00, R2 (top 6) 7:00–8:00, winners 8:15.

**Guiding principle:** get a thin end-to-end slice working on ONE case by lunch, then thicken. Freeze early. The 3-min live demo is the deliverable — everything serves it. A working Case-A hero beat beats a half-built five-feature app.

**Distributing the work:** everything below is unowned — divide it between you however fits your strengths. Tasks marked *parallel tracks* are independent and can run simultaneously; the rest have ordering dependencies noted inline. The one hard dependency to respect: extraction needs an authored case to run against, so author Case A early.

---

## Pre-clock — 9:00–10:30 AM (arrival & prep; DON'T touch project code)
Doors 9:00, breakfast/team formation, kickoff 10:00. Use this to arrive at 10:30 ready to sprint:
- Dev env + API keys verified working; empty public repo initialized with a README stub.
- Roles locked; the two hero scenarios decided **on paper** (clinical logic can be pre-thought; write the actual reports/code after 10:30 for DQ cleanliness).
- **At kickoff, absorb the Abridge/partner resources reveal.** If they hand out clinical data or an MCP server that helps, adjust the plan in the first 15 minutes.

## Morning — 10:30 AM–1:00 PM (foundation + thin vertical slice)
**Goal by lunch:** extract → reconcile → verdict-with-evidence runs end-to-end on Case A, even if rough.
- **10:30–10:50 (both):** Architecture lock. Init public repo + README stating today's plan. Fold in any kickoff resources.
- **10:50–12:00 (two parallel tracks):**
  - Author the hero cases + rubric: write **Case A first** (nodule rec Nov-2024 + Feb-2025 CT chest that *omits* the nodule) — the extraction track needs it to run against, so it's the critical path; then Case B (nodule rec + later PET/CT benign). Draft the 5-axis rubric as clinical criteria.
  - Build the pipeline: stand up the skeleton + MCP server + Haiku extraction producing recommendation/study objects from reports as they land.
- **12:00–1:00 (integrate):** Wire extraction → Opus reconciliation on Case A → emit a verdict + evidence span, ugly rendering is fine.
- **★ Milestone: thin vertical slice runs on Case A.**

## Midday — 1:00–3:00 PM (harden core + contrast case + escalation)
Grab lunch, keep momentum (a real 10-min break helps). **Goal:** reasoning is solid on both cases and renders as the hero.
- **1:00–2:00 (two parallel tracks):**
  - Harden Opus reconciliation — reliable, structured verdicts across the 5 axes with evidence spans + confidence; implement closure-state resolution + **the escalation rule** (indeterminate + specific human question).
  - Build/refine the reasoning-trace surface (axes rendering, evidence highlighting in source text); start the demo script against real output.
- **2:00–3:00 (integrate):**
  - Push Case B through the full pipeline. **★ Milestone: both beats work — catch-the-miss AND suppress-the-false-alarm.**
  - Add the action beat: draft outreach/order → human-approve → audit entry (lightweight).

## Afternoon — 3:00–5:00 PM (polish, freeze, package, submit)
- **3:00–3:45:** Polish the demo surface — legible reasoning trace, evidence highlighting, visible MCP calls, the 2-second aggregate bookend. Fix only the top 2–3 rough edges. Finalize the 3-min script + Q&A.
- **3:45 — ★ HARD FEATURE FREEZE.** No new functionality after this. Whatever works, works.
- **4:00–4:30:** Full dry-run of the 3-min demo on the real build; time it; cut anything that breaks or overruns. **Record the 1-minute video** (tight: hero beat + close line).
- **4:30–5:00:** Repo **public**; clean README (what we built today, architecture, how to run); verify video/demo link works; add both teammates; **submit before 5:00.** Keep buffer for the inevitable glitch.

## Judging — 5:00 PM onward
- **5:00–6:45 (R1):** Rehearse once more before your assigned slot. Run it live, nail the Case-A beat, deliver the close line ("The report was right. The system around it failed. We built the system."), field Q&A with the grounded answers. Dinner 6:00.
- **7:00–8:00 (R2, if top 6):** Same demo on stage, tighter (equal-weighted criteria).
- **8:15:** Winners.

---

## If you're behind (graceful degradation)
Cut in this order — never add scope to catch up:
1. Drop the action beat (draft/approve) → describe it verbally.
2. Drop Case B → ship **Case A hero beat + close line only.** The catch-the-miss reasoning alone carries the wedge and still wins the Ricci moment.
3. Ugly-but-working rendering beats pretty-but-broken. Protect the reasoning trace + evidence highlighting above all else.
