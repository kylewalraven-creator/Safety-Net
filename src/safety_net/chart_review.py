"""Whole-chart review — deterministic, code-orchestrated pipeline.

The whole-chart analogue of ``sweep.py``. Loads a ``ChartBundle`` and runs:

    extract signals (Haiku)  ->  thread by entity (code)  ->  reconcile each
    thread (Opus)  ->  validate citations + rank + surface (code)

Reasoning steps (extraction, reconciliation) are the agentic core; threading,
grounding, ranking and the TOP_N cap are pure code, which is what makes the
on-stage output reliable. Like Safety Net, it runs offline from a committed
cache (``data/chart/cache/``) when no key is present, so the demo and the eval
harness are deterministic. For the stage, ``live_entities`` reconciles just the
two live heroes against the API and loads the rest from cache.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import time
from pathlib import Path

from .client import MODEL_HAIKU, MODEL_OPUS, MissingAPIKeyError, has_api_key
from .extract import extract_chart, extract_signals
from .grounding import apply_surfacing
from .models import (
    ChartBundle,
    ChartReviewResult,
    CitationValidation,
    ExtractedSignal,
    Finding,
    GroundTruth,
    LatencyMs,
    RunMeta,
    Thread,
)
from .reconcile import reconcile_thread
from .timeline import build_threads


def _default_data_dir() -> Path:
    env = os.environ.get("SAFETY_NET_DATA_DIR")
    return Path(env) if env else Path(__file__).resolve().parents[2] / "data"


DATA_DIR = _default_data_dir()
CHART_DIR = DATA_DIR / "chart"
CACHE_DIR = CHART_DIR / "cache"
CHART_PATH = CHART_DIR / "chart.json"
MANIFEST_PATH = CHART_DIR / "manifest.json"
SIGNALS_CACHE = CACHE_DIR / "signals.json"
FINDINGS_CACHE = CACHE_DIR / "findings.json"

# The two live heroes reconciled live on stage; the rest precomputed.
LIVE_HERO_ENTITIES = {"apixaban", "colonoscopy_followup"}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_chart(path: Path = CHART_PATH) -> ChartBundle:
    return ChartBundle.model_validate_json(path.read_text(encoding="utf-8"))


def load_ground_truth(path: Path = MANIFEST_PATH) -> GroundTruth:
    return GroundTruth.model_validate_json(path.read_text(encoding="utf-8"))


def _load_cached_signals() -> list[ExtractedSignal] | None:
    if not SIGNALS_CACHE.exists():
        return None
    data = json.loads(SIGNALS_CACHE.read_text(encoding="utf-8"))
    return [ExtractedSignal.model_validate(d) for d in data]


def _load_cached_findings() -> dict[str, Finding] | None:
    if not FINDINGS_CACHE.exists():
        return None
    data = json.loads(FINDINGS_CACHE.read_text(encoding="utf-8"))
    findings = [Finding.model_validate(d) for d in data]
    return {f.thread_id: f for f in findings}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _get_signals(bundle: ChartBundle, *, use_cache: bool) -> tuple[list[ExtractedSignal], bool]:
    """Return (signals, live). Uses the cache when asked/available; otherwise
    extracts live via Haiku (requires a key)."""
    if use_cache:
        cached = _load_cached_signals()
        if cached is not None:
            return cached, False
    return extract_chart(bundle), True


def _reconcile_threads(
    threads: list[Thread],
    signals_by_id: dict[str, ExtractedSignal],
    bundle: ChartBundle,
    *,
    use_cache: bool,
    live_entities: set[str] | None,
) -> tuple[list[Finding], bool]:
    """Return (findings, any_live). If ``live_entities`` is given, only those
    entities are reconciled live and the rest are loaded from cache (the stage
    behavior); otherwise cache-all or live-all per ``use_cache``."""
    cached = _load_cached_findings() if use_cache else None
    findings: list[Finding] = []
    any_live = False
    for thread in threads:
        do_live = (
            (live_entities is not None and thread.entity in live_entities)
            or (cached is None)
            or (cached.get(thread.thread_id) is None)
        )
        if do_live:
            findings.append(reconcile_thread(thread, signals_by_id, bundle))
            any_live = True
        else:
            findings.append(cached[thread.thread_id])
    return findings, any_live


def run_review(
    bundle: ChartBundle,
    *,
    use_cache: bool = False,
    live_entities: set[str] | None = None,
    ground_truth: GroundTruth | None = None,
) -> ChartReviewResult:
    """Run the whole-chart pipeline end to end and return a ChartReviewResult.

    ``ground_truth`` is accepted for signature symmetry; scoring lives in the
    eval harness, which reads the returned result.
    """
    started = _dt.datetime.now(_dt.timezone.utc)

    t0 = time.perf_counter()
    signals, sig_live = _get_signals(bundle, use_cache=use_cache)
    threads = build_threads(signals, bundle)
    signals_by_id = {s.signal_id: s for s in signals}
    t_index = int((time.perf_counter() - t0) * 1000)

    t1 = time.perf_counter()
    findings, rec_live = _reconcile_threads(
        threads, signals_by_id, bundle, use_cache=use_cache, live_entities=live_entities
    )
    t_reason = int((time.perf_counter() - t1) * 1000)

    surf = apply_surfacing(findings, bundle)

    stay_len = bundle.patient.discharge_day - bundle.patient.admit_day + 1
    n = len(surf.surfaced)
    summary_line = (
        f"{n} unreconciled thread{'' if n == 1 else 's'} across a {stay_len}-day stay"
    )

    checked, passed, failed = surf.citation_counts
    run_meta = RunMeta(
        model_reasoning=MODEL_OPUS,
        model_extraction=MODEL_HAIKU,
        chart_id=bundle.chart_id,
        context_tokens=sum(len(n.body) for n in bundle.notes) // 4,  # rough estimate
        latency_ms=LatencyMs(index=t_index, reason=t_reason, draft=0),
        citation_validation=CitationValidation(checked=checked, passed=passed, failed=failed),
        started_at=started.isoformat(timespec="seconds"),
        live=sig_live or rec_live,
    )

    return ChartReviewResult(
        chart_id=bundle.chart_id,
        summary_line=summary_line,
        findings=surf.surfaced,
        cleared=surf.cleared,
        run_meta=run_meta,
    )


# ---------------------------------------------------------------------------
# Cache writing (capture a good live run for offline determinism)
# ---------------------------------------------------------------------------


def write_cache(bundle: ChartBundle) -> tuple[Path, Path]:
    """Run extraction + reconciliation LIVE and cache the raw signals + findings
    (pre-surfacing) so later offline runs reproduce them deterministically."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    signals = extract_chart(bundle)
    threads = build_threads(signals, bundle)
    signals_by_id = {s.signal_id: s for s in signals}
    findings = [reconcile_thread(t, signals_by_id, bundle) for t in threads]
    SIGNALS_CACHE.write_text(
        json.dumps([s.model_dump(mode="json") for s in signals], indent=2), encoding="utf-8"
    )
    FINDINGS_CACHE.write_text(
        json.dumps([f.model_dump(mode="json") for f in findings], indent=2), encoding="utf-8"
    )
    return SIGNALS_CACHE, FINDINGS_CACHE


