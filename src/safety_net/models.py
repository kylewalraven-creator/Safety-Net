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
# This is the FROZEN data contract for whole-chart review. It was reconstructed
# from the handoff docs because ``01-schema-contract.md`` was absent from the
# handoff bundle: the ``Finding`` JSON is transcribed field-for-field from
# ``03-whole-chart-reasoning-prompt.md``; the taxonomy from the iteration doc
# §2; the ground-truth manifest and pinned strings from
# ``02-synthetic-data-spec.md``; the constants and eval spec from
# ``04-build-plan.md``.
#
# ADDITIVE ONLY: Sections 1 & 2 (the Safety Net contract) are untouched, so
# Safety Net stays runnable as the fallback demo. As with Section 1, the strings
# the Opus whole-chart prompt emits must round-trip through ``Finding`` and its
# members unchanged — do NOT rename or reorder those fields.
# ======================================================================


# ---- Controlled vocabularies -----------------------------------------


class SignalType(str, Enum):
    """The widened extraction taxonomy — the nine signal families the agent
    scans for across the full record (iteration doc §2, A–I). This is the
    "recommendation -> signal" widening of the Safety Net extractor."""

    ORPHANED_INCIDENTAL = "orphaned_incidental"  # A: incidental/secondary findings
    PENDING_RESULT = "pending_result"  # B: results in limbo at discharge
    TREND = "trend"  # C: point-normal, trend-abnormal series
    MED_RECONCILIATION = "med_reconciliation"  # D: med-rec gaps
    CONSULT_RECOMMENDATION = "consult_recommendation"  # E: consult recs not closed
    DROPPED_SYMPTOM = "dropped_symptom"  # F: dropped symptom/assessment threads
    CROSS_DOMAIN = "cross_domain"  # G: cross-domain interactions
    CARE_CONTINUITY = "care_continuity"  # H: care-continuity/disposition gaps
    DOCUMENTATION_CONTRADICTION = "documentation_contradiction"  # I: contradictions


class Risk(str, Enum):
    """Risk = CONSEQUENCE OF THE MISS, not raw finding severity (doc 03)."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ThreadStatus(str, Enum):
    """Per-thread reconciliation status (doc 03). Extends the Safety Net enum
    to the whole-chart, four-status world."""

    CONFIRMED_ADDRESSED = "CONFIRMED_ADDRESSED"  # loop closed (possibly reworded)
    UNCONFIRMED = "UNCONFIRMED"  # capable note silent, or rec never in plan
    CONTRADICTED = "CONTRADICTED"  # notes disagree
    PENDING_AT_DISCHARGE = "PENDING_AT_DISCHARGE"  # unresolved, no follow-up plan


class EvidenceKind(str, Enum):
    """Whether a timeline excerpt attests presence of text, or the context of an
    absence (the section that SHOULD contain the item)."""

    PRESENCE = "presence"
    ABSENCE_CONTEXT = "absence_context"


# ---- Chart ingestion models ------------------------------------------


class Note(BaseModel):
    """One note/event in the admission. ``note_id`` is stable and is what
    ``timeline[].source_note_id`` and ``suggested_action.citation_note_id``
    reference. ``body`` is the verbatim text; every ``presence`` excerpt must be
    an exact substring of some note's ``body``."""

    note_id: str
    day: int
    timestamp: str
    author_role: str
    note_type: str
    body: str


class ChartBundle(BaseModel):
    """A complete admission — the unit the whole-chart review runs over."""

    chart_id: str
    patient_id: str
    patient_name: str
    age: int
    sex: str
    admission_reason: str
    admit_date: str
    discharge_date: str
    notes: list[Note] = Field(default_factory=list)

    def note_by_id(self, note_id: str) -> Note | None:
        return next((n for n in self.notes if n.note_id == note_id), None)

    def notes_of_type(self, note_type: str) -> list[Note]:
        return [n for n in self.notes if n.note_type == note_type]

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


class ExtractedSignal(BaseModel):
    """One atomic signal extracted (by Haiku) from a single note. ``entity`` is
    the canonical key threading groups on (e.g. ``apixaban``,
    ``pulmonary_nodule_lll``). ``verbatim_excerpt`` MUST be an exact substring
    of the source note's ``body`` — enforced at extraction and again in the
    harness."""

    signal_id: str
    note_id: str
    day: int
    note_type: str
    signal_type: SignalType
    entity: str
    description: str
    verbatim_excerpt: str
    value: str | None = None  # optional structured value, e.g. a lab "1.6 mg/dL"


