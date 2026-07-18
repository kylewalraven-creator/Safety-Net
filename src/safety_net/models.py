"""Data models for Safety Net.

This module has two clearly separated sections:

1. FROZEN RECONCILIATION CONTRACT — the finding/reconciliation JSON contract,
   transcribed field-for-field from ``docs/reconciliation-prompt.md``. This is
   the keystone that the UI and the agent are built against in parallel. Do NOT
   add, rename, or reorder fields here; the strings the Opus prompt emits must
   round-trip through these models unchanged.

2. SUPPORTING DATA + ORCHESTRATION MODELS — the raw report/study/action/audit
   data model from ``docs/master-blueprint.md`` §4, plus small aggregation types
   the deterministic sweep and the UI use. These are internal and never travel
   in or out of the Opus reconciliation call.

Enum members use UPPERCASE names (keyword-safe, e.g. ``PASS``) but carry the
exact lowercase/uppercase string *values* the contract specifies, so JSON
round-trips exactly.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# ======================================================================
# SECTION 1 — FROZEN RECONCILIATION CONTRACT (docs/reconciliation-prompt.md)
# ======================================================================


# ---- Controlled vocabularies -----------------------------------------


class Verdict(str, Enum):
    """Per-candidate verdict (choose exactly one)."""

    SATISFIES = "SATISFIES"
    SUPERSEDES = "SUPERSEDES"
    PARTIAL = "PARTIAL"
    UNCONFIRMED = "UNCONFIRMED"
    INADEQUATE = "INADEQUATE"
    NO_EVIDENCE = "NO_EVIDENCE"


class Confidence(str, Enum):
    """Confidence in the verdict."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ClosureState(str, Enum):
    """Aggregate closure state for the recommendation (choose exactly one).

    Note: ``scheduled`` is intentionally absent — per the prompt doc it is set
    upstream from order/appointment data, not by the reconciliation engine.
    """

    COMPLETED = "completed"
    SUPERSEDED = "superseded"
    DECLINED = "declined"
    OVERRODE = "overrode"
    OPEN_OVERDUE = "open_overdue"
    ESCALATE = "escalate"


class ModalityResult(str, Enum):
    """Result vocabulary for the modality_adequacy axis."""

    SUPERIOR = "superior"
    PASS = "pass"
    FAIL = "fail"
    UNCLEAR = "unclear"


class PassFailUnclear(str, Enum):
    """Result vocabulary for anatomic_coverage and finding_acknowledgment."""

    PASS = "pass"
    FAIL = "fail"
    UNCLEAR = "unclear"


class TemporalResult(str, Enum):
    """Result vocabulary for the temporal_adequacy axis."""

    ON_TIME = "on_time"
    LATE = "late"
    NEVER = "never"
    UNCLEAR = "unclear"


class TerminalResult(str, Enum):
    """Result vocabulary for the terminal_event axis."""

    PRESENT = "present"
    ABSENT = "absent"


class TerminalType(str, Enum):
    """Type of terminal event (``none`` when absent)."""

    RESOLVED = "resolved"
    BENIGN = "benign"
    BIOPSY = "biopsy"
    DECLINED = "declined"
    OVERRODE = "overrode"
    NONE = "none"


# ---- Evidence + axis results -----------------------------------------


class Evidence(BaseModel):
    """A verbatim quote from a source document, tagged with its source_id."""

    source_id: str
    quote: str


class ModalityAxis(BaseModel):
    result: ModalityResult
    reason: str
    evidence: list[Evidence] = Field(default_factory=list)


class CoverageAxis(BaseModel):
    """Used for both anatomic_coverage and finding_acknowledgment."""

    result: PassFailUnclear
    reason: str
    evidence: list[Evidence] = Field(default_factory=list)


class TemporalAxis(BaseModel):
    result: TemporalResult
    reason: str
    evidence: list[Evidence] = Field(default_factory=list)


class TerminalEventAxis(BaseModel):
    result: TerminalResult
    type: TerminalType
    reason: str
    evidence: list[Evidence] = Field(default_factory=list)


class Axes(BaseModel):
    """The five axes, every candidate evaluated on all five."""

    modality_adequacy: ModalityAxis
    anatomic_coverage: CoverageAxis
    finding_acknowledgment: CoverageAxis
    temporal_adequacy: TemporalAxis
    terminal_event: TerminalEventAxis


