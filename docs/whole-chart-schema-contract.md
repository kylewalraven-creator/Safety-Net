# Safety Net Whole-Chart — Schema Contract (FROZEN)

The single source of truth every component codes against. Freeze this first; all other work parallelizes against it. Notation is readable-typed pseudo-schema — turn it into dataclasses / Pydantic / TypedDict as the repo prefers. Field constraints are inline.

---

## Input: `ChartBundle`

```
ChartBundle {
  chart_id: str
  patient: { age: int, sex: str, admit_day: int=1, discharge_day: int=14 }
  notes: Note[]                       # the full 14-day record, any order
}

Note {
  note_id: str                        # stable, unique; used in every citation
  day: int                            # 1..14
  timestamp: str                      # ISO; ordering is load-bearing
  author_role: str                    # e.g. "hospitalist", "GI consult", "radiologist"
  note_type: NoteType
  body: str                           # raw text; citations must be exact substrings of this
}

NoteType = one of:
  progress_note | consult_note | radiology_report | lab_result | micro_result |
  med_reconciliation | med_admin | procedure_note | nursing_note |
  discharge_summary | discharge_addendum | pcp_letter
```

---

## Stage 1 output: `ExtractedSignal` (Haiku, bulk)

Widened from Safety Net's "recommendation" extraction to the full signal taxonomy.

```
ExtractedSignal {
  signal_id: str
  source_note_id: str
  day: int
  signal_type: SignalType
  entity: str                         # CANONICAL key for threading — see rule below
  summary: str                        # one-line paraphrase (not cited)
  verbatim_excerpt: str               # MUST be an exact substring of source note body
}

SignalType = one of (maps to taxonomy A–I in the iteration doc):
  incidental_finding | pending_result | trend | med_recon_gap |
  consult_recommendation | dropped_thread | cross_domain_interaction |
  continuity_gap | documentation_contradiction
```

**Entity canonicalization rule (critical for threading):** `entity` is a normalized handle that links events across notes/days about the *same thing*. Same nodule across two reports → same entity. Same drug → same entity. A lab series → one entity. Use lowercase snake_case, anatomically/pharmacologically specific:
`pulmonary_nodule_lll`, `apixaban`, `creatinine_series`, `abscess_culture`, `colonoscopy_followup`, `blood_culture_d11`. The threading step groups purely on this key, so extraction MUST be consistent. When unsure, prefer the more specific handle.

---

## Stage 2 output: `Thread` (deterministic code — no LLM)

```
Thread {
  thread_id: str
  entity: str
  signal_type: SignalType             # dominant type across the thread's signals
  event_signal_ids: str[]             # ExtractedSignal ids, sorted ascending by (day, timestamp)
  first_day: int
  last_day: int
}
```

Built by: group signals by `entity`, sort by time, emit one Thread per entity. Threads with a single event are still valid (e.g., a lone incidental).

---

## Stage 3 output: `Finding` (Opus, the reasoning — the hero)

```
Finding {
  finding_id: str
  thread_id: str
  title: str                          # one line naming the dot
  risk: "High" | "Medium" | "Low"     # consequence-of-the-miss, not finding severity
  status: Status
  connection: str                     # the reasoning: which >=2 events connect + why single-pass misses it
  timeline: TimelineEvent[]           # ordered evidence
  question: str                       # specific, human-answerable escalation; never "review the chart"
  suggested_action: Action | null     # populated for surfaced High/Medium findings
  confidence: float                   # 0..1
  surfaced: bool                      # set downstream by cap + threshold; NOT by the model
  cleared_reason: str | null          # if not surfaced: why (e.g. "addressed in discharge addendum d14")
}

Status = one of:
  CONFIRMED_ADDRESSED     # loop closed (possibly in different words) — SUPPRESS
  UNCONFIRMED             # a capable later note exists but never acknowledges the thread — ESCALATE
  CONTRADICTED            # notes disagree (e.g. active in progress notes, absent from discharge problem list)
  PENDING_AT_DISCHARGE    # unresolved at discharge with no documented follow-up plan — ESCALATE

TimelineEvent {
  day: int
  note_type: NoteType
  source_note_id: str
  excerpt: str                        # verbatim substring when evidence_kind=presence
  evidence_kind: "presence" | "absence_context"
}

Action {
  kind: "addendum" | "pcp_message" | "order" | "appointment_request"
  target: str                         # e.g. "discharge summary", "PCP", "scheduling"
  draft_text: str
  citation_note_id: str               # the evidence this action rests on
}
```

**Evidence rules (anti-hallucination — enforced by the harness):**
- `evidence_kind: presence` → `excerpt` MUST be an exact substring of the referenced note's body. Validated automatically; non-matching → finding rejected.
- `evidence_kind: absence_context` → cite the section that *should* contain the item (e.g. the discharge Follow-up section) verbatim, and reason in `connection` about the omission. Used to evidence a gap; not substring-required to name the missing thing, but the cited context text must itself be a real substring.

---

## Top-level output: `SweepResult`

```
SweepResult {
  chart_id: str
  summary_line: str                   # e.g. "3 unreconciled threads across a 14-day stay" — the 2-sec bookend, NOT a dashboard
  findings: Finding[]                 # surfaced=true only, ranked by (risk_weight * confidence) desc
  cleared: Finding[]                  # surfaced=false, collapsed by default (Q&A material)
  run_meta: RunMeta
}
```

**Ranking + surfacing:** `risk_weight` = High 3 / Medium 2 / Low 1. Surface if `confidence >= ABSTAIN_THRESHOLD` (default 0.6) AND rank within `TOP_N` (default 4). Everything else → `cleared` with a reason. The cap is structural anti-dashboard enforcement.

---

## `RunMeta` + run log (also the reliability exhibit for Ricci)

```
RunMeta {
  model_reasoning: str                # "claude-opus-4-8"
  model_extraction: str               # "claude-haiku-4-5-20251001"
  chart_id: str
  context_tokens: int
  latency_ms: { index: int, reason: int, draft: int }
  citation_validation: { checked: int, passed: int, failed: int }
  eval: EvalSummary | null            # populated when run against ground truth
}

EvalSummary {
  precision: float                    # TARGET 1.0 on the live set (a false positive is fatal on stage)
  recall: float
  per_item: { planted_id: str, expected_status: str, got_status: str, outcome: "TP"|"FP"|"FN"|"TN" }[]
  suppression_traces: { thread_id: str, reason: str }[]   # gold for Q&A
  abstentions: { thread_id: str, trigger: str }[]
}
```

Log every finding's raw model output, assigned status, confidence, citations + validation result, and TP/FP/FN vs. ground truth. Log suppression traces verbatim — that's the "reasons about equivalence, knows when to shut up" evidence.
