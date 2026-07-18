# Safety Net — Whole-Chart Review — Demo Script (live 3-min + Q&A)

> **This script is the source of truth for the UI.** The stage directions name the
> exact on-screen elements; build `ui/whole_chart.html` to match. See **"UI spec"**
> and **"Pipeline fixes required"** below.

## Summary — read this first
- **What it is:** Safety Net reviews an entire **14-day inpatient admission at discharge**, connects signals across every note/lab/consult, and surfaces only the threads that genuinely fell through — each with a verbatim citation and a specific, human-answerable question — while **correctly clearing** everything that was actually handled.
- **The frame:** **discharge isn't the finish line — it's the start of the patient's journey home.** The discharge summary is written *forward* from today's problem list; no one re-reads all 14 days at the one moment it matters. Safety Net does, then notifies the clinician (and, optionally, the patient).
- **The numbers that sell it:** **34 threads considered → 4 surfaced → 30 cleared**, **98/98 citations validated** as exact substrings, **precision 1.0** on ground truth. The 30 cleared is the anti-alert-fatigue proof; say it out loud.
- **Who's presenting:** first-person voice of a **practicing physician** — "my patient," "this scares me."
- **The arc (~2:50):** cold open (discharge = start) → **Hero: held anticoagulant never restarted** (escalate) → **a value that crossed a threshold** (creatinine trend, unacknowledged) → the classic radiology miss + a pending result (quick) → **precision: 30 loops it checked and closed**, including a look-alike closed in different words → one human-approved notification → close.
- **"Why an agent" (reflex):** it reads every note across 14 days and reasons about *acknowledgment* across time and domain — no order to match, no keyword to grep. Code where it must be reliable; the model where it must reason.
- **The close (never cut it):** *"The chart had the answer the whole time. No one had read all of it. Now something has."*

## UI spec — what `whole_chart.html` must render (script drives this)
- **Header:** "Safety Net · Whole-Chart Review."
- **Bookend line (one line, 2-second read):** *"14-day admission · 34 threads considered · 4 surfaced · 30 cleared · 98/98 citations valid."*
- **Surfaced list — exactly 4 cards, ranked by consequence**, each showing: a **risk pill** (High/Medium) + **status pill** (UNCONFIRMED / PENDING_AT_DISCHARGE), a one-line **title**, a **timeline of verbatim citations** (day · note-id · quote, with "gap" citations styled differently), the **question**, and the **drafted action**. Order for the demo: **apixaban, creatinine, nodule, blood cultures.**
- **Cleared section — collapsed by default**, showing just the **count (30)** with a caption "considered and correctly closed"; expandable to the list. One item (the colonoscopy) is the suppress proof.
- **One live control:** an **Approve** button on the apixaban action → reveals an audit line, disables itself. No other interactivity; zero network calls at demo time.

---

## How to use this
- Render offline first: `python ui/render_chart.py` → open `ui/whole_chart.html`. Zero network calls; wifi loss is survivable. Beats are *scroll-and-point*; the only click is **Approve**.
- **If a live run hangs, flip to the cached render and keep talking** — identical output from `data/chart/cache/`. Ultimate fallback: the 1-min video.
- **Deliver in the first-person voice of a physician.** One consistent clinician voice if two present.
- **Rehearse to ~2:50** with buffer. Four surfaced threads in three minutes is tight — apixaban and creatinine get the airtime; nodule and cultures are one line each. The close line is fixed.
- **Tone (Ricci is in the room):** reference "order-matching" and "keyword checkers" neutrally — real, good products. The contrast is an honest technical distinction.
- **Fallback demo:** two-hero radiology, fully scripted, in `docs/demo-script-two-hero.md` (`ui/render.py`).

---

## THE SCRIPT

### Cold open — discharge is the start, not the end (0:00–0:20)
[Screen: a **pre-recorded** clip of `chart_review` streaming, or the cached `whole_chart.html` at the top — **never a live run**. Land on the header + bookend line.]

> "I'm a physician. When I discharge a patient after a two-week admission, that's not the finish line — it's the *start* of their journey home. But the discharge summary gets written *forward* from today's problem list. Nobody re-reads all fourteen days — every note, every lab, every consult — at the one moment it matters most."

[Point at the bookend: *"34 threads considered · 4 surfaced · 30 cleared · 98/98 citations valid."*]

> "Safety Net read this patient's whole chart at discharge. It considered thirty-four open threads, quietly closed thirty that were actually handled, and surfaced the four that fell through. Let me show you the one that scares me."

