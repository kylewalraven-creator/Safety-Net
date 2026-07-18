# Safety Net — Whole-Chart Review — Demo Script (live 3-min + Q&A)

## Summary — read this first
- **What it is:** Safety Net reviews an entire **14-day inpatient admission at discharge** and surfaces the threads that fell through — each with a verbatim citation and a specific, human-answerable question — while **suppressing** look-alikes that were actually closed in different words.
- **The frame:** **discharge isn't the finish line — it's the start of the patient's journey home.** The discharge summary is written *forward* from today's problem list; nobody re-reads all 14 days at the one moment it matters. Safety Net does, then notifies the clinician (and, optionally, the patient).
- **Who's presenting:** first-person voice of a **practicing physician** — "my patient," "this scares me." Not a vendor pitch.
- **The arc (~2:50):** cold open (discharge = start) → the chart sweep → **Hero: held anticoagulant never restarted** (escalate) → **a value that crossed a threshold** (creatinine trend, unacknowledged) → **suppress** (colonoscopy already closed in the PCP letter) → one human-approved notification → close.
- **On screen (`ui/whole_chart.html`):** one page — bookend *"4 unreconciled threads across a 14-day stay,"* findings ranked by consequence with **risk + status** pills, each with its cross-day **timeline of verbatim citations**, a specific **question**, and a drafted **action**; a collapsed **CLEARED** section (the suppressed look-alike); one live **Approve** button.
- **Measured, not vibes:** `python -m safety_net.eval_harness` → **precision 1.0**, suppress correct, **9/9 citations validated** as exact substrings. Say it out loud.
- **"Why an agent" (reflex):** it reads every note across 14 days and reasons about *acknowledgment* across time and domain — no order to match, no keyword to grep. Code where it must be reliable; the model where it must reason.
- **The close (never cut it):** *"The chart had the answer the whole time. No one had read all of it. Now something has."*

---

## How to use this
- **Matches the built whole-chart UI.** Render offline first: `python ui/render_chart.py` → open `ui/whole_chart.html`. The page makes **zero network calls**, so wifi loss is survivable. Beats below are *scroll-and-point*; the only live interaction is the **Approve** button.
- **If a live call hangs, flip to the cached render and keep talking** — identical output, from `data/chart/cache/`. If everything dies, the 1-min video is the ultimate fallback.
- **Deliver in the first-person voice of a physician** — "my patient," "I've watched this happen." If two of you present, keep one consistent clinician voice across handoffs.
- **Rehearse to ~2:50** with buffer. The close line is fixed — never cut it, never rush it.
- **Tone for the room (Ricci is in it):** reference "order-matching" and "keyword checkers" neutrally — they describe real, good products. The contrast is an honest technical distinction, not a takedown.
- **Two-hero radiology demo is the fallback** — see `docs/demo-script-two-hero.md` (fully scripted, `ui/render.py`) if you need to pivot back.

---

## THE SCRIPT

### Cold open — discharge is the start, not the end (0:00–0:20)
[Screen: a **pre-recorded** clip of `chart_review` streaming, or the cached `whole_chart.html` at the top — **never a live run**. Land on the header + bookend line.]

> "I'm a physician. When I discharge a patient after a two-week admission, that's not the finish line — it's the *start* of their journey home. But the discharge summary gets written *forward* from today's problem list. Nobody re-reads all fourteen days — every note, every lab, every consult — at the one moment it matters most."

[Point at the bookend line: *"4 unreconciled threads across a 14-day stay."*]

> "Safety Net does. It read this patient's entire chart at discharge and found four threads that fell through — and stayed silent on everything that was actually handled."

