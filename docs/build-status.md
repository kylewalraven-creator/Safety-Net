# Safety Net — Build Status & Handoff

_As of 2026-07-18. Branch: `claude/safety-net-repo-setup-f3yb0f`._

This is the continuity doc for a fresh session. It captures what exists, what's
been verified, the decisions made (and why), and what's left. Pair it with
`CLAUDE.md` (invariants + quickstart) and `docs/demo-runbook.md` (the demo).

> **Scope / headline.** The repo's current **headline build and canonical demo is
> Whole-Chart Review** (the most recent pivot; script `docs/demo-script.md`, UI
> `ui/render_chart.py`). This handoff documents the original **radiology Safety
> Net**, now the **retained fallback** — the status below is still accurate for it.
> Whole-chart status is in **"Whole-Chart Review — status"** just below.

## Current state — built & verified

The full first slice from `docs/master-blueprint.md` §5 is implemented. Verified
end-to-end on a machine with a real key:

- **`scripts/preflight.py`: 11/11 pass live** — SDKs (anthropic 0.117, pydantic
  2.13, fastmcp 3.4), models round-trip the contract's worked examples, prompt is
  verbatim, hero data loads, key present, Opus + Haiku live pings OK.
- **Case A (live): `UNCONFIRMED` → `escalate`** with a specific Confirm/Deny
  question and a drafted provider message. Acknowledgment axis correctly fails on
  the later CT that imaged the lung but never mentions the nodule.
- **Case B (live): `SUPERSEDES` → `superseded`**, no escalation (PET/CT
  characterized the nodule benign → false alarm suppressed).
- **`tests/test_offline.py`: 8/8 pass** (no key needed) — models, anatomic
  overlap, overdue math, JSON repair, evidence highlighting, UI render, and the
  Opus-omits-temperature guard.
- **UI** renders from the committed cache with 9 evidence highlights, both closure
  banners (ESCALATE / SUPERSEDED), Case A's escalation question, and a working
  Approve → audit line.
- **Real hero responses captured** to `data/cache/case_a.json` / `case_b.json`
  and committed as the offline fallback.
- **No secrets tracked** — only `.env.example`.

Commit sequence on the branch: scaffold → docs → models → client/prompts →
pipeline → mcp → data → ui → scripts/tests → **temperature fix** → **cache** →
(this handoff). Deep's synthetic FHIR dataset commit also sits on the branch.

## Whole-Chart Review — status (headline build)

The pivot workflow (net-new, on the same engine) is built and self-verifies
**offline** (no key needed). Verified in this repo:

- **`python -m safety_net.eval_harness`: gate PASS** — precision **1.0** / recall
  **1.0** on the ground-truth manifest, **9/9 citations** validate as exact
  substrings, and every live-set check passes (H4 → UNCONFIRMED/High, H1 surfaces,
  H_SUPPRESS suppressed as CONFIRMED_ADDRESSED cited to the PCP letter).
- **`python -m safety_net.chart_review --use-cache`: 4 threads surfaced, 1 cleared**
  — apixaban / creatinine / nodule / blood cultures surface; the colonoscopy
  look-alike is correctly suppressed (closed as "lower endoscopy" in the PCP letter).
- **`tests/test_whole_chart.py`: 12/12 pass** (no key).
- **Live heroes:** H4 (held apixaban never restarted) + H_SUPPRESS (colonoscopy);
  H1/H2/H3 precompute. Offline cache committed in `data/chart/cache/`.
- **Contract:** Section 3 of `models.py` (additive; Sections 1–2 untouched, so the
  radiology fallback still runs). Pipeline is in the `CLAUDE.md` pivot section.

## Decisions & rationale (don't "fix" these without reading)

1. **Contract source = `docs/reconciliation-prompt.md`, not blueprint §4.** The
   blueprint sketches a looser `recommendation` (with `patient_id`, `status`); the
   prompt is the frozen I/O contract and the blueprint defers to it. `models.py`
   §1 matches the prompt exactly. Patient linkage is derived via
   `recommendation.source_id → report.patient_id`, not carried on the contract.
2. **`temperature` dropped for Opus.** The prompt doc suggests temp ~0.0–0.2, but
   `claude-opus-4-8` now returns HTTP 400 for `temperature` (preflight caught it).
   `client._request_params` strips it for Opus; Haiku still uses 0.0. The live API
   is authoritative over the doc here.
3. **`actions.py` drafts a `provider_message` centered on the escalation
   question.** The brief said "produce the human-answerable question"; the spec/
   demo frame the action as drafting outreach. The draft operationalizes the
   reconciliation's `escalation.question` into a clinician-facing message. Retarget
   to a patient letter if desired.
4. **Hero specifics differ from the prompt's worked examples on purpose** (9 mm
   left-upper-lobe / 11 mm right-middle-lobe vs. the doc's 6 mm RUL / 8 mm LLL), per
   the prompt doc's note and the demo script — so the model is reasoning, not
   pattern-matching the prompt.
5. **`scripts/preflight.py` was created** (brief step 12 said to move one *if
   present*; none was, and the "Then" section calls for running it).
6. **fastmcp v3 installed** (pin `>=2.0`); `from fastmcp import FastMCP` +
   `@mcp.tool` are stable.

## Stubbed / intentionally minimal

- **UI** is a static single-file stub (`ui/render.py` → `ui/index.html`); the
  Approve button reveals the audit line client-side, while the real
  `approve_action` + `AuditEvent` run in Python at render time. Not a server app —
  and not a dashboard (the aggregate is a one-line bookend, by design).
- **MCP server** is a thin wrapper (12 tools — 7 Safety Net + 5 whole-chart), off
  the live demo path.
- **Filler** is 6 normal reports (sweep count = 10 total). Pad `data/filler/` if a
  bigger "swept N" number is wanted; it's cosmetic and needs no reconciliation.

## Team / key setup

- The key belongs **only** in each dev's local gitignored `.env`. Share the value
  via a shared **password manager** (1Password/Bitwarden).
- Do **not** put it in the Claude Code cloud environment's "environment variables"
  field — that's plaintext and visible to anyone using the environment (the UI
  says so). Consequence: cloud/agent sessions can't make the live calls; run them
  on a laptop that has the key. The offline cache covers demos either way.

## Collaborators

- **Kyle Walraven** (`kylewalraven-creator`) — repo owner.
- **Deep Nana** (`deep.nana@abridge.com`) — pushed `data/synthetic-ambient-fhir-25/`
  (synthetic Synthea/LLM FHIR dataset). Already has push access. That dataset is
  not consumed by the safety-net sweep.

## Next steps (aligned to `docs/run-of-day.md`)

- Rehearse the demo (`docs/demo-runbook.md`); record the 1-min video.
- Optional: pad `data/filler/` for a larger sweep number.
- Freeze features at 3:45; submit by 5:00 (repo already public; README covers
  what / architecture / how-to-run; collaborators added).
- If picking up fresh: `pip install -e .`, `cp .env.example .env` (add key),
  `python scripts/preflight.py`, then continue.