class Thread(BaseModel):
    """All events about one entity across the stay, in temporal order. Built by
    the deterministic threading module — no LLM."""

    thread_id: str
    entity: str
    signal_type: SignalType
    events: list[ExtractedSignal] = Field(default_factory=list)


# ---- Reconciliation OUTPUT: the Finding contract (doc 03, verbatim) ---


class TimelineEvent(BaseModel):
    """One ordered event in a Finding's evidence timeline."""

    day: int
    note_type: str
    source_note_id: str
    excerpt: str
    evidence_kind: EvidenceKind


class SuggestedAction(BaseModel):
    """A draftable artifact a human approves (addendum line, PCP message, order
    text). ``null`` for CONFIRMED_ADDRESSED findings."""

    kind: str
    target: str
    draft_text: str
    citation_note_id: str


class Finding(BaseModel):
    """The strict-JSON object Opus emits per Thread (doc 03). ``surfaced`` and
    ``cleared_reason`` are set by the pipeline, never by the model."""

    thread_id: str
    title: str
    risk: Risk
    status: ThreadStatus
    connection: str
    timeline: list[TimelineEvent] = Field(default_factory=list)
    question: str = ""
    suggested_action: SuggestedAction | None = None
    confidence: float
    # Pipeline-set (grounding/ranking stage) — NOT part of the model's output.
    surfaced: bool | None = None
    cleared_reason: str | None = None

    def presence_excerpts(self) -> list[tuple[str, str]]:
        """(source_note_id, excerpt) for every presence timeline event — the
        set the citation validator must confirm are exact substrings."""
        return [
            (e.source_note_id, e.excerpt)
            for e in self.timeline
            if e.evidence_kind is EvidenceKind.PRESENCE
        ]


# ---- Run logging + eval oracle ---------------------------------------


class RunMeta(BaseModel):
    """Per-run reliability log (iteration §5). ``live`` distinguishes a real
    LLM run from the deterministic cache path."""

    chart_id: str
    started_at: str
    live: bool
    model_opus: str
    model_haiku: str
    note_count: int = 0
    signal_count: int = 0
    thread_count: int = 0
    finding_count: int = 0
    cleared_count: int = 0
    latency_ms: dict[str, float] = Field(default_factory=dict)  # per-stage
    abstained: list[str] = Field(default_factory=list)  # thread_ids below threshold


class ChartReviewResult(BaseModel):
    """The whole-chart review output. ``summary_line`` is the 2-second bookend;
    ``findings`` is ranked and TOP_N-capped; ``cleared`` holds everything
    considered and correctly suppressed/abstained (the noise-discipline proof)."""

    chart_id: str
    summary_line: str
    findings: list[Finding] = Field(default_factory=list)
    cleared: list[Finding] = Field(default_factory=list)
    run_meta: RunMeta | None = None


class PlantedItem(BaseModel):
    """One row of the ground-truth manifest (doc 02) — the eval oracle."""

    planted_id: str
    entity: str
    note_types: list[str] = Field(default_factory=list)
    expected_status: ThreadStatus
    expected_risk: Risk | None = None
    surfaced: bool  # the pass/fail expectation
    live: str  # "live" | "precompute"


class GroundTruth(BaseModel):
    chart_id: str
    items: list[PlantedItem] = Field(default_factory=list)

    def by_entity(self, entity: str) -> PlantedItem | None:
        return next((i for i in self.items if i.entity == entity), None)


class CitationCheck(BaseModel):
    thread_id: str
    source_note_id: str
    excerpt: str
    ok: bool


class ItemScore(BaseModel):
    planted_id: str
    entity: str
    expected_surfaced: bool
    actual_surfaced: bool
    expected_status: ThreadStatus
    actual_status: ThreadStatus | None = None
    outcome: str  # "TP" | "FP" | "FN" | "TN"


class EvalSummary(BaseModel):
    """The self-verification gate output (doc 04 Step 7)."""

    model_config = ConfigDict(extra="forbid")

    chart_id: str
    precision: float
    recall: float
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    item_scores: list[ItemScore] = Field(default_factory=list)
    citation_checks: list[CitationCheck] = Field(default_factory=list)
    all_citations_valid: bool = True
    unexpected_entities: list[str] = Field(default_factory=list)  # surfaced, unplanted
    passed_gate: bool = False
    notes: list[str] = Field(default_factory=list)


# ---- Frozen constants (doc 04) ---------------------------------------

ABSTAIN_THRESHOLD: float = 0.6  # confidence below this -> cleared (abstain), not surfaced
TOP_N: int = 4  # hard cap on surfaced findings (the anti-dashboard discipline)
RISK_WEIGHT: dict[Risk, int] = {Risk.HIGH: 3, Risk.MEDIUM: 2, Risk.LOW: 1}
