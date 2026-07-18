# Safety Net

**A retrospective diagnostic-safety agent.** It sweeps a backlog of finished
radiology reports, extracts every follow-up recommendation, and reasons about
whether each was *actually addressed* by a later study — not merely whether a
later study happened. Findings that fell through are surfaced, each with a
specific, human-answerable question; a capable scan that never mentions the
original finding is **UNCONFIRMED** and is escalated, never silently closed.

> "The report was right. The system around it failed. We built the system."

> **Working on this?** Start with [`CLAUDE.md`](CLAUDE.md) and
> [`docs/build-status.md`](docs/build-status.md) (current status, decisions, next
> steps). The live demo is scripted in [`docs/demo-runbook.md`](docs/demo-runbook.md).

## Architecture (two sentences)

A deterministic, code-orchestrated backlog sweep loads reports and runs a
three-stage pipeline — **Haiku** bulk-extracts recommendations and studies,
plain code matches candidate later studies per open recommendation, and
**Opus** reconciles each recommendation against its candidates across five
explicit axes, emitting a strict-JSON verdict with a verbatim citation behind
every determination. The reasoning core (reconciliation + action-drafting) is
genuinely agentic Opus; everything is exposed as a thin FastMCP server, while
the live demo path calls the core Python directly for reliability.

The five reconciliation axes: **modality adequacy**, **anatomic coverage**,
**finding acknowledgment** (the crux — silence ≠ satisfaction), **temporal
adequacy**, and **terminal events**. Acknowledgment gates the verdict: correct
modality + anatomy + timing but no acknowledgment of the finding → escalate.

## Layout

```
docs/                     Authoritative design docs (source of truth)
src/safety_net/
  models.py               Frozen finding/reconciliation JSON contract (Pydantic)
  client.py               Anthropic client + Opus/Haiku helpers
  prompts/                System prompts (reconciliation copied verbatim from docs)
  extract.py              Haiku bulk extraction: report -> recommendations + study
  reconcile.py            Opus reconciliation: five-axis reasoning -> verdict
  actions.py              Opus action-drafting for escalate cases
  sweep.py                Deterministic code-orchestrated backlog sweep
  mcp_server.py           Thin FastMCP wrapper (off the live demo path)
data/heroes/              Two hero cases: A (looks closed, isn't) / B (looks open, is closed)
data/filler/              Templated filler reports for the sweep count
data/cache/               Real captured hero responses (offline demo fallback)
scripts/preflight.py      SDK / key / model-resolution / live-ping check
scripts/smoke_case_a.py   End-to-end Case A reconciliation smoke test
ui/render.py              Minimal UI stub: renders the two hero cases to HTML
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .            # or: pip install -r requirements.txt
cp .env.example .env        # then put a real ANTHROPIC_API_KEY in .env
```

The key needs access to **both** `claude-opus-4-8` and
`claude-haiku-4-5-20251001`.

## Run

```bash
# 1. Verify the environment (SDK version, key, model resolution, live pings)
python scripts/preflight.py

# 2. Smoke test: reconcile Case A end to end (expects escalate + question)
python scripts/smoke_case_a.py

# 3. Full sweep over the backlog; reconcile the two heroes live, write cache
python -m safety_net.sweep --write-cache

# 4. Render the minimal two-case UI (writes ui/index.html; open it)
python ui/render.py

# (optional) Run the thin MCP server — a credibility exhibit, off the demo path
python -m safety_net.mcp_server
```

Without a network/key, the sweep and UI fall back to `data/cache/` so the demo
runs offline.

## Whole-Chart Review (pivot)

A net-new workflow that **extends the same engine** to a critical moment:
instead of one follow-up recommendation, the agent reviews an entire **14-day
inpatient admission at discharge** and connects dots no single clinician or
specialty would — an orphaned incidental, a result pending at discharge, a
trend visible only across days, a dropped consult rec, a med-reconciliation gap.
It surfaces only the threads that genuinely fell through (hard-capped, ranked by
consequence-of-the-miss), each with a verbatim citation and a specific,
human-answerable question — and it **suppresses** look-alikes that were actually
closed in different words (equivalence reasoning, not keyword matching).

Reuses the reconciliation engine, verbatim-citation validation, action drafting,
the MCP wrapper, and the UI shell. The only new code is entity threading, the
eval harness, and the widened schemas. Design docs:
[`docs/whole-chart-schema-contract.md`](docs/whole-chart-schema-contract.md)
(frozen contract), `-iteration`, `-synthetic-data-spec`, `-reasoning-prompt`,
`-build-plan`.

```
# Run the whole-chart review (offline, from the committed cache)
python -m safety_net.chart_review --use-cache

# Self-verify against the ground-truth manifest (the eval harness gate)
python -m safety_net.eval_harness          # precision 1.0, suppress correct, citations valid

# Render the reasoning-first UI (writes ui/whole_chart.html; open it)
python ui/render_chart.py

# With a key: capture a fresh live cache, or run the two heroes live on stage
python -m safety_net.chart_review --write-cache
python -m safety_net.chart_review --live-heroes   # H4 + H_SUPPRESS live, rest precomputed
```

Pipeline: **Haiku** widened signal extraction → deterministic **entity
threading** (`timeline.py`) → **Opus** per-thread reconciliation (four statuses,
the suppress/equivalence wedge) → citation validation + `TOP_N`/abstain
surfacing (`grounding.py`) → `ChartReviewResult`. The two live heroes are
**H4** (home anticoagulant held for a procedure, never restarted → escalate) and
**H_SUPPRESS** (post-diverticulitis colonoscopy, closed as "lower endoscopy" in
the PCP letter → suppressed). Whole-chart layout additions:

```
src/safety_net/
  timeline.py             NEW — deterministic entity threading (no LLM)
  chart_review.py         NEW — whole-chart orchestrator (+ offline cache)
  eval_harness.py         NEW — citation validator + ground-truth scorer (the gate)
  grounding.py            NEW — citation validation + rank/surface (TOP_N, abstain)
data/chart/               14-day synthetic chart, manifest, cache (offline fallback)
scripts/generate_chart.py Author the synthetic chart (self-validating)
ui/render_chart.py        Reasoning-first whole-chart UI
```

## Notes

- **Synthetic data only.** The hero cases are hand-authored; no PHI.
- **Not a diagnostician.** The engine reasons about *documentation* — whether a
  later study addressed a prior finding — with a verbatim citation behind every
  claim. It does not make or second-guess clinical decisions.
- **Not a dashboard.** Any aggregate view is a two-second bookend, never a feature.
