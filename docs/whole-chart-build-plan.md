# Safety Net Whole-Chart — Build Plan (for the Claude Code session)

Execution plan for extending the existing Safety Net build into whole-chart review. Written for an autonomous coding agent: concrete targets, per-step acceptance criteria, and a self-verifying eval gate. **Inventory the existing repo first and reuse — do not rebuild what exists.**

---

## Reuse map (extend, don't recreate)

| Capability | Status | Action |
|---|---|---|
| Haiku bulk extraction | exists (Safety Net) | Widen the extraction schema from "recommendation" to the 9-type `SignalType` taxonomy + `entity` canonicalization. |
| Opus reconciliation | exists | Swap in the whole-chart system prompt (doc 03); reason per `Thread` instead of per single recommendation. |
| Verbatim-citation validation | exists | Reuse as-is; wire into the harness gate. |
| Action drafting | exists | Reuse; produce `suggested_action` for surfaced High/Medium findings. |
| FastMCP wrapper | exists | Reuse; keep OFF the live demo path (credibility exhibit only). |
| UI shell | exists | Reuse; adapt to the reasoning-first whole-chart view. |
| Timeline / entity threading | **new** | Build (Step 3). Deterministic code, no LLM. |
| Eval harness | **new** | Build (Step 7). |
| 14-day synthetic chart | **new** | Generate from doc 02. |

The genuinely new code is threading + the harness + widened schemas. Everything else is adaptation.

---

## Sequenced steps

Freeze the schema (doc 01) before anything else so steps run in parallel against the contract.

**Step 0 — Branch.** Create a branch off the working Safety Net build. Keep `main`/Safety Net runnable as the fallback demo. *Done when:* Safety Net still runs from its entry point on the branch.

**Step 1 — Generate the synthetic chart.** Produce the `ChartBundle` per doc 02. The live heroes (H4, H_SUPPRESS) and the bridge (H1) use the pinned verbatim strings exactly; secondaries (H2, H3) and filler to guidance. Emit as data files (JSON per the `Note` schema) plus a human-readable dump. *Done when:* all pinned strings from doc 02 are present verbatim; filler is clean (no unplanned unreconciled threads); a domain read passes plausibility.

**Step 2 — Ingestion + widened extraction (Haiku).** Load notes → run extraction → emit `ExtractedSignal[]`. Enforce that every `verbatim_excerpt` is a substring of its source body (reject + retry on failure). Enforce consistent `entity` keys. *Done when:* extraction recovers all planted-dot signals with the canonical entities from the manifest, and all excerpts validate.

**Step 3 — Timeline / threading (new, deterministic).** Group signals by `entity`, sort by (day, timestamp), emit `Thread[]`. No LLM. *Done when:* each manifest entity resolves to exactly one thread with events in temporal order.

**Step 4 — Reconciliation (Opus).** For each thread, call Opus with doc 03's prompt + the thread events + discharge summary + addendum + PCP letter. Parse strict JSON to `Finding`. *Done when:* every thread yields a schema-valid `Finding`; H4 → UNCONFIRMED and H_SUPPRESS → CONFIRMED_ADDRESSED (H1 → UNCONFIRMED).

**Step 5 — Grounding, ranking, surfacing.** Run citation validation on every finding (reject any with a non-matching `presence` excerpt). Rank by `risk_weight * confidence`. Apply `ABSTAIN_THRESHOLD` (0.6) and `TOP_N` (4); populate `findings` vs `cleared`. *Done when:* H_SUPPRESS lands in `cleared` with a reason; surfaced set contains no false positives.

**Step 6 — Action drafting + MCP wrapper.** Draft `suggested_action` for surfaced High/Medium findings. Expose sweep/reconcile as FastMCP tools, off the live path. *Done when:* H4 has the live-approved clarify/restart-apixaban action and H1 a sensible addendum citing the CT note; MCP tools callable but not on the demo path.

**Step 7 — Eval harness (new — the self-verification gate).** See spec below. *Done when:* the harness runs green on the live-set gate.

**Step 8 — UI / output.** Reasoning-first: `summary_line` as a 2-second bookend, then a click-through to one finding's `connection` + `timeline` (with excerpts) + `question`, and a human-approve control on H4's action. Reuse the Safety Net shell. **Not a dashboard.** *Done when:* the H4 timeline-and-question view renders and its action (clarify/restart apixaban) can be approved live.

**Step 9 — Precompute + rehearse.** Reconcile H4 and H_SUPPRESS live; precompute H1/H2/H3 for determinism. Produce the sweep artifact the UI reads on stage. *Done when:* a cold run reproduces the same on-stage output.

---

## Eval harness spec (Step 7)

Two checks; both must pass on the live set.

**A. Verbatim-citation validator.** For every `Finding` in `findings` and `cleared`: each `timeline` event with `evidence_kind == "presence"` must have `excerpt` be an exact substring of the referenced note's `body`. Any failure → hard fail (and the finding should have been rejected upstream).

**B. Ground-truth scorer.** Load the manifest from doc 02. For each planted item, compare surfaced/status against expectation → TP/FP/FN/TN. Compute precision/recall. Emit `EvalSummary`.

**Live-set success gate (build is not done until all true):**
1. `H4_apixaban` (primary live escalate) surfaced, status UNCONFIRMED, risk High, all citations valid; `H1_nodule` also surfaces (UNCONFIRMED/High) in the full sweep.
2. `H_SUPPRESS_colo` NOT surfaced (in `cleared`), status CONFIRMED_ADDRESSED, cited to the PCP letter.
3. **precision == 1.0** on the surfaced set (zero false positives) — non-negotiable.
4. All `presence` citations across the run validate.

Log everything to the run log per doc 01 (`RunMeta` + per-finding + suppression traces + abstentions).

---

## Guardrails (build constraints — the agent must not drift from these)

- **No dashboard.** The aggregate/summary is a one-line 2-second bookend. The hero is the reasoning on one thread. The `TOP_N` cap is mandatory, not optional.
- **Precision over recall.** A false positive on the live set fails the build. Prefer abstain (low confidence → `cleared`) over a speculative surface.
- **Grounding is mandatory.** No finding survives without a validated verbatim citation. The model reconciles documents; it never diagnoses.
- **Determinism on stage.** Two heroes live, the rest precomputed. MCP off the live path.
- **Don't break Safety Net.** Branch; keep the fallback runnable.
- **DQ line.** Only reuse code built during the event (all listed reuse qualifies). Demo shows only what was built during the event.

---

## Critical path + parallelization

Step 1 (data) is the long pole and gates Steps 2–6. Freeze the schema (doc 01) in the first minutes so Steps 2, 3, 8, and the harness scaffold build in parallel against the contract. New code is small (Step 3 + harness + widened schemas); the real effort is data authoring and reconciliation-prompt precision.

## Graceful degradation (if behind)

Cut secondaries first: ship **H4 + H_SUPPRESS live, plus H1 precomputed as the Safety Net bridge; drop H2/H3**. A tight two-hero demo that passes the live gate beats a rich chart you didn't finish grounding. If reconciliation precision is fighting you, raise `ABSTAIN_THRESHOLD` before shipping anything that produces a false positive. Safety Net remains the ultimate fallback.

## Definition of done

Live gate green; H4 timeline-and-question view renders with an approvable action (clarify/restart apixaban); H_SUPPRESS correctly suppressed; MCP exhibit callable off-path; Safety Net still runs on `main`; run log populated. Then hand back for rehearsal + the 60-second video cut.
