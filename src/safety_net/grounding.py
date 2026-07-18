"""Grounding, ranking, and surfacing — Stage 5 of the whole-chart pipeline.

Two jobs, both pure code:

1. **Citation validation (anti-hallucination).** Every ``presence`` timeline
   excerpt must be an exact substring of its cited note body. Findings that fail
   are REJECTED upstream (dropped from both ``findings`` and ``cleared``) so the
   harness's substring gate never sees a bad citation. Same discipline as Safety
   Net's evidence rule, applied to the whole-chart Finding.

2. **Ranking + surfacing (anti-dashboard).** CONFIRMED_ADDRESSED loops are
   suppressed to ``cleared``. Escalate-status findings surface only if
   ``confidence >= ABSTAIN_THRESHOLD`` AND they rank within ``TOP_N`` by
   ``risk_weight * confidence``. Everything else is cleared with a reason. The
   cap is structural — precision over recall, by construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import (
    ABSTAIN_THRESHOLD,
    RISK_WEIGHT,
    TOP_N,
    ChartBundle,
    EvidenceKind,
    Finding,
    ThreadStatus,
)

# Escalate statuses (the reasoner surfaces these; CONFIRMED_ADDRESSED is suppressed).
SURFACE_STATUSES = {
    ThreadStatus.UNCONFIRMED,
    ThreadStatus.CONTRADICTED,
    ThreadStatus.PENDING_AT_DISCHARGE,
}


@dataclass
class CitationResult:
    thread_id: str
    source_note_id: str
    excerpt: str
    ok: bool


@dataclass
class SurfacingResult:
    surfaced: list[Finding] = field(default_factory=list)
    cleared: list[Finding] = field(default_factory=list)
    rejected: list[Finding] = field(default_factory=list)  # invalid citations -> dropped
    duplicates: list[Finding] = field(default_factory=list)  # same-evidence dups -> dropped
    citation_results: list[CitationResult] = field(default_factory=list)
    abstentions: list[tuple[str, str]] = field(default_factory=list)  # (thread_id, trigger)

    @property
    def citation_counts(self) -> tuple[int, int, int]:
        checked = len(self.citation_results)
        passed = sum(1 for c in self.citation_results if c.ok)
        return checked, passed, checked - passed


def validate_citations(finding: Finding, bundle: ChartBundle) -> list[CitationResult]:
    """Check every presence excerpt is an exact substring of its cited note."""
    results: list[CitationResult] = []
    for note_id, excerpt in finding.presence_excerpts():
        note = bundle.note_by_id(note_id)
        ok = note is not None and excerpt in note.body
        results.append(CitationResult(finding.thread_id, note_id, excerpt, ok))
    return results


def rank_score(finding: Finding) -> float:
    """risk_weight * confidence (contract §Ranking + surfacing)."""
    return RISK_WEIGHT.get(finding.risk, 1) * finding.confidence


def _presence_pairs(finding: Finding) -> list[tuple[str, str]]:
    return [
        (e.source_note_id, e.excerpt)
        for e in finding.timeline
        if e.evidence_kind is EvidenceKind.PRESENCE
    ]


def _same_evidence(a: Finding, b: Finding) -> bool:
    """True if two findings rest on the same evidence — a shared presence citation
    (same note, and one excerpt equal to or containing the other). Catches a
    semantic duplicate where extraction split one thread into two entities (e.g. a
    nodule finding vs. its recommended follow-up CT), which suffix-canonicalization
    cannot merge because the keys share no stem."""
    for na, xa in _presence_pairs(a):
        for nb, xb in _presence_pairs(b):
            if na == nb and (xa == xb or xa in xb or xb in xa):
                return True
    return False


def dedupe_by_evidence(findings: list[Finding]) -> tuple[list[Finding], list[Finding]]:
    """Collapse findings that rest on the same evidence, keeping the highest
    confidence one. Returns (kept, dropped)."""
    kept: list[Finding] = []
    dropped: list[Finding] = []
    for f in sorted(findings, key=lambda x: x.confidence, reverse=True):
        if any(_same_evidence(f, k) for k in kept):
            f.surfaced = False
            f.cleared_reason = "duplicate — same evidence as a higher-confidence finding"
            dropped.append(f)
        else:
            kept.append(f)
    return kept, dropped


def _addressed_reason(finding: Finding) -> str:
    cites = ", ".join(sorted({nid for nid, _ in finding.presence_excerpts()}))
    return f"CONFIRMED_ADDRESSED — loop closed; cited to {cites or 'the discharge documentation'}"


def apply_surfacing(
    findings: list[Finding],
    bundle: ChartBundle,
    *,
    abstain_threshold: float = ABSTAIN_THRESHOLD,
    top_n: int = TOP_N,
) -> SurfacingResult:
    """Validate citations, then partition findings into surfaced / cleared /
    rejected and stamp ``surfaced`` + ``cleared_reason`` on each."""
    res = SurfacingResult()

    valid: list[Finding] = []
    for f in findings:
        checks = validate_citations(f, bundle)
        res.citation_results.extend(checks)
        if all(c.ok for c in checks):
            valid.append(f)
        else:
            f.surfaced = False
            f.cleared_reason = "REJECTED — a presence citation is not a verbatim substring"
            res.rejected.append(f)

    # Collapse semantic duplicates (two entities, same evidence) BEFORE ranking,
    # so a duplicate neither surfaces nor consumes a TOP_N slot.
    valid, dups = dedupe_by_evidence(valid)
    res.duplicates.extend(dups)

    # Candidates to surface = escalate statuses with confidence at/above threshold.
    candidates: list[Finding] = []
    cleared: list[Finding] = []
    for f in valid:
        if f.status not in SURFACE_STATUSES:
            f.surfaced = False
            f.cleared_reason = _addressed_reason(f)
            cleared.append(f)
        elif f.confidence < abstain_threshold:
            f.surfaced = False
            f.cleared_reason = (
                f"abstained — confidence {f.confidence:.2f} < {abstain_threshold:.2f}"
            )
            res.abstentions.append((f.thread_id, f.cleared_reason))
            cleared.append(f)
        else:
            candidates.append(f)

    candidates.sort(key=rank_score, reverse=True)
    for i, f in enumerate(candidates):
        if i < top_n:
            f.surfaced = True
            f.cleared_reason = None
            res.surfaced.append(f)
        else:
            f.surfaced = False
            f.cleared_reason = f"below the top-{top_n} cap (rank {i + 1})"
            cleared.append(f)

    cleared.sort(key=rank_score, reverse=True)
    res.cleared = cleared
    return res
