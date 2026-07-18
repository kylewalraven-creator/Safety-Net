"""Deterministic, code-orchestrated backlog sweep.

This orchestration is plain Python, not an autonomous agent — the determinism
is intentional and is what produces the reliable "swept N reports" number. It
loads reports and runs the pipeline: extract (Haiku) -> candidate-match (code)
-> reconcile (Opus) -> draft action (Opus). Candidate-matching and the
overdue state machine are pure code; the reasoning steps are the agentic core.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path

from .actions import draft_action, should_draft
from .client import MissingAPIKeyError, has_api_key
from .extract import extract_reports
from .models import (
    Candidate,
    ClosureState,
    HeroCase,
    Recommendation,
    RecommendationOutcome,
    Report,
    Study,
    SweepResult,
)
from .reconcile import reconcile

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def _default_data_dir() -> Path:
    env = os.environ.get("SAFETY_NET_DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "data"


DATA_DIR = _default_data_dir()
HEROES_DIR = DATA_DIR / "heroes"
FILLER_DIR = DATA_DIR / "filler"
CACHE_DIR = DATA_DIR / "cache"


def default_as_of_date() -> str:
    return os.environ.get("SAFETY_NET_AS_OF_DATE") or _dt.date.today().isoformat()


# ---------------------------------------------------------------------------
# Candidate matching (pure code) — deliberately generous / recall-oriented.
# The Opus reconciliation makes the real adequacy judgment; the matcher only
# narrows the search space, so over-matching is safe and under-matching is not.
# ---------------------------------------------------------------------------

_REGION_SYNONYMS: dict[str, list[str]] = {
    "chest": [
        "chest", "thorax", "thoracic", "lung", "pulmon", "pleur", "mediastin",
        "hilar", "cardiopulmonary", "upper lobe", "lower lobe", "middle lobe",
        "rul", "lul", "rml", "rll", "lll", "bronch",
    ],
    "abdomen": [
        "abdomen", "abdominal", "liver", "hepatic", "renal", "kidney", "pancrea",
        "spleen", "splenic", "adrenal", "retroperiton", "bowel",
    ],
    "pelvis": [
        "pelvis", "pelvic", "bladder", "prostate", "adnexa", "ovary", "ovarian",
        "uterus", "uterine", "rectal", "rectum",
    ],
    "neck": ["neck", "thyroid", "parotid", "larynx", "supraclavicular"],
    "head": ["head", "brain", "cerebr", "intracran", "pituitary"],
    "spine": ["spine", "spinal", "vertebr", "lumbar", "disc"],
    "breast": ["breast", "mammar"],
    "msk": ["osseous", "fracture", "femur", "tibia", "humerus", "joint"],
}
_WHOLE_BODY_TRIGGERS = [
    "skull base to mid-thigh", "skull base to midthigh", "whole body",
    "whole-body", "total body", "torso", "pet/ct", "pet ct",
]
_WHOLE_BODY_REGIONS = {"chest", "abdomen", "pelvis", "neck"}


def regions_of(text: str) -> set[str]:
    """The set of coarse body regions a free-text string references."""
    t = (text or "").lower()
    regions: set[str] = set()
    if any(trigger in t for trigger in _WHOLE_BODY_TRIGGERS):
        regions |= _WHOLE_BODY_REGIONS
    for region, synonyms in _REGION_SYNONYMS.items():
        if any(s in t for s in synonyms):
            regions.add(region)
    return regions


def anatomic_overlap(anatomic_site: str, anatomic_coverage: str) -> bool:
    """Whether a study's coverage plausibly includes a finding's site."""
    site_regions = regions_of(anatomic_site)
    coverage_regions = regions_of(anatomic_coverage)
    if not site_regions or not coverage_regions:
        # Region undeterminable from text — be generous and let Opus judge.
        return True
    return bool(site_regions & coverage_regions)


def _parse_date(value: str) -> _dt.date | None:
    try:
        return _dt.date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return None


def _is_after(later: str, earlier: str) -> bool:
    d_later, d_earlier = _parse_date(later), _parse_date(earlier)
    if d_later is None or d_earlier is None:
        return True  # can't compare — keep the candidate rather than drop it
    return d_later > d_earlier


def match_candidates(
    recommendation: Recommendation,
    patient_id: str,
    studies: list[Study],
) -> list[Candidate]:
    """Later studies for the same patient with plausible anatomic overlap."""
    matched = [
        s
        for s in studies
        if s.patient_id == patient_id
        and s.report_id != recommendation.source_id
        and _is_after(s.date, recommendation.report_date)
        and anatomic_overlap(recommendation.anatomic_site, s.anatomic_coverage)
    ]
    matched.sort(key=lambda s: s.date)
    return [s.to_candidate() for s in matched]


# ---------------------------------------------------------------------------
# Overdue state machine (pure code) — naive date logic, for contrast with the
# reconciliation verdict. `overdue` is purely date-based on purpose.
# ---------------------------------------------------------------------------

_TIMEFRAME_RE = re.compile(r"(\d+)\s*(day|week|month|year)s?", re.IGNORECASE)
_UNIT_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}


def timeframe_to_days(timeframe: str) -> int | None:
    """Upper-bound the recommended interval in days (e.g. '3-6 months' -> 180)."""
    matches = _TIMEFRAME_RE.findall(timeframe or "")
    if not matches:
        return None
    return max(int(n) * _UNIT_DAYS[unit.lower()] for n, unit in matches)


def is_overdue(report_date: str, timeframe: str, as_of_date: str) -> bool:
    """True if the recommended window has passed as of `as_of_date`."""
    days = timeframe_to_days(timeframe)
    start, now = _parse_date(report_date), _parse_date(as_of_date)
    if days is None or start is None or now is None:
        return False
    return now > start + _dt.timedelta(days=days)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def reconcile_recommendation(
    recommendation: Recommendation,
    patient_id: str,
    studies: list[Study],
    as_of_date: str,
    *,
    draft: bool = True,
) -> RecommendationOutcome:
    """Match candidates, reconcile, compute overdue, and draft any action."""
    candidates = match_candidates(recommendation, patient_id, studies)
    result = reconcile(recommendation, candidates, as_of_date)
    overdue = is_overdue(
        recommendation.report_date, recommendation.recommended_timeframe, as_of_date
    )
    action = None
    if draft and should_draft(result):
        action = draft_action(recommendation, result)
    return RecommendationOutcome(
        recommendation=recommendation,
        patient_id=patient_id,
        candidates=candidates,
        reconciliation=result,
        overdue=overdue,
        action=action,
    )


def run_sweep(
    reports: list[Report],
    as_of_date: str,
    *,
    reconcile_patient_ids: set[str] | None = None,
    draft: bool = True,
) -> SweepResult:
    """Full backlog sweep. If `reconcile_patient_ids` is given, only those
    patients' recommendations are reconciled (bulk pre-run scope); all reports
    and recommendations are still counted for the aggregate bookend."""
    extractions = extract_reports(reports)
    studies = [e.study for e in extractions]
    patient_of = {r.report_id: r.patient_id for r in reports}

    outcomes: list[RecommendationOutcome] = []
    rec_count = 0
    for extraction in extractions:
        for rec in extraction.recommendations:
            rec_count += 1
            pid = patient_of.get(rec.source_id, "")
            if reconcile_patient_ids is not None and pid not in reconcile_patient_ids:
                continue
            outcomes.append(
                reconcile_recommendation(rec, pid, studies, as_of_date, draft=draft)
            )
    return SweepResult(
        as_of_date=as_of_date,
        report_count=len(reports),
        recommendation_count=rec_count,
        outcomes=outcomes,
    )


def run_hero_case(
    case: HeroCase,
    *,
    draft: bool = True,
    use_cache: bool = False,
    write_cache: bool = False,
) -> list[RecommendationOutcome]:
    """Run the full pipeline for one hero case (its reports only)."""
    if use_cache:
        cached = read_cache(case.case_id)
        if cached is not None:
            return cached

    extractions = extract_reports(case.reports)
    studies = [e.study for e in extractions]
    patient_of = {r.report_id: r.patient_id for r in case.reports}

    outcomes: list[RecommendationOutcome] = []
    for extraction in extractions:
        for rec in extraction.recommendations:
            pid = patient_of.get(rec.source_id, case.patient_id)
            outcomes.append(
                reconcile_recommendation(rec, pid, studies, case.as_of_date, draft=draft)
            )

    if write_cache:
        write_cache_file(case.case_id, outcomes)
    return outcomes


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _load_reports_from_file(path: Path) -> list[Report]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [Report.model_validate(d) for d in data]
    return [Report.model_validate(data)]


def load_filler(directory: Path = FILLER_DIR) -> list[Report]:
    if not directory.exists():
        return []
    reports: list[Report] = []
    for path in sorted(directory.glob("*.json")):
        reports.extend(_load_reports_from_file(path))
    return reports


def load_hero_case(path: Path) -> HeroCase:
    return HeroCase.model_validate_json(path.read_text(encoding="utf-8"))


def load_hero_cases(directory: Path = HEROES_DIR) -> list[HeroCase]:
    return [load_hero_case(p) for p in sorted(directory.glob("*.json"))]


def backlog_reports() -> list[Report]:
    """All reports for the sweep count: every hero report plus filler."""
    reports: list[Report] = []
    for case in load_hero_cases():
        reports.extend(case.reports)
    reports.extend(load_filler())
    return reports


# ---------------------------------------------------------------------------
# Caching (real captured hero responses; the offline demo fallback)
# ---------------------------------------------------------------------------


def cache_path(case_id: str) -> Path:
    return CACHE_DIR / f"{case_id}.json"


def write_cache_file(case_id: str, outcomes: list[RecommendationOutcome]) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = [o.model_dump(mode="json") for o in outcomes]
    path = cache_path(case_id)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_cache(case_id: str) -> list[RecommendationOutcome] | None:
    path = cache_path(case_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return [RecommendationOutcome.model_validate(o) for o in data]


# ---------------------------------------------------------------------------
# Human-readable summary (CLI + smoke test)
# ---------------------------------------------------------------------------


def format_outcome(outcome: RecommendationOutcome) -> str:
    rec = outcome.recommendation
    result = outcome.reconciliation
    lines = [
        f"  recommendation : {rec.id}  ({rec.report_date})",
        f"  finding        : {rec.finding}",
        f"  follow-up       : {rec.recommended_modality} in {rec.recommended_timeframe}"
        f"  [urgency: {rec.urgency_tier}]",
        f"  overdue (date)  : {outcome.overdue}",
        f"  candidates      : {len(outcome.candidates)}",
    ]
    if result is None:
        lines.append("  reconciliation  : <none>")
        return "\n".join(lines)
    lines.append(f"  CLOSURE STATE   : {result.closure_state.value.upper()}")
    for assessment in result.candidate_assessments:
        lines.append(f"    - {assessment.study_id}: {assessment.verdict.value} "
                     f"(confidence: {assessment.confidence.value})")
        for axis_name in (
            "modality_adequacy", "anatomic_coverage", "finding_acknowledgment",
            "temporal_adequacy", "terminal_event",
        ):
            axis = getattr(assessment.axes, axis_name)
            lines.append(f"        {axis_name:22s}: {axis.result.value}  — {axis.reason}")
            for ev in axis.evidence:
                lines.append(f"            “{ev.quote}”  [{ev.source_id}]")
        lines.append(f"        rationale: {assessment.rationale}")
    if result.escalation.required:
        lines.append(f"  ESCALATION      : {result.escalation.question}")
    if outcome.action is not None:
        lines.append(f"  DRAFT ({outcome.action.type.value}): {outcome.action.draft_text}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_case(case: HeroCase, outcomes: list[RecommendationOutcome]) -> None:
    print(f"\n=== {case.case_id}: {case.title} ===")
    print(f"    patient: {case.patient_name} ({case.patient_id})  as_of: {case.as_of_date}")
    if case.expected_closure_state is not None:
        print(f"    expected closure_state: {case.expected_closure_state.value}")
    for outcome in outcomes:
        print(format_outcome(outcome))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safety Net backlog sweep.")
    parser.add_argument("--case", help="Run a single hero case by case_id (e.g. case_a).")
    parser.add_argument("--use-cache", action="store_true",
                        help="Use cached hero responses if present (offline demo fallback).")
    parser.add_argument("--write-cache", action="store_true",
                        help="Write the hero responses to data/cache/ for offline reuse.")
    parser.add_argument("--no-draft", action="store_true",
                        help="Skip action-drafting (faster; escalate cases won't get a draft).")
    parser.add_argument("--full", action="store_true",
                        help="Also report the whole-backlog aggregate (2-second bookend).")
    args = parser.parse_args(argv)

    draft = not args.no_draft

    if not args.use_cache and not has_api_key():
        print(
            "ANTHROPIC_API_KEY is not set. Either add a key to .env, or run with "
            "--use-cache once data/cache/ has been populated from a good run.",
            file=sys.stderr,
        )
        return 2

    try:
        cases = load_hero_cases()
        if args.case:
            cases = [c for c in cases if c.case_id == args.case]
            if not cases:
                print(f"No hero case with case_id={args.case!r}.", file=sys.stderr)
                return 2

        for case in cases:
            outcomes = run_hero_case(
                case, draft=draft, use_cache=args.use_cache, write_cache=args.write_cache,
            )
            _print_case(case, outcomes)

        if args.full:
            reports = backlog_reports()
            hero_patient_ids = {c.patient_id for c in load_hero_cases()}
            result = run_sweep(
                reports, default_as_of_date(),
                reconcile_patient_ids=hero_patient_ids, draft=False,
            )
            print(
                f"\n--- Aggregate bookend --- swept {result.report_count} reports "
                f"-> {result.recommendation_count} follow-up recommendation(s)."
            )
    except MissingAPIKeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