*(That's the thesis. Land it, then go straight to the hero.)*

### Hero beat — the held anticoagulant (0:20–1:20)
[Scroll to the first finding: **High / UNCONFIRMED** — "Home anticoagulant apixaban … never restarted."]

> "Here's the one that scares me. This patient came in on apixaban — a blood thinner for atrial fibrillation."

[Point at the Day 1 citations — the med-rec line, then the hold note.]

> "Day 1, we held it for his drain procedure — completely appropriate. But then —"

[Point at the Day 14 discharge-medications gap citation.]

> "— the discharge list continues his *other* home meds and just… drops the apixaban. No rationale. He's going home off stroke prevention, and in a normal discharge nothing flags it."

> "This is why it has to be an *agent*, not a rule: there's no order and no recommendation to match — only a loop across three documents and fourteen days that nobody closed. Safety Net connects them and asks the exact question a human can answer:"

[Point at the question; read it.]

> "'Was apixaban intentionally discontinued, or should it be restarted at discharge for stroke prevention?'"

*(Beat. This is the moment — highest, most acute stakes. Let it sit.)*

### Threshold beat — the value that drifted (1:20–1:45)
[Scroll to the **Medium / UNCONFIRMED** creatinine finding.]

> "It isn't only medications. Safety Net also walks the labs for values that crossed a threshold and were never acknowledged. His creatinine rose from 0.9 to 1.6 mid-stay —"

[Point at the Day 1 → Day 5 → Day 12 lab citations.]

> "— each single value looked unremarkable in the moment; the *slope* is the signal. No kidney injury on the discharge problem list, no recheck arranged. It caught the trend across days and flagged an outpatient creatinine recheck for the PCP."

### Contrast beat — suppress the false alarm (1:45–2:15)
[Scroll to the **CLEARED** section — the colonoscopy thread.]

> "Now the discipline — because a tool that cries wolf is worse than nothing. The GI team recommended a colonoscopy after this diverticulitis. It is *not* in the structured discharge plan, so a keyword checker fires a false alarm."

[Point at the cleared item's citation — the PCP letter.]

> "But Safety Net read the PCP letter — 'lower endoscopy in about two months' — recognized that's the same plan in different words, and stayed silent. Cleared, with the receipt. Catching real misses and suppressing false ones is the same capability: reasoning about what actually happened, not matching strings."

### Action beat — notify, human-gated (2:15–2:45)
[Scroll back to the apixaban finding's drafted action. This is the one real click.]

> "For every real miss it drafts the notification — an addendum for the discharging team, a message to the PCP, and optionally patient outreach — but it sends nothing on its own. A clinician reviews and approves."

[CLICK — Approve. The audit line appears; the button disables.]

> "Approved, logged, audit trail intact. Autonomous where it's safe — reading fourteen days of chart no human has time to re-read. Human-gated where it matters — anything that touches the patient. It's an MCP server, so it runs on the discharge with no new workflow and no new headcount — it's safety capacity the system can't hire for. And because the reasoning *is* the model, it gets sharper every time Claude does."

*(Credibility, ~8s — first to cut if over time.)*
> "And this isn't a vibe — we measured it: on our ground truth, precision 1.0, zero false alarms, and every quote on screen is an exact substring of the source, checked automatically. Nine of nine."

### Close (2:45–3:00)
*(Stop moving. Look up. Deliver clean, then stop talking.)*

> "The chart had the answer the whole time. No one had read all of it. Now something has."

---

## Q&A (rehearse — ~15–20 sec each; answer, then stop)

**"Isn't this just a discharge checklist / problem-list checker?"**
> "A checker matches strings against the problem list. We reason about *acknowledgment across time and domain* — a held med that was never restarted, a lab slope no single value flags, a consult rec that's closed in the discharge letter in different words. We proved it both directions: we escalate the real miss and *suppress* the look-alike a checker would false-alarm on."

**"Why does this need to be an agent, not a scripted pipeline?"**
> "The orchestration *is* deterministic on purpose — loading notes, threading entities, ranking. The hard part is open-ended reasoning: does this later note actually close this thread, possibly in different words? No rule captures that. Code where it should be reliable, the model where it must reason."

**"What happens when it's wrong? A hallucinated finding could hurt someone."**
> "It never closes or decides — it surfaces a question with the evidence and a human approves any action. Every claim carries a verbatim citation validated automatically as an exact substring of a source note; unvalidated claims are dropped. Nine of nine on our set, zero hallucinated."

**"How do you know it's right — did you measure anything?"**
> "Yes — the chart is hand-authored, so the planted threads are ground truth, and our eval harness scores against them: precision 1.0 on the surfaced set, the suppress case correctly cleared, all citations validating. It's a reproducible gate, not a vibe."

**"What did you build today vs. what pre-existed?"**
> "Everything in the repo — the whole-chart pipeline, entity threading, the reasoning prompt, the eval harness, the UI — built today; here's the public repo. We reuse the Anthropic SDK, Pydantic, FastMCP, and Claude. All data is synthetic, no PHI."

**"HIPAA / PHI — where does the data go?"**
> "Demo is fully synthetic. In production it runs inside the covered boundary — the same place ambient documentation already lives — no data leaves a safe path."

**"Where does this sit in the clinician's day / who pushes the button?"**
> "It runs at discharge on the chart that's already there — no new workflow. It produces a short, ranked queue of questions; the clinician answers or approves. Optionally the approved outreach goes to the patient."

**"As Claude gets smarter, does this get better or does your edge vanish?"**
> "Better — the reconciliation *is* the model's reasoning, so every capability gain raises our precision and recall directly. We're a harness around frontier reasoning, not a workaround for its limits."

**"Are you replacing clinical judgment?"**
> "Supporting it. We never decide; we surface an unclosed loop with the evidence and ask. The human stays in control of everything that touches the patient."

**"What breaks on a real, messy Epic/Cerner chart?"**
> "Extraction is the fragile part — which is exactly why every finding is grounded in a verbatim citation and we escalate-not-close under ambiguity. Messiness degrades to a question, never a false closure."

*If you don't know an answer: say the honest version and offer to follow up. Never bluff a domain expert.*

---

## 1-minute video cut (condensed — record after the freeze)
*(Visuals: cut between four regions of `whole_chart.html` — the bookend, the apixaban finding + question, the creatinine trend, the CLEARED colonoscopy — then the Approve click.)*

> "Discharge isn't the end of a hospital stay — it's the start of the patient's journey home, and it's where things fall through. No clinician re-reads all fourteen days of a chart at that moment. Safety Net does. [bookend] On this admission it found four threads that fell through. Here's the one that matters: this patient's blood thinner for atrial fibrillation was held for a procedure Day 1 — and never restarted. The discharge list keeps his other meds but drops it. He's going home off stroke prevention, and nothing flagged it. No order to match — Safety Net connected three documents across the stay and asks: should apixaban be restarted? [creatinine] It also caught a kidney-function trend no single value flags, and [cleared] it *suppressed* a colonoscopy 'miss' that was actually closed in the PCP letter — reasoning, not keyword-matching. Precision 1.0, every citation verbatim. It drafts the notification; a clinician approves; nothing sends itself. The chart had the answer the whole time. No one had read all of it. Now something has."

---

## Pre-flight checklist (verify before you walk into the room)
- [ ] `python -m safety_net.eval_harness` is **green** (precision 1.0, suppress cleared, citations valid) — and you can quote the numbers.
- [ ] `ui/whole_chart.html` renders offline from `data/chart/cache/` with the bookend, all four surfaced findings, the CLEARED section, and a working **Approve** button.
- [ ] The apixaban timeline highlights land on all three citations (Day 1 med-rec, Day 1 hold, Day 14 discharge-meds gap).
- [ ] The creatinine trend shows the Day 1 / Day 5 / Day 12 values.
- [ ] The colonoscopy thread is in **CLEARED**, cited to the PCP letter (the suppress proof).
- [ ] The cold-open clip is **pre-recorded** (no live run on stage).
- [ ] You can deliver in ≤3:00 with the close line intact.
- [ ] 1-min video renders and its link opens logged-out.
