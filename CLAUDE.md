# CLAUDE.md — Safety Net

Safety Net is a **retrospective diagnostic-safety agent**: it sweeps finished
radiology reports, extracts follow-up recommendations, and reasons about whether
each was **actually addressed** by a later study (acknowledgment) — not merely
whether a later study happened. A capable scan that never mentions the finding
is **UNCONFIRMED → escalate with a specific, human-answerable question**, never
silently closed. One-day hackathon project (Abridge × Anthropic × Lightspeed).

> **New session: read `docs/build-status.md` (full handoff — status, decisions,
> next steps) and `docs/demo-runbook.md` (how the demo actually runs) first.**
> The four authoritative design docs live in `docs/`: `master-blueprint.md`,
> `reconciliation-spec.md`, `run-of-day.md`, `reconciliation-prompt.md`.

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
  cache), `mcp_server.py` (thin FastMCP, 7 tools).
- `data/heroes/`: Case A (→ escalate), Case B (→ superseded). `data/filler/`:
  sweep volume (6 normal reports). `data/cache/`: committed real hero responses.
- `scripts/preflight.py`, `scripts/smoke_case_a.py`; `tests/test_offline.py`
  (runs with no key); `ui/render.py` (static two-case UI stub).
- `data/synthetic-ambient-fhir-25/`: teammate Deep's synthetic FHIR dataset —
  **not** consumed by the sweep (which loads only `data/heroes` + `data/filler`).

## Status (2026-07-18)
Full first slice built and verified end-to-end: preflight 11/11 live, Case A →
escalate + question, Case B → superseded, offline tests 8/8, UI renders with
highlighted citations. Working branch: `claude/safety-net-repo-setup-f3yb0f`.
See `docs/build-status.md` for decisions, rationale, what's stubbed, and next steps.