# ---------------------------------------------------------------------------
# Human-readable rendering (CLI)
# ---------------------------------------------------------------------------


def format_result(result: ChartReviewResult) -> str:
    lines = [
        f"\n=== Whole-chart review: {result.chart_id} ===",
        f"SUMMARY: {result.summary_line}",
    ]
    if result.run_meta:
        rm = result.run_meta
        cv = rm.citation_validation
        lines.append(
            f"  [run] live={rm.live}  citations {cv.passed}/{cv.checked} valid  "
            f"latency index={rm.latency_ms.index}ms reason={rm.latency_ms.reason}ms"
        )
    lines.append(f"\n-- SURFACED ({len(result.findings)}) --")
    for f in result.findings:
        lines.append(f"  [{f.risk.value}/{f.status.value}] {f.title}  (conf {f.confidence:.2f})")
        lines.append(f"      Q: {f.question}")
        for ev in f.timeline:
            tag = "quote" if ev.evidence_kind.value == "presence" else "gap  "
            lines.append(f"        d{ev.day} {tag} [{ev.source_note_id}] {ev.excerpt[:80]!r}")
        if f.suggested_action:
            lines.append(f"      ACTION({f.suggested_action.kind}): {f.suggested_action.draft_text[:100]}...")
    lines.append(f"\n-- CLEARED ({len(result.cleared)}) --")
    for f in result.cleared:
        lines.append(f"  [{f.status.value}] {f.title}")
        lines.append(f"      reason: {f.cleared_reason}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safety Net whole-chart review.")
    parser.add_argument("--use-cache", action="store_true",
                        help="Use committed cache (offline; deterministic demo path).")
    parser.add_argument("--write-cache", action="store_true",
                        help="Run live and write signals+findings to data/chart/cache/.")
    parser.add_argument("--live-heroes", action="store_true",
                        help="Reconcile the two live heroes live, load the rest from cache "
                             "(the on-stage behavior; needs a key).")
    parser.add_argument("--json", action="store_true", help="Print the ChartReviewResult as JSON.")
    args = parser.parse_args(argv)

    key = has_api_key()
    if (args.write_cache or args.live_heroes) and not key:
        print(
            "ANTHROPIC_API_KEY is not set. Add it to .env for a live run "
            "(--write-cache / --live-heroes), or use --use-cache to run offline "
            "from the committed cache.",
            file=sys.stderr,
        )
        return 2

    try:
        bundle = load_chart()
        if args.write_cache:
            sp, fp = write_cache(bundle)  # the single live extract+reconcile pass
            print(f"Wrote cache: {sp.name}, {fp.name}")

        live_entities = LIVE_HERO_ENTITIES if args.live_heroes else None
        # After --write-cache, display from the just-written cache (one live pass,
        # not two). --live-heroes reconciles the two heroes live and loads the rest
        # from cache. With no key and no flags, fall back to the committed cache.
        use_cache = args.use_cache or args.write_cache or args.live_heroes or (not key)
        result = run_review(bundle, use_cache=use_cache, live_entities=live_entities)

        if args.json:
            print(json.dumps(result.model_dump(mode="json"), indent=2))
        else:
            print(format_result(result))
    except MissingAPIKeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