*(That's the thesis and the precision proof in one breath. Go straight to the hero.)*

### Hero beat — the held anticoagulant (0:20–1:15)
[Scroll to the apixaban card: **High / UNCONFIRMED**.]

> "This patient came in on apixaban — a blood thinner for atrial fibrillation."

[Point at the Day 1 citations: the med-rec line, then the hold note.]

> "Day 1 we held it for his drain procedure — exactly right. But then —"

[Point at the Day 14 gap citations: discharge meds + PCP letter.]

> "— the discharge medications continue his *other* home meds, lisinopril and atorvastatin, and just… drop the apixaban. No rationale, in the summary or the PCP letter. He's going home off stroke prevention, and in a normal discharge nothing flags it."

> "This is why it has to be an *agent*, not a rule. There's no order and no recommendation to match — only a loop across three documents and fourteen days that nobody closed. Safety Net connects them and asks the exact question a human can answer:"

[Point at the question; read it.]

> "'Was apixaban intentionally discontinued, or should it be restarted for stroke prevention now that the drain is out? If it was stopped deliberately, where's the rationale?'"

*(Beat. Highest, most acute stakes of the set. Let it sit.)*

### Threshold beat — the value that drifted over the line (1:15–1:45)
[Scroll to the creatinine card: **Medium / UNCONFIRMED**.]

> "It isn't only medications. Safety Net walks the labs for values that crossed a threshold and were never acknowledged. His kidney function drifted — creatinine from 0.9 up to 1.6 mid-stay —"

[Point at the Day 1 → Day 5 → Day 12 lab citations.]

> "— and only partway back by discharge. Each single value looked fine in the moment; the *slope* is the signal. No kidney injury on the discharge problem list, no recheck arranged. It caught the trend across days and drafted an outpatient recheck for the PCP."

### Depth beat — the classic miss and the loose end (1:45–2:05)
[Point quickly at the nodule card, then the blood-cultures card.]

> "Two more it caught: an incidental nine-millimeter lung nodule that needs a three-month scan — never carried into the follow-up plan. And blood cultures drawn for a Day 11 fever spike, still pending at discharge with no one assigned to read them. Both surfaced, both with a specific owner and question."

### Precision beat — the thirty it stayed quiet on (2:05–2:30)
[Point at the collapsed **CLEARED (30)** count; expand the colonoscopy item.]

> "Now the discipline — because a tool that cries wolf is worse than nothing. It cleared thirty threads it checked and found genuinely closed: the antibiotics reconciled, the stable labs, the follow-ups already booked. Including this —"

[Point at the colonoscopy cleared item, cited to the PCP letter.]

> "— the GI team recommended a colonoscopy; it's not in the structured discharge plan, so a keyword checker fires a false alarm. Safety Net read the PCP letter — 'lower endoscopy in about two months' — recognized the same plan in different words, and stayed silent. Catching real misses and suppressing false ones is the same reasoning."

### Action beat — notify, human-gated (2:30–2:50)
[Scroll to the apixaban action. This is the one real click.]

> "For every real miss it drafts the notification — an addendum for the discharging team, a message to the PCP, optionally outreach to the patient — but it sends nothing on its own. A clinician reviews and approves."

[CLICK — Approve. Audit line appears; button disables.]

> "Approved, logged, audit trail intact. Autonomous where it's safe — reading fourteen days of chart no human has time to re-read. Human-gated where it matters — anything that touches the patient. It runs at discharge with no new workflow and no new headcount: safety capacity the system can't hire for. And because the reasoning *is* the model, it gets sharper every time Claude does. We measured it: precision 1.0, and every one of ninety-eight citations is an exact quote from the chart."

### Close (2:50–3:00)
*(Stop moving. Look up. Deliver clean, then stop talking.)*

> "The chart had the answer the whole time. No one had read all of it. Now something has."

---

## Q&A (rehearse — ~15–20 sec each; answer, then stop)

**"Isn't this just a discharge checklist / problem-list checker?"**
> "A checker matches strings. We reason about *acknowledgment across time and domain* — a held med never restarted, a lab slope no single value flags, a consult rec closed in the letter in different words. We proved it both directions: we surfaced four real misses and correctly *cleared* thirty, including a look-alike a checker would false-alarm on."

**"Why an agent, not a scripted pipeline?"**
> "The orchestration *is* deterministic — loading notes, threading entities, ranking. The hard part is open-ended: does this later note actually close this thread, maybe in different words? No rule captures that. Code where it should be reliable, the model where it must reason."

**"What happens when it's wrong? A hallucinated finding could hurt someone."**
> "It never closes or decides — it surfaces a question with the evidence, and a human approves any action. Every claim carries a verbatim citation validated automatically as an exact substring: ninety-eight of ninety-eight on this chart, zero hallucinated. Unvalidated claims are dropped before you ever see them."

**"How do you know it's right — did you measure anything?"**
> "The chart is hand-authored, so the planted threads are ground truth, and our eval harness scores against them: precision 1.0 on the surfaced set, the suppress case correctly cleared, all citations validating. A reproducible gate, not a vibe."

**"Won't 4 findings plus 30 cleared become alert fatigue / a dashboard?"**
> "The opposite — the cap is the point. It ranks by consequence, shows four, and collapses the thirty it cleared. The 30 aren't alerts; they're the proof it stayed quiet on what was handled. Precision over recall, by design."

**"What did you build today vs. pre-existing?"**
> "Everything in the repo — the whole-chart pipeline, entity threading, the reasoning prompt, the eval harness, the UI — built today; here's the public repo. We reuse the Anthropic SDK, Pydantic, FastMCP, and Claude. All data synthetic, no PHI."

**"HIPAA/PHI — where does the data go?"**
> "Demo is fully synthetic. In production it runs inside the covered boundary where ambient documentation already lives — no data leaves a safe path."

**"Where does it sit in the day / who pushes the button?"**
> "It runs at discharge on the chart that's already there — no new workflow — and produces a short, ranked queue; the clinician answers or approves. Optionally the approved outreach goes to the patient."

**"As Claude gets smarter, does this get better or does your edge vanish?"**
> "Better — the reconciliation *is* the model's reasoning, so every capability gain raises our precision and recall directly. We're a harness around frontier reasoning, not a workaround for it."

**"Are you replacing clinical judgment?"**
> "Supporting it. We never decide; we surface an unclosed loop with the evidence and ask. The human controls everything that touches the patient."

*If you don't know an answer: say the honest version and offer to follow up. Never bluff a domain expert.*

---

## 1-minute video cut (condensed — record after the freeze)
*(Visuals: bookend → apixaban card + question → creatinine trend → the CLEARED (30) count → the Approve click.)*

> "Discharge isn't the end of a hospital stay — it's the start of the patient's journey home, and it's where things fall through. No clinician re-reads all fourteen days of a chart at that moment. Safety Net does. On this admission it considered thirty-four threads, cleared thirty that were handled, and surfaced four that weren't. Here's the one that matters: this patient's blood thinner for atrial fibrillation was held for a procedure Day 1 — and never restarted. The discharge list keeps his other meds but drops it. He's going home off stroke prevention, and nothing flagged it. No order to match — Safety Net connected three documents across the stay and asks: should apixaban be restarted? It also caught a kidney-function trend no single value flags, a lung nodule with no follow-up, and cultures left pending — and it *suppressed* a colonoscopy 'miss' that was actually closed in the PCP letter. Precision 1.0; every one of ninety-eight citations verbatim. It drafts the notification; a clinician approves; nothing sends itself. The chart had the answer the whole time. No one had read all of it. Now something has."

---

## Pipeline fixes required (so the UI matches this script)
1. **De-duplicate the apixaban thread.** The agent currently surfaces apixaban **twice** (two near-identical High/UNCONFIRMED cards). Collapse to one during entity threading / finding assembly — a judge will notice a duplicate, and it's occupying two of the four slots.
2. **That dedup lifts the creatinine thread into the surfaced top-4** (it's currently rank 5, in cleared). The creatinine "value-over-threshold" beat depends on it being surfaced — confirm it lands at rank 4 after the fix, or bump `TOP_N` deliberately and say why.
3. **Bookend must show the cleared count + citation total** (`34 considered · 4 surfaced · 30 cleared · 98/98 citations`) — today the UI only shows the surfaced count.
4. **Cleared section:** render the count prominently, collapsed, with the colonoscopy reachable as the suppress example.

## Pre-flight checklist
- [ ] `python -m safety_net.eval_harness` green (precision 1.0, suppress cleared, citations valid) — numbers memorized.
- [ ] Apixaban appears **once**; creatinine is **surfaced** (top-4); bookend shows `34 · 4 · 30 · 98/98`.
- [ ] `ui/whole_chart.html` renders offline from `data/chart/cache/`; Approve works.
- [ ] Apixaban timeline highlights land on all four citations; creatinine shows Day 1 / 5 / 12.
- [ ] Colonoscopy reachable in CLEARED, cited to the PCP letter.
- [ ] Cold-open clip pre-recorded (no live run on stage).
- [ ] Deliverable in ≤3:00 with the close line intact; 1-min video link opens logged-out.
