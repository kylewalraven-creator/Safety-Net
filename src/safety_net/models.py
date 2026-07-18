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
