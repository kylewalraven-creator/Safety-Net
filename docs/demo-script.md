# Safety Net — Demo Script (live 3-min + Q&A)

## Summary — read this first
- **What it is:** Safety Net — a retrospective diagnostic-safety agent that sweeps a backlog of *correct* radiology reports and surfaces the follow-up recommendations that were never actually addressed, each with a verbatim citation and a specific, human-answerable question.
- **Who's presenting:** you deliver this in the **first-person voice of a practicing physician** — the pain is *yours*, not a vendor's. It grounds every claim in "this is what happens to my patients."
- **The arc (~2:50):** cold open (the failure) → **Hero A** *looks closed, isn't* → escalate → **Hero B** *looks open, is closed* → suppress → one human-approved action → fixed close.
- **The two heroes:** A = a 9 mm left-upper-lobe nodule an order-matcher "closes" on a later chest CT that never mentions it → **ESCALATE**. B = a nodule flagged overdue by date logic, but a later PET/CT already called it benign → **SUPPRESS** (no false alarm).
- **On screen:** one static page; the only live interaction is the **Approve** button on Hero A. If the network dies, the cached render is byte-identical — keep talking.
- **"Why an agent" (reflex answer):** multi-step reasoning over messy documents — it reconciles each finding across five axes and drafts the outreach; it's not a keyword match or a date check.
- **The close (never cut it):** *"Every report here was right. The system around it failed. We built the system."*

---

## How to use this
- **Specifics are filled from the real hero cases** (`data/heroes/case_a.json`, `case_b.json`) so the narration matches exactly what renders on screen. If you edit the hero JSON, re-check the numbers here.
- **The UI is a single static page** (`ui/index.html`), not a click-through. Everything — both cases, the five-axis traces, the highlighted evidence, the escalation question, the drafted action — is pre-rendered and visible on load. The **only** interactive element is the **Approve** button on Case A. The beats below map to *scroll-and-point* regions of that one page, not to clicks. Rehearse the scroll path and where you point.
- **If the live API call hangs, flip to the cached response and keep talking** — the narration is identical, only the source of the result changes. Don't call attention to it. If everything dies, the 1-min video is queued as the ultimate fallback.
- **Deliver in the first-person voice of a physician** — the narration is a clinician describing a failure they see on their own patients, not a vendor pitching a product. Say "my patients," "I've had this happen." If two of you present, keep that single physician voice consistent across the handoffs; rehearse them.
- **Rehearse to ~2:50** so you have buffer. The close line is fixed — never cut it, never rush it.
- **Tone for the room (Ricci is in it):** when you reference "order-matching," say it neutrally — it describes real, good products, including his old one. The contrast is an honest technical distinction, not a takedown. Confidence without arrogance; precision over hype.

---

## THE SCRIPT

