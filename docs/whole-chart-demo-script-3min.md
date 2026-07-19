# Safety Net — Whole-Chart Review — 3-Minute Demo Script

Final cut for the live 3-minute demo + Q&A. Delivered in the **first-person
voice of a practicing physician**, driven by the redesigned master-detail UI,
run **offline / deterministic** from the cached render (never a live model call
on stage). Pair with `docs/whole-chart-demo-runbook.md` (mechanics) and
`docs/whole-chart-live-test.md` (why the demo path is deterministic).

> **Delivery note.** The opener and "the one that scares me" line assume a
> clinician is speaking. If the presenter isn't an MD, swap the ⟨MD-voice⟩ lines
> for the third-person alternates in brackets — everything else is unchanged.

---

## Script at a glance
- **Cold open (0:00):** discharge is the *start* of the journey home, not the end; nobody re-reads 14 days at that moment — Safety Net does.
- **Hook — the nodule (0:18):** a recognizable miss — an incidental lung nodule on a Day-2 abdominal CT that never reached the discharge plan. Lands fast, then escalates.
- **Hero — held anticoagulant (0:38):** apixaban held Day 1 for a procedure, never restarted, silently dropped at discharge — *no order to match*, an open loop across three documents. The exact human-answerable question + verbatim citations. **The one live Approve → audit line.**
- **Threshold — creatinine slope (1:28):** a lab trend no single value flags (0.9 → 1.6 → partway back); the sparkline; a drafted recheck.
- **Loose end — cultures (1:52):** Day-11 blood cultures still pending at discharge, no owner — one line.
- **Contrast — the suppress (2:04):** a colonoscopy "miss" already closed in the PCP letter in different words → cleared with the receipt. Precision, not keyword matching.
- **How it works + trust + moat (2:28):** Haiku → deterministic threading → Opus; every quote a validated verbatim substring (9/9, 0 hallucinated); reconciles documentation, never diagnoses; measured precision/recall 1.0; sharper as Claude improves; one engine, any handoff.
- **Close (2:52):** "The chart had the answer the whole time. No one had read all of it. Now something has."

## Locked facts (verified against the current build — keep these exact)
1. **Surfaced order on screen:** `01` lung nodule · `02` apixaban · `03` blood cultures · `04` creatinine. **Cleared:** the colonoscopy, **cited to the PCP letter** ("lower endoscopy … in approximately two months").
2. **Say "every note, lab, result, and consult" — never "multi-modal" or "transcript."** The pipeline reads chart *text* only. We do not ingest audio/ambient transcripts; claiming so is inaccurate and a DQ risk.
3. **The numbers (from `eval_harness`):** 4 surfaced · 1 cleared · **9/9 citations validated · 0 hallucinated · precision 1.0 · recall 1.0**.
4. **The one live control is Approve** — now enabled on every surfaced card; the demo approves the **apixaban** fix (restart stroke prevention).

## Timing map (target 3:00; rehearse to ~2:50 with buffer)
| Beat | Window | Airtime |
|---|---|---|
| Cold open — discharge is the start | 0:00–0:18 | 18s |
| Hook — the incidental nodule | 0:18–0:38 | 20s |
| **Hero — held anticoagulant + live Approve** | 0:38–1:28 | 50s |
| Threshold — creatinine slope | 1:28–1:52 | 24s |
| Loose end — cultures pending | 1:52–2:04 | 12s |
| Contrast — suppress the look-alike | 2:04–2:28 | 24s |
| How it works + trust + moat | 2:28–2:52 | 24s |
| Close | 2:52–3:00 | 8s |

Nodule and cultures are ~one line each; **apixaban and creatinine get the air.** The Approve click is the only live control. The close line is fixed.

---

## THE SCRIPT

### Cold open — discharge is the start, not the end (0:00–0:18)
*[Show: cached `whole_chart.html` at the top — header + meta strip. Never a live run.]*

