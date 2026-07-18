# Safety Net — Demo Runbook (radiology two-hero — the fallback demo)

> **This is the retained _fallback_ demo (radiology two-hero, renders
> `ui/index.html`).** The current **headline/canonical demo is Whole-Chart
> Review** — script `docs/demo-script.md`, rendered by `ui/render_chart.py` →
> `ui/whole_chart.html`. Keep this one rehearsed as the backup.

The click-by-click guide for the live demo. This matches what the **built UI
actually shows** — a **pre-rendered static page** (both cases' reasoning is
already on screen). You scroll through it and make **one real click (Approve)**.
The page makes **zero network calls during the demo**, so wifi loss is survivable.

For the full narration and timing, see `docs/demo-script-two-hero.md` (the
radiology script); this runbook maps those beats onto the real artifacts.

## One-time setup (before dry runs)
```bash
cd Safety-Net
source .venv/bin/activate
ANTHROPIC_API_KEY= python ui/render.py     # cached render: offline, instant, identical every run
open ui/index.html
```
The empty `ANTHROPIC_API_KEY=` forces a render from the committed cache, so every
dry run is byte-identical and needs no wifi/tokens. In the browser: **Cmd-+** for
readability, scroll to the top.

**Between dry runs:** **Cmd-R** to reload — resets the Approve button.

## The demo — 5 beats, ~3:00

### Beat 1 · Cold open (0:00–0:20) — top of page
- **Show:** header + bookend line: _"Swept 10 finished reports · 2 hero
  recommendations reconciled."_
- **Say:** "Patients get harmed when a follow-up buried in a *correct* radiology
  report is never acted on. This is a backlog of finished reports — every one read
  correctly. The question isn't whether the scans got done. It's whether the
  finding was ever looked at again."

### Beat 2 · Hero A — catch the miss (0:20–1:40) — scroll to "Looks closed, isn't (escalate)"
- **Point at the recommendation:** "October 2024 — a 9 mm nodule, left upper lobe.
  Follow-up CT recommended in six months."
- **Point at the "Later study A-R2" card:** "A naive tracker asks one thing: was a
  chest CT done? One was — March 2025. Order matched, case closed."
- **Walk the axis badges:** "Our agent checks whether that scan actually *addressed*
  the nodule. Modality — a chest CT can assess it: pass. Anatomy — it covered the
  lung: pass. Acknowledgment —"
- **Point at the yellow highlight in A-R2** (_"Mild bronchial wall thickening. No
  lobar consolidation. No pleural effusion."_): "— the March report never mentions
  the nodule. It was ordered for shortness of breath. It imaged the lung, but nobody
  looked at the nodule."
- **Point at the red ESCALATE banner + escalation box, read it:** "So it doesn't
  close it. It escalates, with the exact question a human answers: *was the 9 mm
  left-upper-lobe nodule reassessed on the March 18 study? Confirm or deny.* A scan
  being *done* is not the finding being *addressed* — and that gap is invisible to
  order-matching."

### Beat 3 · Contrast B — suppress the false alarm (1:40–2:20) — scroll to "Looks open, is closed (suppress)"
- **Point at "naive date logic: OVERDUE":** "The opposite failure. Flagged overdue
  by date logic — window passed, no matching CT. An alarm system pages the team
  right now."
- **Point at the PET/CT highlight + green SUPERSEDED banner:** "But our agent finds
  a PET/CT three months later that characterized the same nodule as benign — *the
  previously noted 11 mm right middle lobe nodule.* The question's already answered,
  so it stays silent. No false alarm. Same reasoning, both directions."

### Beat 4 · Human-gated action (2:20–2:50) — scroll back up to Case A's "Drafted provider_message"
- **Say:** "Back to the patient who fell through. The agent drafts the outreach —
  but sends nothing on its own."
- **CLICK → [Approve].** Audit line appears (_"Approved · Dr. Reviewer (demo) · … ·
  logged to audit trail"_).
- **Say:** "A clinician approves. Logged, audit trail intact. Autonomous where it's
  safe — reading and reasoning. Human-gated where it matters. And it's an MCP
  server, so it runs on this backlog with no EHR integration — it could run on yours
  Monday."

### Beat 5 · Close (2:50–3:00)
- **Say (stop moving, look up):** "Every report here was right. The system around it
  failed. We built the system."

## Optional flourish — the live "thinking" moment
If wifi is solid and you want judges to watch the agent reason in real time, open
Beat 2 in the **terminal** first:
```bash
python scripts/smoke_case_a.py
```
Opus "thinks" ~10s, then prints the five-axis trace and the escalation — then cut
to the browser for the visual. Skip it if the network is shaky; the browser carries
the whole demo alone.

## Reliability notes
- The demo page is **offline** once rendered — wifi-loss insurance.
- Don't re-render with the key set right before showing (live wording varies
  run-to-run). Keep the **cached render** for consistency.
- Only real click = **Approve** (well under the ≤5-click target); the rest is
  scrolling.
- Ultimate fallback if everything dies: the 1-min video (see `docs/run-of-day.md`).

## Pre-run checklist
- [ ] `ui/index.html` open, zoomed, scrolled to top
- [ ] Case A shows **ESCALATE** (red), Case B shows **SUPERSEDED** (green)
- [ ] Highlights land on the right text in both cases
- [ ] Approve reveals the audit line; **Cmd-R** resets it
- [ ] You land the close line by ~2:50
