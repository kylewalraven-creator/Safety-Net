# CLAUDE.md — Safety Net

Safety Net is a **retrospective diagnostic-safety agent**: it sweeps finished
radiology reports, extracts follow-up recommendations, and reasons about whether
each was **actually addressed** by a later study (acknowledgment) — not merely
whether a later study happened. A capable scan that never mentions the finding
is **UNCONFIRMED → escalate with a specific, human-answerable question**, never
silently closed. One-day hackathon project (Abridge × Anthropic × Lightspeed).

> **New session, start here.** The **headline build and canonical demo is
> Whole-Chart Review** (the most recent pivot). Read the **"Whole-Chart Review
> pivot"** section below, `docs/demo-script.md` (the demo — source of truth for the
> UI), and the whole-chart design docs (`whole-chart-schema-contract.md` [frozen],
> `-build-plan`, `-iteration`, `-reasoning-prompt`, `-synthetic-data-spec`) first.
> The original **radiology Safety Net is the retained fallback**: handoff in
> `docs/build-status.md`, runbook `docs/demo-runbook.md`; design docs
> `master-blueprint.md`, `reconciliation-spec.md`, `run-of-day.md`,
> `reconciliation-prompt.md`.

## Architecture
Deterministic code sweep loads reports → **Haiku** extracts recommendations +
studies → code matches candidate later studies (same patient, later date,
anatomic overlap) → **Opus** reconciles each recommendation across five axes
(modality adequacy, anatomic coverage, **finding acknowledgment — gates the
verdict**, temporal adequacy, terminal event), emitting strict JSON with a
verbatim citation behind every determination → code state machine + Opus
action-drafting (human approve → audit). All wrapped as a thin FastMCP server;
the live demo/UI calls core Python directly (MCP is off the demo path).

## Critical invariants — do NOT break these
1. **Frozen contract.** `src/safety_net/models.py` (Section 1) and
   `src/safety_net/prompts/reconciliation_system.txt` are transcribed **verbatim**
   from `docs/reconciliation-prompt.md`. Do not add / rename / reorder contract
   fields or edit the prompt text — two people build against it in parallel.
   `scripts/preflight.py` asserts the prompt is verbatim and that the models
   round-trip the doc's own worked examples.
2. **Model IDs are settled — do not substitute:** Opus `claude-opus-4-8`
   (reconcile + action-drafting), Haiku `claude-haiku-4-5-20251001` (bulk extract).
3. **Opus 4.8 rejects `temperature`** (HTTP 400 — deprecated for that model).
   `client._request_params` strips it for models in `_NO_TEMPERATURE_MODELS`.
   Never re-add `temperature` to an Opus call. Haiku keeps `temperature=0.0`.
4. **No secrets in the repo.** `.env` is gitignored; only the placeholder
   `.env.example` is tracked. The key lives in each dev's local `.env` + a shared
   password manager — **NOT** in the Claude Code cloud-env "environment variables"
   field (that field is plaintext, visible to anyone using the environment).