> ⟨MD-voice⟩ "When I discharge a patient after two weeks in the hospital, that's not the finish line — it's the *start* of their journey home. But the discharge summary gets written *forward* from today's problem list. Nobody re-reads all fourteen days — every note, every lab, every consult — at the one moment it matters most. Safety Net did."
>
> *[Non-MD alternate: "When a physician discharges a patient after two weeks, that's not the finish line — it's the start of the journey home…"]*

*[Point at the meta strip: 14-day admission · 4 surfaced · 1 cleared · 9/9 citations valid.]*

### Hook — the incidental nodule (0:18–0:38)
*[Show: the nodule card (01) is already open. Point at the Day-2 citation, then the red discharge GAP.]*

> "Start with one you'll recognize. Day 2, an abdominal CT — ordered for something else — mentions in passing a nine-millimeter lung nodule that needs a three-month scan. It's buried in a report about the abdomen, and it never made the discharge plan. That's exactly how an incidental finding becomes a late-stage diagnosis two years later. Safety Net caught it — with the exact line from the report. But that's the *familiar* miss. ⟨MD-voice⟩ Here's the one that scares me."

### Hero — the held anticoagulant (0:38–1:28)
*[Show: click worklist row 02 — apixaban. Point at the two Day-1 citations, then the Day-14 GAP.]*

> "This patient came in on apixaban — a blood thinner for atrial fibrillation. Day 1 we held it for a drain procedure — exactly right. But the discharge medications continue his *other* home meds and just… drop the apixaban. No rationale. He's going home off stroke prevention, and in a normal discharge nothing flags it.
>
> This is why it has to be an *agent*, not a rule. There's no order and no recommendation to match — only an open loop across three documents and fourteen days that nobody closed. Safety Net threads those signals into entities across the whole stay, reasons about each one at discharge, and asks the exact question a human can answer —"

*[Point at the "Needs a human answer" panel; read it.]*

> "— 'Was apixaban intentionally stopped, or should it restart for stroke prevention now that the drain is out?' Every claim on the card is a verbatim citation — an exact substring of the chart, validated automatically.
>
> And it doesn't stop at flagging — it drafts the fix, but sends nothing itself. I review, and I approve."

*[CLICK **Approve & send**. Audit line appears; button disables.]*

> "Logged, audit trail intact. Autonomous where it's safe — reading fourteen days no one has time to re-read — and human-gated on anything that touches the patient."

### Threshold — the value that drifted over the line (1:28–1:52)
*[Show: click worklist row 04 — creatinine. Point at the sparkline, then the Day 1 → 5 → 12 lab citations.]*

> "It isn't only medications. It walks the labs for values that crossed a line and were never acknowledged. His kidney function drifted — creatinine point-nine up to one-point-six mid-stay, and only partway back by discharge. Each single value looked fine in the moment; the *slope* is the signal. No kidney injury on the discharge problem list, no recheck arranged — it caught the trend across days and drafted an outpatient recheck for the PCP."

### Loose end — cultures pending (1:52–2:04)
*[Show: click worklist row 03 — blood cultures.]*

> "One more, quickly: blood cultures drawn for a Day-11 fever, still pending at discharge with nobody assigned to read them. Surfaced, with a specific owner and question."

### Contrast — suppress the false alarm (2:04–2:28)
*[Show: click the green CLEARED row — the colonoscopy. Point at the "MATCH — SAME PLAN" row, then the VERDICT strip.]*

> "Now the discipline — because a tool that cries wolf is worse than nothing. The GI team recommended a colonoscopy after this patient's diverticulitis. It's *not* in the structured discharge plan, so a keyword checker fires a false alarm. But Safety Net read the PCP letter — 'lower endoscopy in about two months' — recognized the same plan in different words, and stayed silent. Cleared, with the receipt. Catching real misses and suppressing false ones is the *same* reasoning — and it's why this doesn't drown a clinician in alerts."

### How it works + why you can trust it (2:28–2:52)
*[Show: gesture at the validation footer — precision 1.0 · 9/9 · 0 hallucinated.]*