class CandidateAssessment(BaseModel):
    study_id: str
    verdict: Verdict
    axes: Axes
    confidence: Confidence
    rationale: str


class Escalation(BaseModel):
    required: bool
    question: str | None = None


class ReconciliationResult(BaseModel):
    """The strict-JSON object emitted by the Opus reconciliation prompt."""

    recommendation_id: str
    candidate_assessments: list[CandidateAssessment] = Field(default_factory=list)
    closure_state: ClosureState
    escalation: Escalation


# ---- Reconciliation call INPUT ---------------------------------------


class Recommendation(BaseModel):
    """One extracted follow-up recommendation (the "finding" object).

    This is the exact shape passed into the reconciliation call.
    """

    id: str
    source_id: str
    report_date: str
    finding: str
    anatomic_site: str
    recommended_modality: str
    recommended_timeframe: str
    urgency_tier: str
    original_text: str


class Candidate(BaseModel):
    """A later study offered as a candidate for a recommendation."""

    id: str
    report_date: str
    modality: str
    anatomic_coverage: str
    impression_text: str
    full_text: str


class ReconciliationInput(BaseModel):
    """The user-message payload for the reconciliation call."""

    recommendation: Recommendation
    candidates: list[Candidate] = Field(default_factory=list)
    as_of_date: str


# ======================================================================
# SECTION 2 — SUPPORTING DATA + ORCHESTRATION (docs/master-blueprint.md §4)
# ======================================================================


class Report(BaseModel):
    """A raw finished report loaded from the backlog."""

    report_id: str
    patient_id: str
    date: str
    modality: str
    specialty: str
    full_text: str


class Study(BaseModel):
    """A performed exam extracted from a report; convertible to a Candidate."""

    study_id: str
    patient_id: str
    report_id: str
    date: str
    modality: str
    anatomic_coverage: str
    impression_text: str
    full_text: str

    def to_candidate(self) -> Candidate:
        """Project this study into the reconciliation Candidate contract."""
        return Candidate(
            id=self.study_id,
            report_date=self.date,
            modality=self.modality,
            anatomic_coverage=self.anatomic_coverage,
            impression_text=self.impression_text,
            full_text=self.full_text,
        )


class ActionType(str, Enum):
    PATIENT_LETTER = "patient_letter"
    PROVIDER_MESSAGE = "provider_message"
    ORDER = "order"


class ActionStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"


class ActionDraft(BaseModel):
    """A human-in-the-loop outreach/order draft. No action is autonomous."""

    action_id: str
    rec_id: str
    type: ActionType
    draft_text: str
    status: ActionStatus = ActionStatus.DRAFT
    approver: str | None = None
    ts: str | None = None


class AuditEvent(BaseModel):
    """Append-only audit record."""

    ts: str
    actor: str
    action: str
    rec_id: str
    detail: str


# ---- Extraction + sweep aggregates -----------------------------------


class ExtractionResult(BaseModel):
    """What Haiku extraction yields for a single report: the follow-up
    recommendations stated in it, plus the report itself as a study that could
    later serve as a candidate for an earlier recommendation."""

    recommendations: list[Recommendation] = Field(default_factory=list)
    study: Study


class RecommendationOutcome(BaseModel):
    """One recommendation after the full sweep: its candidates, the Opus
    reconciliation result, the code-computed overdue flag, and any drafted
    action. Ties the pieces together for the state machine and the UI."""

    recommendation: Recommendation
    patient_id: str
    candidates: list[Candidate] = Field(default_factory=list)
    reconciliation: ReconciliationResult | None = None
    overdue: bool = False
    action: ActionDraft | None = None


class SweepResult(BaseModel):
    """The whole-backlog result. The aggregate counts drive the two-second
    bookend only — never a dashboard."""

    model_config = ConfigDict(extra="forbid")

    as_of_date: str
    report_count: int = 0
    recommendation_count: int = 0
    outcomes: list[RecommendationOutcome] = Field(default_factory=list)