## Quickstart
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env                 # add a real ANTHROPIC_API_KEY (Opus + Haiku)
python scripts/preflight.py          # SDK / key / model checks + live pings
python scripts/smoke_case_a.py       # Case A live -> expect escalate + question
python -m safety_net.sweep --write-cache   # reconcile both heroes live, cache results
python ui/render.py                  # render ui/index.html
python -m safety_net.mcp_server      # thin MCP server (credibility exhibit)
```

## Offline demo path (no wifi / no key)
Real hero responses are committed in `data/cache/`. Render from them:
```bash
ANTHROPIC_API_KEY= python ui/render.py     # empty var forces the cached render
python -m safety_net.sweep --use-cache
```
`ui/index.html` is a **static page** (zero network calls during the demo) and is
gitignored — regenerate it, don't commit it.

## Layout
- `src/safety_net/`: `models.py` (contract), `client.py`, `prompts/`,
  `extract.py` (Haiku), `reconcile.py` (Opus 5-axis), `actions.py` (Opus draft +
  approve/audit), `sweep.py` (deterministic orchestration + matching + overdue +
  cache), `mcp_server.py` (thin FastMCP, 12 tools — 7 Safety Net + 5 whole-chart).
- `data/heroes/`: Case A (→ escalate), Case B (→ superseded). `data/filler/`:
  sweep volume (6 normal reports). `data/cache/`: committed real hero responses.
- `scripts/preflight.py`, `scripts/smoke_case_a.py`; `tests/test_offline.py`
  (runs with no key); `ui/render.py` (static two-case UI stub).
- `data/synthetic-ambient-fhir-25/`: teammate Deep's synthetic FHIR dataset —
  **not** consumed by the sweep (which loads only `data/heroes` + `data/filler`).

## Status (2026-07-18) — Safety Net (radiology, the fallback demo)
Full first slice built and verified end-to-end: preflight 11/11 live, Case A →
escalate + question, Case B → superseded, offline tests 8/8, UI renders with
highlighted citations. Working branch: `claude/safety-net-repo-setup-f3yb0f`.
See `docs/build-status.md` for decisions, rationale, what's stubbed, and next steps.

## Whole-Chart Review pivot — the headline build (merged into `claude/safety-net-repo-setup-f3yb0f`)
A net-new workflow on the same engine: review a **14-day admission at discharge**
and surface only the threads that fell through (escalate), while **suppressing**
look-alikes closed in different words (equivalence, not keyword match). Frozen
contract: `docs/whole-chart-schema-contract.md` → implemented as **Section 3** of
`models.py` (additive; Sections 1–2 untouched, so Safety Net still runs).

- **Pipeline:** `extract.extract_chart` (Haiku, widened 9-type `SignalType`) →
  `timeline.build_threads` (deterministic entity threading, NEW) →
  `reconcile.reconcile_thread` (Opus, doc-03 prompt, 4 statuses) →
  `grounding.apply_surfacing` (citation validation + `TOP_N=4`/`ABSTAIN=0.6`) →
  `chart_review.run_review` → `ChartReviewResult`.
- **Prompts (verbatim invariant applies):** `prompts/whole_chart_reasoning_system.txt`
  (doc-03 system prompt + two few-shot anchors), `whole_chart_extraction_system.txt`.
- **Self-verify:** `python -m safety_net.eval_harness` → live-set gate (H4
  UNCONFIRMED/High, H1 surfaces, H_SUPPRESS suppressed & cited to the PCP letter,
  **precision == 1.0**, all citations validate). Offline tests: `tests/test_whole_chart.py`.
- **Live test + determinism model:** `docs/whole-chart-live-test.md`. Two paths —
  the deterministic demo/gate (committed cache + `chart_review --live-heroes`) vs.
  the non-deterministic full-live stress test (`chart_review --write-cache`).
  Extraction naming drifts run-to-run (absorbed by `canonicalize_entity`,
  `dedupe_by_evidence`, discharge-doc skip, and harness `match_excerpt`); the
  sweep is precomputed on purpose. Lock the demo on the deterministic path.
- **Data / offline cache:** `data/chart/{chart.json,manifest.json,cache/}`.
  Regenerate the chart with `scripts/generate_chart.py`; author the offline cache
  (no-key envs) with `scripts/author_cache.py`, or capture a live cache with
  `chart_review --write-cache`. UI: `python ui/render_chart.py` → `ui/whole_chart.html`.
- **Two live heroes:** H4 (held apixaban never restarted → escalate), H_SUPPRESS
  (post-diverticulitis colonoscopy closed as "lower endoscopy" in the PCP letter →
  suppress). Their pinned strings in `docs/whole-chart-synthetic-data-spec.md` are
  verbatim — editing them breaks citation validation and the equivalence demo.
- **Two noted schema-name deviations** (values/shape match the contract): contract
  `SweepResult` → `ChartReviewResult` (avoids Section 2 collision); `Status` →
  `ThreadStatus`.