### Cold open — establish the failure (0:00–0:15)
[Screen: a **pre-recorded** clip of the sweep's tool-call lines streaming, or simply the cached `index.html` at the top — **never a live sweep** (the page makes zero network calls, so wifi loss is survivable). Land on the header + bookend line.]

> "I'm a physician. Every year, patients get harmed — not because a scan was misread, but because a follow-up buried in a *correct* report was never acted on. Studies routinely find fewer than half of recommended follow-up imaging is ever completed. I've watched it happen."

*(Have a citable source for that statistic ready — a domain expert will ask. If you can't source it live, drop the number and keep the sentence.)*

[Point at the bookend line: "Swept 10 finished reports · 2 hero recommendation(s) reconciled live."]

> "This is a backlog of finished reports — ten here so you can see it, but the sweep runs the same over ten thousand. Every one read correctly. My agent read them all and asked the question no one has time to: not whether the scan got done, but whether the finding was ever looked at again. Two fell through — here's the first."

*(Thesis landed. Move straight to Hero A — aim to have the escalate reveal on screen by ~0:45.)*

### Hero beat — Case A: looks closed, isn't (0:15–1:35)
[Scroll to the first case: "Looks closed, isn't (escalate)" — Margaret Ellison · PT-A-2213. Point at the source report (highlighted).]

> "Here's one. October 2024: a 9 mm nodule in the left upper lobe. The radiologist recommended a follow-up CT chest in six months."

> "An order-matching tracker asks one question — was a chest CT done? And one was."

[Point at the later study card — the March 2025 chest CT.]

> "March 2025, a chest CT. Order matched, loop closed, case closed. That's how order-matching works."

*(Beat. Then:)*

> "Watch what our agent does instead."

[Point at the five-axis reasoning trace, already rendered below the reports.]

> "This is why it has to be an agent, not a rule: it *reads* both reports and reasons about whether the second actually addressed the first — across five axes. Modality: a chest CT can assess a nodule — pass. Anatomy: it covered the left upper lobe — pass. But acknowledgment —"

*(Pause. Point at the highlighted March 2025 report — nothing about the nodule is marked.)*

> "— the March 2025 scan never mentions the nodule. It was a PE study, ordered for shortness of breath and cough. It imaged the lung, but nobody looked at the nodule."

[Point at the closure banner — it reads "Closure state: ESCALATE".]

> "So the agent doesn't close it. It escalates — with the exact question a human needs to answer:"

[Point at the escalation box; read it. (Exact wording is model-generated — read what's on screen; it will name the March 2025 CT and the October 2024 nodule.)]

> "'A chest CT was performed in March 2025 but doesn't mention the October 2024 left-upper-lobe nodule — was it reassessed? Confirm or deny.'"

*(Beat — this is the moment. Let it sit.)*

> "That's the difference. A scan being *done* is not the same as the finding being *addressed*. That gap is where patients fall through — and it's invisible to anything that just matches orders."

### Contrast beat — Case B: looks open, is closed (1:40–2:20)
[Scroll to the second case: "Looks open, is closed (suppress)" — Harold Nkemelu · PT-B-7749. Point at the rec-sub line — it reads "naive date logic: OVERDUE".]

> "Now the opposite failure. June 2024: an 11 mm nodule in the right middle lobe, follow-up CT recommended in three months. This patient's flagged overdue by simple date logic — the window's passed, no matching CT. An alarm-based system pages the care team right now."

[Point at the highlighted PET/CT card — the September 2024 study.]

> "But our agent finds this —"

*(Point at the highlighted benign line.)*

> "— a PET/CT three months later that characterized the same 11 mm nodule as benign. The question's already answered."

[Point at the closure banner — it reads "Closure state: SUPERSEDED".]

> "So it closes the loop and stays silent. No false alarm."

*(Beat.)*

> "Catching real misses and suppressing false ones is the same capability — reasoning about what actually happened, not pattern-matching dates and orders. And this half is the one an order-matcher can't do: there's no order to match, so it either pages a false alarm or stays blind. Reasoning is what lets us stay quiet here."

### Action beat — human-gated closure (2:20–2:50)
[Scroll back up to Case A's drafted action (labeled "Drafted … (human-gated)"). This is the one real click in the demo.]

> "Back to the patient who fell through. The agent drafts the outreach to re-engage them — but it doesn't send anything on its own. A clinician reviews and approves."

[CLICK — the Approve button. The audit line appears and the button disables.]

> "Approved, logged, audit trail intact. Autonomous where it's safe — reading and reasoning. Human-gated where it matters — anything that touches a patient. And because it's all an MCP server, it runs on this backlog with no EHR integration. It could run on yours Monday."

### Close (2:50–3:00)
*(Stop moving. Look up. Deliver clean, then stop talking.)*

> "Every report here was right. The system around it failed. We built the system."

---

## Q&A (rehearse these — ~15–20 sec each; answer the question, then stop)

**"How is this different from Rad AI Continuity / PowerScribe Follow-up Manager?"**
> "Order-matching systems confirm a scan was *ordered and done* — that's genuinely useful. But two things they structurally can't do: catch a later scan that imaged the area yet never mentions the finding, and *suppress* a false alarm when the finding was already resolved in different words. You just saw both — the escalate and the suppress. The wedge is reasoning about acknowledgment, not matching orders."

**"What's your false-negative rate — what about the ones you miss?"**
> "We don't silently close anything ambiguous. If we can't confirm a finding was addressed, it escalates with a specific question instead of closing. The goal isn't perfect extraction — it's making misses *visible* instead of losing them. A miss surfaces as a question, not a silent closure."

**"Can you really trust an LLM for this clinically?"**
> "It's not diagnosing or recommending treatment. It's reasoning about document equivalence — did study B address finding A — and every verdict has a verbatim citation behind it a clinician can verify in one click. It's a reconciliation engine with an audit trail, not an autonomous clinician."

**"Is this real data or synthetic?"**
> "Synthetic — hand-authored to show the reasoning cleanly, no PHI. The pipeline's real; on actual reports the extraction and reconciliation run identically."

**"Does this generalize beyond radiology?"**
> "The reasoning is specialty-agnostic — the same five-axis logic applies to a pathology re-excision or a GI surveillance interval; only the clinical taxonomy changes. We built radiology as the beachhead because it's the best-documented, but nothing in the architecture is radiology-specific."

**"Won't this create alert fatigue?"**
> "We just showed the answer — the same reasoning that catches misses suppresses false alarms. We only surface what we genuinely can't confirm, not everything that's technically overdue."

**"How much of this did you build today?"**
> "All of it — here's the public repo. The agent pipeline and the reconciliation reasoning are the work; the data we authored today to demo it."

*If you don't know an answer: say the honest version and offer to follow up. Never bluff a domain expert.*

---

## 1-minute video cut (condensed — record after the freeze)
*(Visuals: cut between four regions of the static page — (1) the bookend line, (2) Case A's five-axis trace + escalation box, (3) Case B's SUPERSEDED banner, (4) the Approve click on Case A. Record the voiceover separately and cut visuals to it.)*

> "Patients are harmed when a follow-up buried in a *correct* radiology report is never acted on. [sweep] Our agent reads a backlog of finished reports and pulls every recommendation. Here's one — an October 2024 lung nodule, 9 mm in the left upper lobe, follow-up CT recommended. A chest CT was done in March 2025, so an order-matching tracker closes the case. But our agent checks whether the nodule was actually *addressed*: modality and anatomy pass — but that March scan never mentions the nodule. So it doesn't close it. It escalates with the exact question: was the nodule reassessed? [Case B] It also suppresses false alarms — an 11 mm nodule flagged overdue, but a benign PET/CT here means no page. [action] For real misses, it drafts the outreach for a clinician to approve — human-gated, fully audited. It's an MCP server, so it runs with no EHR integration. Every report was right. The system around it failed. We built the system."

---

## Pre-flight checklist (verify before you walk into the room)
- [ ] Both hero cases produce the right verdict live **and** from cache (A → `Closure state: ESCALATE` + question; B → `Closure state: SUPERSEDED`).
- [ ] The escalation question text reads cleanly and names Case A's specifics (March 2025 CT / October 2024 left-upper-lobe nodule). It's model-generated — read what's actually on screen, not this doc's example.
- [ ] Evidence highlighting lands on the right source text in both cases (no whitespace/quote mismatch) — especially the "no mention of the nodule" gap in Case A's March 2025 report.
- [ ] The bookend line renders a real count ("Swept 10 finished reports · 2 hero recommendation(s) reconciled live") — not a placeholder.
- [ ] The **Approve** button on Case A works (reveals the audit line, disables itself).
- [ ] The scroll path — bookend → Case A → Case B → back to Case A's action — runs without a dead end.
- [ ] Cached-fallback works with wifi off (populate `data/cache/` first via `python -m safety_net.sweep --write-cache`).
- [ ] 1-min video renders and its link opens logged-out.
- [ ] You can deliver the whole thing in ≤3:00 with the close line intact.