> "Under the hood: Haiku extracts every signal, deterministic code threads them into entities across the timeline, and Opus reasons about each one against the discharge documents — with every quote validated as an exact substring of the chart before you see it. It reconciles documentation; it never diagnoses. We measured it against hand-authored ground truth — measuring precision and recall. And because the reasoning *is* the model, it gets sharper every time Claude does. It's one engine — point it at any record, any handoff, any specialty."

### Close (2:52–3:00)
*[Stop moving. Look up. Deliver clean, then stop talking.]*

> "The chart had the answer the whole time. No one had read all of it. Now something has."
>
> *[Optional patient-facing button — pick one, don't say both: "Now every patient has a safety net."]*

---

## Q&A (rehearse — ~15–20s each; answer, then stop)

**"Isn't this just a discharge checklist / problem-list checker?"**
> "A checker matches strings. We reason about *acknowledgment across time and domain* — a held med never restarted, a lab slope no single value flags, a consult rec closed in the letter in different words. We proved it both directions: four real misses surfaced, and the look-alike a checker would false-alarm on correctly cleared."

**"Why an agent, not a scripted pipeline?"**
> "The orchestration *is* deterministic — loading notes, threading entities, ranking. The hard part is open-ended: does this later note actually close this thread, maybe in different words? No rule captures that. Code where it should be reliable; the model where it must reason."

**"What happens when it's wrong? A hallucinated finding could hurt someone."**
> "It never closes or decides — it surfaces a question with the evidence, and a human approves any action. Every claim carries a verbatim citation validated automatically as an exact substring: nine of nine here, zero hallucinated. Unvalidated claims are dropped before you ever see them."

**"How do you know it's right — did you measure anything?"**
> "The chart is hand-authored, so the planted threads are ground truth, and our eval harness scores against them: precision 1.0 and recall 1.0 on the surfaced set, the suppress case correctly cleared, all citations validating. A reproducible gate, not a vibe."

**"Won't this cause alert fatigue / isn't it a dashboard?"**
> "The opposite — the cap and the abstain threshold are the point. It ranks by consequence, surfaces only what it genuinely can't confirm, and stays silent on everything it *can* confirm was handled. Precision over recall, by design."

**"What did you build during the event vs. pre-existing?"**
> "Everything in the repo — the whole-chart pipeline, entity threading, the reasoning prompt, the eval harness, the UI — built during the event; here's the public repo. We reuse the Anthropic SDK, Pydantic, FastMCP, and Claude. All data synthetic, no PHI."

**"HIPAA / PHI — where does the data go?"**
> "The demo is fully synthetic. In production it runs inside the covered boundary where ambient documentation already lives — no data leaves a safe path."

**"Where does it sit in the day / who pushes the button?"**
> "It runs at discharge on the chart that's already there — no new workflow — and produces a short, ranked queue; the clinician answers or approves. Optionally the approved outreach goes to the patient."

**"As Claude gets smarter, does this get better or does your edge vanish?"**
> "Better — the reconciliation *is* the model's reasoning, so every capability gain raises our precision and recall directly. We're a harness around frontier reasoning, not a workaround for it."

**"Are you replacing clinical judgment?"**
> "Supporting it. We never decide; we surface an unclosed loop with the evidence and ask. The human controls everything that touches the patient."

*If you don't know an answer: say the honest version and offer to follow up. Never bluff a domain expert.*

---

## What this cut pulls from both drafts
- **Structure:** opens on the nodule (recognizable, matches the reordered UI) as a 20s hook, then **escalates to apixaban as the acute hero** — legibility *and* the strongest differentiation.
- **Voice:** first-person physician, with safe non-MD swaps.
- **Approve beat** lands during the hero (no back-navigation), on the now-live apixaban action.
- **Honesty locked:** colonoscopy → PCP letter; "every note, lab, and consult" (never "multi-modal/transcript"); the measured numbers.
- **Added:** the "sharper as Claude improves" moat, the one-engine extensibility line, and the full Q&A bank.
