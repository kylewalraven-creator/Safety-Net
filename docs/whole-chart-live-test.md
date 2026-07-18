# Safety Net Whole-Chart — Live Test & Determinism Runbook

How to run the whole-chart review against the real models, how to read the eval
harness, and — most important — **which path is deterministic (use it for the
demo and the gate) versus which is a variable stress test.** Pair with
`docs/demo-runbook.md` (the Safety Net demo) and `CLAUDE.md` (invariants).

---

## TL;DR — two paths, pick deliberately

| | Path A — demo & gate | Path B — full-live stress test |
|---|---|---|
| Command | `eval_harness` + `chart_review --live-heroes` | `chart_review --write-cache` then `eval_harness` |
| Determinism | **Deterministic — passes every time** | **Non-deterministic** run to run |
| Live LLM calls | reconcile the 2 heroes only (few-shot-anchored) | Haiku extracts all notes + Opus reconciles every thread |
| Use it for | the on-stage demo, CI/pre-demo gate | a credibility spot-check only |
| Never | — | don't demo from it or treat a red run as "the build broke" |

**Lock the demo on Path A.** Path B is a good "yes, it works end-to-end live"
check, but treat a green result as *confirmed*, not *required*.

---

## Why two paths (the determinism model)

The pipeline has one stochastic stage that matters here:

- **Extraction (Haiku, bulk, free-form)** decides how to name each `entity`.
  Across runs it drifts — a size suffix (`pulmonary_nodule_lll_9mm`), an
  indication suffix (`colonoscopy_followup_diverticulitis`), or splitting one
  thread into two (`pulmonary_nodule_lll` **and** `chest_ct_followup`). This is
  inherent to running a bulk LLM over 20+ notes; it is not a bug.
- **Reconciliation of the two heroes (Opus)** is few-shot-anchored on H4 and
  H_SUPPRESS, so it is stable.

That is exactly why the design **precomputes the sweep and reconciles only the
two heroes live**, and why the harness scores the **committed cache** (canonical
entities) rather than a fresh live extraction. Chasing byte-perfect
full-sweep-live determinism is a losing game — the deterministic artifact is the
cache.

The system still absorbs the common drift so Path B usually passes anyway (see
"Known drift modes" below), but "usually" is the point: Path A is "always."

---

## One-time setup

```bash
cd Safety-Net
git checkout claude/safety-net-repo-setup-f3yb0f   # or the pivot branch — same tip
git pull
python -m venv .venv && source .venv/bin/activate
pip install -e .
cat .env                                            # ANTHROPIC_API_KEY=sk-ant-...
python scripts/preflight.py                         # live-pings Opus + Haiku
```
`preflight` confirms the key reaches **both** `claude-opus-4-8` and
`claude-haiku-4-5-20251001`. If it fails, stop here — nothing live will work.

---

## Path A — the demo & gate (deterministic)

