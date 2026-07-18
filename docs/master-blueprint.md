# Safety Net — Master Build Blueprint (Hackathon Day)

The integrating doc. Detail on the reasoning logic lives in `safety-net-reconciliation-prompt.md`, the demo shape and wedge in `safety-net-reconciliation-spec.md`, and the schedule in `safety-net-run-of-day.md`. This is the *what to build, with what, in what order, and what not to forget*.

## 1. What we're building
A retrospective diagnostic-safety agent: it sweeps a backlog of finished radiology reports, extracts every follow-up recommendation, reasons about whether each was **actually addressed** by a later study (not just whether a study happened), and surfaces the ones that fell through — with a specific, human-answerable question for each ambiguous case. The deliverable is a **~3-minute live demo** of two contrasting patients (one that looks closed but isn't → escalate; one that looks open but is closed → suppress) plus one human-approved closing action.

## 2. Architecture

```
raw reports (JSON)
  → [Extract · Haiku]        → recommendations[] + studies[]
  → [Candidate match · code] → per open rec: plausible later studies (same patient, anatomic overlap, date > rec date)
  → [Reconcile · Opus]       → verdict + per-axis evidence + closure_state + escalation   ◀── the reasoning core
  → [State machine · code]   → per-rec status; overdue computed vs as_of_date
  → [Draft action · Opus/Haiku] → outreach/order draft (for escalate/open) → [Human approve · UI] → audit log
                                    ▲
              all wrapped as an [MCP server] (tools); thin [Web UI] renders trace + evidence highlight + approve
```

**Key architectural decision — hybrid, not fully autonomous.** The backlog *sweep* is orchestrated by plain code (reliable, and it's what produces the "swept 50 reports" number). The *reconciliation* and *action-drafting* steps are genuinely agentic Opus calls with visible multi-step reasoning and tool use. Everything is exposed as an MCP server so it's tool-native (your "runs Monday, no integration" story).

- Why hybrid: a fully autonomous orchestrator looks more agentic but is nondeterministic and will bite you live. A pure hardcoded pipeline is reliable but reads as "a data script with LLM calls." Hybrid gets reliability *and* a genuine agentic core.
- MCP scoping: build clean Python functions first, then wrap them as thin MCP tools (fast with FastMCP). Don't build MCP-first. The stage demo should go **UI → backend → tools/functions**, not depend on an external MCP client over venue wifi. (Connecting Claude Desktop to your MCP server is a great flourish *for the video*, not the primary stage path.)

## 3. Tech stack + the forks to settle in the first 20 minutes
| Layer | Recommendation | Why / tradeoff |
|---|---|---|
| Backend / agent | Python 3.11+, `anthropic` SDK | Fastest path; MCP + Anthropic both first-class in Python |
| Models | Opus `claude-opus-4-8` (reconcile, draft); Haiku `claude-haiku-4-5-20251001` (bulk extract) | Opus for ambiguity, Haiku for cheap volume |
| MCP | `mcp` / FastMCP, thin wrapper over functions | On-theme + judging value; keep it a wrapper, not the architecture |
| Orchestration | Hybrid (code sweep + agentic reconcile/action) | Reliability + genuine agency (see §2) |
| Live vs pre-run | Reconcile the **2 hero cases live**; pre-compute the rest of the sweep | Avoids stage latency/cost/rate-limits; heroes are the demo anyway |
| Trace rendering | Click-to-run with a visible "reasoning…" state (stream only if trivial) | Token-streaming is fragile; a 5–15s Opus call reads as "thinking" |
| UI | Plain HTML/JS single page **or** Vite+React+Tailwind | Plain if no strong frontend hand (zero build); React if you have a React person. UI is one page, two cases — keep it tiny |
| Storage | JSON files loaded in-memory (SQLite only if you want it) | Demo-scale; persistence is a non-goal |
| Filler data | Script- or Haiku-generated templated reports; **skip Synthea** | Synthea is Java + setup-heavy; it'll eat the clock for filler you don't need |
| Serving | FastAPI + uvicorn (only if the UI needs a backend endpoint) | Or run the pipeline to JSON the page reads — simpler |

## 4. Data model (freeze these early — they're the contracts)
- **report** `{report_id, patient_id, date, modality, specialty, full_text}`
- **recommendation** `{rec_id, patient_id, source_report_id, report_date, finding, anatomic_site, recommended_modality, recommended_timeframe, urgency_tier, original_text, status}`
- **study** `{study_id, patient_id, report_id, date, modality, anatomic_coverage, impression_text, full_text}`
- **reconciliation_result** — the JSON emitted by the Opus prompt (see prompt doc)
- **action_draft** `{action_id, rec_id, type: patient_letter|provider_message|order, draft_text, status: draft|approved, approver, ts}`
- **audit_event** (append-only) `{ts, actor, action, rec_id, detail}`
- **closure_state** enum: `open_overdue | scheduled | completed | superseded | declined | overrode | escalate`

The reconciliation JSON schema is already fixed in the prompt — that contract is what lets the UI and the agent be built **in parallel** (mock the JSON, build the UI against it, swap in the real agent later).

## 5. Components to build (with dependencies + "done when")
Priority: **MUST** (demo dies without it) · **SHOULD** (first to cut under pressure) · effort is rough.

- **C1 · Synthetic data** — MUST. Two hero patients (A → UNCONFIRMED/escalate; B → SUPERSEDES/superseded) with full report chains, plus ~30–50 filler reports for the sweep number. *Depends: nothing — start at 10:30.* *Done when: the two heroes produce the intended verdicts and the backlog has enough volume.*
- **C2 · Extraction (Haiku)** — MUST. Report → recommendation + study objects. *Depends: C1, schemas.* *Done when: returns schema-valid objects across the backlog.*
- **C3 · Candidate match (code)** — MUST (trivial). Per open rec, later studies with anatomic overlap and date > rec date. *Depends: C2 shape.* *Done when: correct candidates for both heroes.*
- **C4 · Reconciliation (Opus)** — MUST (the core). Use the prompt doc verbatim. *Depends: C1, C3, prompt (done).* *Done when: A → UNCONFIRMED/escalate+question; B → SUPERSEDES/superseded; JSON parses reliably.*
- **C5 · State machine (code)** — MUST (light). Apply closure_state; compute overdue vs as_of_date; track statuses. *Depends: C4.* *Done when: statuses + overdue/escalate flags render correctly.*
- **C6 · Action draft + approve** — SHOULD. Draft outreach/order for escalate/open; one-click human approve; audit entry. *Depends: C4/C5.* *Done when: Case A yields a draft, approve logs an audit event.*
- **C7 · MCP server** — SHOULD. Wrap C2–C6 as tools (`list_reports, extract, match, reconcile, draft_action, approve`). *Depends: clean C2–C6 functions.* *Done when: tools callable and return expected results; degrade to direct calls if flaky.*
- **C8 · Web UI / demo surface** — MUST. Report viewer + reasoning trace (axes → verdict → confidence) + **evidence highlight in source text** + 2-second aggregate bookend + approve button. *Depends: C4 JSON contract only — build against mocks immediately.* *Done when: the scripted click-path runs both cases and renders trace + highlight cleanly.*
- **C9 · Orchestration/glue + cached fallback** — MUST. One command/endpoint that runs extract over the backlog and reconcile over open recs (bulk pre-run; heroes live); a cached copy of the two hero responses. *Depends: C2–C5.* *Done when: pipeline runs end-to-end and a cached-fallback toggle exists.*

## 6. Critical path & parallelization (contract-first)
Chain: **C1 → C2 → C3 → C4 → C5 → C6**. C8 (UI) depends only on C4's *schema*, so it forks off immediately against mocked JSON. Two independent workstreams, split however you two decide:
- **Agent/backend stream:** C2, C3, C4, C5, C6, C7, C9.
- **Data + UI + narrative stream:** C1 (first — it's the critical-path unblock), C8, demo script, Q&A.
The fixed reconciliation JSON is the seam that lets both run without blocking. Sync at: architecture lock (start), first integration (midday), dry-run (afternoon).

## 7. Environment & accounts — have these working *before* 10:30
- Anthropic API key with **Opus + Haiku** access; run a test call and confirm it returns before the clock starts. (Confirm the hackathon's credit/key setup at kickoff.)
- Python venv ready; `pip install anthropic mcp pydantic python-dotenv` (+ `fastapi uvicorn` if serving, + `fastmcp` if using it).
- Node 18+/npm **only if** React (`vite`, `react`, `tailwindcss`). Otherwise plain HTML/JS, no build.
- GitHub repo created **at 10:30, set PUBLIC**, both teammates added as collaborators.
- Screen-record tool (Loom/QuickTime/OBS) + a host for the 1-min video (unlisted YouTube / Loom / Drive).
- **Phone hotspot** as wifi backup; chargers; a second device that can open the repo + video.

## 8. Things to account for that you didn't state
- **The demo runs live on stage — build the cached-response fallback NOW.** Wifi loss, API rate-limit, and a bad API response are the top three demo-killers. Also capture a known-good screen recording of a full run as an ultimate fallback (separate from the 1-min submission video).
- **Only reconcile the two heroes live; pre-compute the rest of the sweep.** Looping Opus over 50 reports on stage risks latency, cost, and rate limits. The aggregate bookend number is pre-run.
- **Evidence highlighting breaks on whitespace/smart-quote mismatches.** The verbatim `quote` must string-match the source to highlight it — normalize whitespace and add a fuzzy fallback, or the money-shot silently fails.
- **The model may wrap output in fences or add prose despite instructions.** Strip defensively, retry once on parse failure, and cache the two hero responses so the demo never depends on a fresh parse.
- **Latency reads as "the agent thinking."** A 5–15s Opus call with a visible reasoning state is fine — even good. Don't apologize for it; don't try to hide it with fake instant results.
- **Keep tool use visible so "agentic" is legible.** Don't let the pipeline collapse into one LLM call. The multi-step reasoning + MCP tool calls are the evidence judges score on Technical Complexity.
- **DQ hygiene:** fresh repo, all code written on-day, **commit frequently** (clean on-day history is your proof), README states what was built today, synthetic data only (no PHI). Don't import a pre-existing project.
- **Submission is due AT 5:00, and GitHub repos default to private.** Flip to public and submit by ~4:50. Test the video link **logged out / incognito**. Add both teammates on the submission form.
- **Judging rooms may not have reliable wifi** (R1 in a room, R2 on stage) — the cached/offline path must run without network.
- **Absorb the kickoff resources reveal (10:00).** Abridge/partner may hand out data, an MCP server, or credits that change these choices — leave 15 min to adjust.

## 9. Demo & submission execution
- **Scripted click-path, ≤5 clicks, rehearsed — never improvised.** Sweep → open Case A → run reconciliation (escalate + question) → open Case B (superseded, no action) → back to A, approve the draft → close line.
- **1-min video** (after freeze): Case A hero beat + close line ("The report was right. The system around it failed. We built the system."). Tight, no dead air.
- **Submission checklist:** repo public ✓ · README ✓ · video link works logged-out ✓ · both teammates added ✓ · **submitted before 5:00** ✓.
- **Q&A** grounded in the system (see prompt/spec docs): order-matching vs acknowledgment; escalation = the false-negative answer; document-equivalence reasoning with citations ≠ diagnosis.

## 10. Non-goals — do NOT build these
Auth · user management · persistence across sessions · a real database (JSON is fine) · multi-specialty extractors (radiology only; *assert* cross-specialty) · FHIR/EHR integration · scheduling integration · forward-looking real-time monitoring (retrospective sweep only) · a general analytics dashboard (the aggregate view is a 2-second bookend, never the centerpiece — it's an explicit anti-project).
