# Safety Net — Demo Script (live 3-min + Q&A)

## How to use this
- **Fill the [brackets]** with your actual hero-case specifics (dates, nodule size, location) — keep them different from the prompt's example values so nothing looks hard-coded.
- **Click-path is ≤5 clicks**, mapped to beats below. Rehearse the exact sequence; never improvise on stage.
- **If the live API call hangs, flip to the cached response and keep talking** — the narration is identical, only the source of the result changes. Don't call attention to it. If everything dies, the 1-min video is queued as the ultimate fallback.
- **Split the delivery however you two decide** — one person reads it clean, or split by beat with one narrating and one driving. Either works; just rehearse the handoffs.
- **Rehearse to ~2:50** so you have buffer. The close line is fixed — never cut it, never rush it.
- **Tone for the room (Ricci is in it):** when you reference "order-matching," say it neutrally — it describes real, good products, including his old one. The contrast is an honest technical distinction, not a takedown. Confidence without arrogance; precision over hype.

---

## THE SCRIPT

### Cold open — establish the failure (0:00–0:20)
[Screen: the backlog view, ready to sweep.]

> "Patients get harmed every year — not because a scan was misread, but because a follow-up recommendation buried in a *correct* report was never acted on."

[CLICK 1 — start the sweep. Count ticks up.]

> "This is a backlog of [N] finished radiology reports. Every one was read correctly. Our agent is reading all of them right now and pulling out every follow-up recommendation."

[Count settles.]

> "It found [X] recommendations. The real question isn't whether these scans got done — it's whether the finding was ever actually looked at again."

*(That last line is your thesis. Land it, then move.)*

### Hero beat — Case A: looks closed, isn't (0:20–1:40)
[CLICK 2 — open Case A. Show the source report.]

> "Here's one. [Month Year]: a [6 mm] nodule in the [right upper lobe]. The radiologist recommended a follow-up CT in six months."

> "A naive tracker asks one question — was a chest CT done? And one was."

[The later study appears.]

> "[Month Year]. Order matched, loop closed, case closed. That's how order-matching works."

*(Beat. Then:)*

> "Watch what our agent does instead."

[CLICK 3 — run reconciliation. The reasoning trace renders.]

> "It checks whether that later scan actually *addressed* the nodule — across five axes. Modality: a chest CT can assess a nodule — pass. Anatomy: it covered the [right upper lobe] — pass. But acknowledgment —"

*(Pause. Point at the highlighted source text.)*

> "— the [February] report never mentions the nodule. It was ordered for a cough. It imaged the lung, but nobody looked at the nodule."

> "So the agent doesn't close it. It flags it UNCONFIRMED and escalates — with the exact question a human needs to answer:"

[Point at the escalation question; read it.]

> "'A chest CT was performed in [February] but doesn't mention the [November] nodule — was it reassessed? Confirm or deny.'"

*(Beat — this is the moment. Let it sit.)*

> "That's the difference. A scan being *done* is not the same as the finding being *addressed*. That gap is where patients fall through — and it's invisible to anything that just matches orders."

### Contrast beat — Case B: looks open, is closed (1:40–2:20)
[CLICK 4 — open Case B.]

> "Now the opposite failure. This patient's flagged overdue by simple date logic — a nodule follow-up recommended, the window's passed, no matching CT. An alarm-based system pages the care team right now."

[Run reconciliation — cached or live. Trace renders.]

> "But our agent finds this —"

[Point at the highlighted PET/CT text.]

> "— a PET/CT three months later that characterized the same nodule as benign. The question's already answered. So it closes the loop and stays silent. No false alarm."

*(Beat.)*

> "Catching real misses and suppressing false ones is the same capability — reasoning about what actually happened, not pattern-matching dates and orders."

### Action beat — human-gated closure (2:20–2:50)
[CLICK 5 — back to Case A, the action draft.]

> "Back to the patient who fell through. The agent drafts the outreach to re-engage them — but it doesn't send anything on its own. A clinician reviews and approves."

[Approve. Audit entry flashes.]

> "Approved, logged, audit trail intact. Autonomous where it's safe — reading and reasoning. Human-gated where it matters — anything that touches a patient. And because it's all an MCP server, it runs on this backlog with no EHR integration. It could run on yours Monday."

### Close (2:50–3:00)
*(Stop moving. Look up. Deliver clean, then stop talking.)*

> "Every report here was right. The system around it failed. We built the system."

---

## Q&A (rehearse these — ~15–20 sec each; answer the question, then stop)

**"How is this different from Rad AI Continuity / PowerScribe Follow-up Manager?"**
> "They match orders and track appointments — they'll tell you a chest CT was scheduled and done. We reason about whether the finding was actually *addressed*. The nodule that never got mentioned is invisible to order-matching — and that's exactly the case we catch. That distinction is the failure mode."

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
> "Patients are harmed when a follow-up buried in a *correct* radiology report is never acted on. [sweep] Our agent reads a backlog of finished reports and pulls every recommendation. Here's one — a [2024] lung nodule, follow-up CT recommended. A chest CT was done in [2025], so an order-matching tracker closes the case. But our agent checks whether the nodule was actually *addressed*: modality and anatomy pass — but the report never mentions the nodule. So it doesn't close it. It escalates with the exact question: was the nodule reassessed? [Case B] It also suppresses false alarms — a benign PET/CT here means no page. [action] For real misses, it drafts the outreach for a clinician to approve — human-gated, fully audited. It's an MCP server, so it runs with no EHR integration. Every report was right. The system around it failed. We built the system."

---

## Pre-flight checklist (verify before you walk into the room)
- [ ] Both hero cases produce the right verdict live **and** from cache (A → escalate + question; B → superseded).
- [ ] The escalation question text reads cleanly and matches Case A's specifics.
- [ ] Evidence highlighting lands on the right source text in both cases (no whitespace/quote mismatch).
- [ ] The 5-click path runs start-to-finish without a dead end.
- [ ] Cached-fallback toggle works with wifi off.
- [ ] 1-min video renders and its link opens logged-out.
- [ ] You can deliver the whole thing in ≤3:00 with the close line intact.