```bash
# 1. Score the committed cache against the ground-truth manifest.
python -m safety_net.eval_harness
#    -> precision 1.000, GATE: PASS ✅   (exit 0). This is your CI/pre-demo gate.

# 2. Render the reasoning-first UI from the (deterministic) cache.
python ui/render_chart.py && open ui/whole_chart.html

# 3. The on-stage behavior: reconcile the two heroes LIVE, rest precomputed.
python -m safety_net.chart_review --live-heroes
```
**What step 3 does:** H4 (held apixaban) and H_SUPPRESS (colonoscopy → "lower
endoscopy") are reconciled against the API using the *canonical cached signals*,
so entity keys never drift; H1/H2/H3 load from the cache. You get live reasoning
where the demo dwells, determinism everywhere else. Needs a key.

---

## Path B — the full-live stress test

```bash
# 0. Restore the committed (authored) cache first — write-cache will overwrite it.
git checkout -- data/chart/cache

# 1. LIVE: Haiku extracts every note, Opus reconciles every thread, cache written.
python -m safety_net.chart_review --write-cache

# 2. Score the LIVE output.
python -m safety_net.eval_harness
```
**What this does:** replaces the cache with raw live model output (~20 Haiku +
~6–12 Opus calls, a minute or two), then grades it. **Expect** `precision 1.000`
and `GATE: PASS ✅` most runs — but a fresh drift mode can drop it. That is
normal for Path B; it is not a regression.

**After Path B, restore the deterministic cache before demoing:**
```bash
git checkout -- data/chart/cache          # discard the live overwrite (recommended)
# …or, if you want the live output as the demo source, review it first, then:
# git add data/chart/cache && git commit -m "data: capture live whole-chart cache"
```

---

## Reading the eval output

- `precision` **must be 1.000** — zero false positives. A false alarm in front of
  a clinician is the fatal failure mode.
- `per-item`: `H1_nodule`, `H4_apixaban`, `H2_bcx`, `H3_aki` → `TP`;
  `H_SUPPRESS_colo` → `TN`. An `UNPLANTED:t_…` row with outcome `FP` is a real
  thread that surfaced when it should have cleared — investigate it.
- `citations: N/N valid` — every presence excerpt is an exact substring of its
  cited note. Any failure is a hard fail.
- The `live-set gate` block must show all `[PASS]`; exit code is 0 on pass, 1 on
  fail (so it doubles as a CI gate).
- Full detail per run is written to `data/chart/run_log.json` (the reliability
  exhibit): models, token estimate, per-stage latency, citation counts, and the
  full `EvalSummary`.

---

## Known live-extraction drift modes (and how the system absorbs them)

| Drift mode | Example | Handled by |
|---|---|---|
| Size / measurement suffix | `pulmonary_nodule_lll_9mm` | `extract.canonicalize_entity` strips it |
| Medication-status suffix | `apixaban_restart` | `extract.canonicalize_entity` strips it |
| Indication / synonym suffix | `colonoscopy_followup_diverticulitis` | harness matches by pinned `match_excerpt`, not the key |
| Thread split into two entities | `pulmonary_nodule_lll` **+** `chest_ct_followup` | `grounding.dedupe_by_evidence` collapses same-evidence findings |
| Discharge-doc "closure" noise | `lower_endoscopy_followup`, `pcp_office_visit` | `extract.extract_chart` skips discharge summary/addendum/PCP letter |
| Low-confidence speculation | a marginal thread at conf 0.5 | `ABSTAIN_THRESHOLD` (0.6) → cleared, not surfaced |
| Over-surfacing | too many escalations | `TOP_N` (4) cap by risk × confidence |

Each is covered by a test in `tests/test_whole_chart.py`, so the mechanisms
can't silently regress.

---

## If a NEW false positive / false negative appears on Path B

1. **Look at it.** Open `data/chart/run_log.json` and the `per-item` block; find
   the offending thread and its citations. Is it a genuinely new dot, a naming
   variant, or a duplicate?
2. **Pick the smallest lever:**
   - Naming variant not matching a planted dot → add/adjust the dot's
     `match_excerpt` in `scripts/generate_chart.py`, regenerate the manifest.
   - Same-evidence duplicate not collapsing → the excerpts differ; widen
     `grounding._same_evidence` or tighten the extraction prompt.
   - A speculative low-value surface → raise `ABSTAIN_THRESHOLD` in `models.py`
     (prefer abstaining over shipping a false alarm — the stated guardrail).
3. **Do not chase full-live determinism indefinitely.** If Path B keeps finding
   new variants, that is the expected behavior of a bulk LLM extractor — lock the
   demo on **Path A** and use Path B as a spot-check.

---

## The one rule

**Precision over recall, always.** A quiet miss on a non-hero dot is survivable;
a false alarm in front of the clinician is not. If precision is ever fighting
you, raise the abstain threshold rather than ship a speculative surface.