class HeroCase(BaseModel):
    """A hand-authored hero case loaded from data/heroes/*.json."""

    case_id: str
    title: str
    patient_id: str
    patient_name: str
    as_of_date: str
    reports: list[Report] = Field(default_factory=list)
    # Expected outcome — demo/test metadata only, NOT part of any wire contract.
    expected_closure_state: ClosureState | None = None
    expected_escalation: bool | None = None
    note: str | None = None


# ======================================================================
# SECTION 3 — WHOLE-CHART REVIEW CONTRACT (the discharge whole-chart pivot)
#
# Transcribed from the FROZEN ``01-schema-contract.md`` (the single source of
# truth every whole-chart component codes against). The contract's notation is
# readable-typed pseudo-schema; this is its Pydantic form. JSON string *values*
# are frozen and match the contract exactly; class *names* follow repo
# convention where the contract leaves that to the repo.
#
# ADDITIVE ONLY: Sections 1 & 2 (the Safety Net contract) are untouched, so
# Safety Net stays runnable as the fallback demo. As with Section 1, the fields
# the Opus whole-chart prompt emits (``Finding`` + members) must round-trip
# unchanged — do NOT rename or reorder them.
#
# Two deliberate, noted name deviations (values/shape match the contract):
#  - contract ``SweepResult`` -> ``ChartReviewResult`` (Section 2 already owns
#    ``SweepResult`` for the radiology sweep; one package can't hold both).
#  - contract ``Status`` -> ``ThreadStatus`` (clearer; bare ``Status`` is
#    ambiguous next to Section 1/2's ``*Status`` enums). Values are identical.
# ======================================================================


# ---- Controlled vocabularies -----------------------------------------


class NoteType(str, Enum):
    """The frozen note-type vocabulary (contract: Input.NoteType)."""

    PROGRESS_NOTE = "progress_note"
    CONSULT_NOTE = "consult_note"
    RADIOLOGY_REPORT = "radiology_report"
    LAB_RESULT = "lab_result"
    MICRO_RESULT = "micro_result"
    MED_RECONCILIATION = "med_reconciliation"
    MED_ADMIN = "med_admin"
    PROCEDURE_NOTE = "procedure_note"
    NURSING_NOTE = "nursing_note"
    DISCHARGE_SUMMARY = "discharge_summary"
    DISCHARGE_ADDENDUM = "discharge_addendum"
    PCP_LETTER = "pcp_letter"


class SignalType(str, Enum):
    """Widened extraction taxonomy (contract: Stage 1; maps to iteration §2 A–I)."""

    INCIDENTAL_FINDING = "incidental_finding"  # A: incidental/secondary findings
    PENDING_RESULT = "pending_result"  # B: results in limbo at discharge
    TREND = "trend"  # C: point-normal, trend-abnormal series
    MED_RECON_GAP = "med_recon_gap"  # D: med-reconciliation gaps
    CONSULT_RECOMMENDATION = "consult_recommendation"  # E: consult recs not closed
    DROPPED_THREAD = "dropped_thread"  # F: dropped symptom/assessment threads
    CROSS_DOMAIN_INTERACTION = "cross_domain_interaction"  # G: cross-domain
    CONTINUITY_GAP = "continuity_gap"  # H: care-continuity/disposition gaps
    DOCUMENTATION_CONTRADICTION = "documentation_contradiction"  # I: contradictions


class Risk(str, Enum):
    """Risk = CONSEQUENCE OF THE MISS, not raw finding severity (contract)."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ThreadStatus(str, Enum):
    """Per-thread reconciliation status (contract: Stage 3 ``Status``)."""

    CONFIRMED_ADDRESSED = "CONFIRMED_ADDRESSED"  # loop closed (reworded ok) — SUPPRESS
    UNCONFIRMED = "UNCONFIRMED"  # capable note silent / rec never in plan — ESCALATE
    CONTRADICTED = "CONTRADICTED"  # notes disagree — ESCALATE
    PENDING_AT_DISCHARGE = "PENDING_AT_DISCHARGE"  # unresolved, no plan — ESCALATE


class EvidenceKind(str, Enum):
    """presence -> excerpt is a verbatim substring; absence_context -> the
    section that SHOULD contain the item, cited verbatim to evidence a gap."""

    PRESENCE = "presence"
    ABSENCE_CONTEXT = "absence_context"


# ---- Input: ChartBundle (contract §Input) ----------------------------


class Patient(BaseModel):
    """Patient block of the ChartBundle. The four frozen fields plus optional
    display extras (patient_id / name / admission_reason) that are NOT part of
    the contract."""

    age: int
    sex: str
    admit_day: int = 1
    discharge_day: int = 14
    patient_id: str | None = None
    name: str | None = None
    admission_reason: str | None = None


class Note(BaseModel):
    """One note/event in the admission. ``note_id`` is stable and is what every
    citation (``timeline[].source_note_id``, ``suggested_action.citation_note_id``)
    references. Citations must be exact substrings of ``body``."""

    note_id: str
    day: int  # 1..14
    timestamp: str  # ISO; ordering is load-bearing
    author_role: str
    note_type: NoteType
    body: str


class ChartBundle(BaseModel):
    """A complete admission — the unit whole-chart review runs over."""

    chart_id: str
    patient: Patient
    notes: list[Note] = Field(default_factory=list)

    def note_by_id(self, note_id: str) -> Note | None:
        return next((n for n in self.notes if n.note_id == note_id), None)

    def notes_of_type(self, note_type: str) -> list[Note]:
        want = note_type.value if isinstance(note_type, NoteType) else note_type
        return [n for n in self.notes if n.note_type.value == want]

    def _first_of_type(self, note_type: str) -> Note | None:
        found = self.notes_of_type(note_type)
        return found[0] if found else None

    @property
    def discharge_summary(self) -> Note | None:
        return self._first_of_type("discharge_summary")

    @property
    def discharge_addendum(self) -> Note | None:
        return self._first_of_type("discharge_addendum")

    @property
    def pcp_letter(self) -> Note | None:
        return self._first_of_type("pcp_letter")

    def discharge_documents(self) -> list[Note]:
        """The three closure documents the reasoner reads against every thread."""
        return [
            n
            for n in (self.discharge_summary, self.discharge_addendum, self.pcp_letter)
            if n is not None
        ]


# ---- Stage 1 output: ExtractedSignal (Haiku, bulk) -------------------


class ExtractedSignal(BaseModel):
    """One atomic signal extracted from a single note. ``entity`` is the
    canonical snake_case key threading groups on (e.g. ``apixaban``,
    ``pulmonary_nodule_lll``). ``verbatim_excerpt`` MUST be an exact substring
    of the source note body — enforced at extraction and again in the harness."""

    signal_id: str
    source_note_id: str
    day: int
    signal_type: SignalType
    entity: str
    summary: str  # one-line paraphrase (NOT cited)
    verbatim_excerpt: str


# ---- Stage 2 output: Thread (deterministic code — no LLM) ------------


class Thread(BaseModel):
    """All events about one entity across the stay. Built by grouping signals on
    ``entity`` and sorting by (day, timestamp). Single-event threads are valid."""

    thread_id: str
    entity: str
    signal_type: SignalType  # dominant type across the thread's signals
    event_signal_ids: list[str] = Field(default_factory=list)  # sorted (day, ts)
    first_day: int
    last_day: int


# ---- Stage 3 output: Finding (Opus, the reasoning hero) --------------


class TimelineEvent(BaseModel):
    """One ordered evidence event in a Finding. ``note_type`` is kept as a plain
    string (a NoteType value) for robustness to model output."""

    day: int
    note_type: str
    source_note_id: str
    excerpt: str  # verbatim substring when evidence_kind == presence
    evidence_kind: EvidenceKind


class SuggestedAction(BaseModel):
    """A draftable artifact a human approves. ``null`` for CONFIRMED_ADDRESSED.
    ``kind`` is one of addendum | pcp_message | order | appointment_request."""

    kind: str
    target: str
    draft_text: str
    citation_note_id: str


class Finding(BaseModel):
    """The strict-JSON object Opus emits per Thread. ``finding_id``, ``surfaced``
    and ``cleared_reason`` are set by the pipeline, never by the model."""

    finding_id: str = ""  # pipeline-assigned
    thread_id: str
    title: str
    risk: Risk
    status: ThreadStatus
    connection: str
    timeline: list[TimelineEvent] = Field(default_factory=list)
    question: str = ""
    suggested_action: SuggestedAction | None = None
    confidence: float
    surfaced: bool = False  # set downstream by cap + threshold; NOT by the model
    cleared_reason: str | None = None

    def presence_excerpts(self) -> list[tuple[str, str]]:
        """(source_note_id, excerpt) for every presence timeline event — the set
        the citation validator must confirm are exact substrings."""
        return [
            (e.source_note_id, e.excerpt)
            for e in self.timeline
            if e.evidence_kind is EvidenceKind.PRESENCE
        ]


# ---- Run logging + eval oracle (contract §RunMeta) -------------------


class LatencyMs(BaseModel):
    index: int = 0  # extraction + threading
    reason: int = 0  # Opus reconciliation
    draft: int = 0  # action drafting


class CitationValidation(BaseModel):
    checked: int = 0
    passed: int = 0
    failed: int = 0


class PerItem(BaseModel):
    """One scored planted item (contract: EvalSummary.per_item)."""

    planted_id: str
    expected_status: str
    got_status: str
    outcome: str  # "TP" | "FP" | "FN" | "TN"
    entity: str | None = None  # display extra


class SuppressionTrace(BaseModel):
    thread_id: str
    reason: str


class Abstention(BaseModel):
    thread_id: str
    trigger: str


class EvalSummary(BaseModel):
    """The self-verification gate output (contract §EvalSummary)."""

    precision: float
    recall: float
    per_item: list[PerItem] = Field(default_factory=list)
    suppression_traces: list[SuppressionTrace] = Field(default_factory=list)
    abstentions: list[Abstention] = Field(default_factory=list)
    # convenience extras (not part of the frozen contract):
    passed_gate: bool = False
    notes: list[str] = Field(default_factory=list)


class RunMeta(BaseModel):
    """Per-run reliability log (contract §RunMeta). ``eval`` is populated when a
    run is scored against ground truth; ``live`` distinguishes a real LLM run
    from the deterministic cache path (a repo extra)."""

    model_reasoning: str  # "claude-opus-4-8"
    model_extraction: str  # "claude-haiku-4-5-20251001"
    chart_id: str
    context_tokens: int = 0
    latency_ms: LatencyMs = Field(default_factory=LatencyMs)
    citation_validation: CitationValidation = Field(default_factory=CitationValidation)
    eval: EvalSummary | None = None
    started_at: str | None = None  # repo extra
    live: bool = False  # repo extra


class ChartReviewResult(BaseModel):
    """The whole-chart review output (contract: ``SweepResult``, renamed to avoid
    colliding with Section 2's). ``summary_line`` is the 2-second bookend;
    ``findings`` is ranked and TOP_N-capped (surfaced only); ``cleared`` holds
    everything considered and correctly suppressed/abstained."""

    chart_id: str
    summary_line: str
    findings: list[Finding] = Field(default_factory=list)
    cleared: list[Finding] = Field(default_factory=list)
    run_meta: RunMeta | None = None


# ---- Ground-truth manifest loader (doc 02 oracle) --------------------
# Not part of the wire contract: it loads the planted-dot table the harness
# scores against. EvalSummary.per_item is the contract-facing scoring output.


class PlantedItem(BaseModel):
    planted_id: str
    entity: str
    note_types: list[str] = Field(default_factory=list)
    expected_status: ThreadStatus
    expected_risk: Risk | None = None
    surfaced: bool  # the pass/fail expectation
    live: str  # "live" | "precompute"
    # A pinned excerpt that uniquely identifies this dot by the EVIDENCE it cites,
    # so the harness can match a finding even when live extraction names the entity
    # differently (e.g. colonoscopy_followup_diverticulitis). Robust oracle.
    match_excerpt: str | None = None


class GroundTruth(BaseModel):
    chart_id: str
    items: list[PlantedItem] = Field(default_factory=list)

    def by_entity(self, entity: str) -> PlantedItem | None:
        return next((i for i in self.items if i.entity == entity), None)


# ---- Frozen constants (contract §Ranking + surfacing) ----------------

ABSTAIN_THRESHOLD: float = 0.6  # confidence below this -> cleared (abstain)
TOP_N: int = 4  # hard cap on surfaced findings (anti-dashboard discipline)
RISK_WEIGHT: dict[Risk, int] = {Risk.HIGH: 3, Risk.MEDIUM: 2, Risk.LOW: 1}
