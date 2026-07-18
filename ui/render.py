#!/usr/bin/env python3
"""Minimal UI stub for Safety Net.

Runs the two hero cases and writes a single self-contained ``ui/index.html``
showing, for each case: the reasoning trace (five axes -> verdict), the verbatim
citation highlighted in the source report, and — for Case A — the escalation
question plus a human-approved closing action. No server, no build step, works
offline from ``data/cache/``. This is a stub, deliberately not a dashboard.
"""

from __future__ import annotations

import html
import pathlib
import re
import sys

_SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_SRC))

from safety_net.actions import approve_action  # noqa: E402
from safety_net.client import has_api_key  # noqa: E402
from safety_net.models import (  # noqa: E402
    ClosureState,
    HeroCase,
    RecommendationOutcome,
)
from safety_net.sweep import load_hero_cases, read_cache, run_hero_case  # noqa: E402

_OUT = pathlib.Path(__file__).resolve().parent / "index.html"

# ---------------------------------------------------------------------------
# Evidence highlighting — whitespace/smart-quote tolerant (the "money shot"
# breaks on exact-match, per the blueprint). Normalize, match, map back.
# ---------------------------------------------------------------------------

_TRANS = {
    ord("’"): "'", ord("‘"): "'",
    ord("“"): '"', ord("”"): '"',
    ord("–"): "-", ord("—"): "-",
}


def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    idx_map: list[int] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            start = i
            while i < n and text[i].isspace():
                i += 1
            chars.append(" ")
            idx_map.append(start)
            continue
        chars.append(_TRANS.get(ord(c), c).lower())
        idx_map.append(i)
        i += 1
    idx_map.append(n)  # sentinel for exclusive-end mapping
    return "".join(chars), idx_map


def _normalize_needle(q: str) -> str:
    return re.sub(r"\s+", " ", q.translate(_TRANS)).strip().lower()


def _find_span(norm: str, idx_map: list[int], needle: str) -> tuple[int, int] | None:
    if not needle:
        return None
    pos = norm.find(needle)
    if pos == -1:
        return None
    return idx_map[pos], idx_map[pos + len(needle)]


def _esc(s: str) -> str:
    return html.escape(s).replace("\n", "<br>\n")


def highlight(full_text: str, quotes: list[str]) -> str:
    norm, idx_map = _normalize_with_map(full_text)
    spans: list[tuple[int, int]] = []
    for q in quotes:
        span = _find_span(norm, idx_map, _normalize_needle(q))
        if span:
            spans.append(span)
    spans.sort()
    merged: list[tuple[int, int]] = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    out: list[str] = []
    cursor = 0
    for s, e in merged:
        out.append(_esc(full_text[cursor:s]))
        out.append("<mark>" + _esc(full_text[s:e]) + "</mark>")
        cursor = e
    out.append(_esc(full_text[cursor:]))
    return "".join(out)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_AXIS_ORDER = [
    ("modality_adequacy", "Modality adequacy"),
    ("anatomic_coverage", "Anatomic coverage"),
    ("finding_acknowledgment", "Finding acknowledgment"),
    ("temporal_adequacy", "Temporal adequacy"),
    ("terminal_event", "Terminal event"),
]
_GOOD = {"pass", "superior", "on_time", "present"}
_BAD = {"fail", "never"}


def _badge(result: str) -> str:
    cls = "good" if result in _GOOD else "bad" if result in _BAD else "warn"
    return f'<span class="badge {cls}">{html.escape(result)}</span>'


def _quotes_by_source(outcome: RecommendationOutcome) -> dict[str, list[str]]:
    by_src: dict[str, list[str]] = {}
    if outcome.reconciliation is None:
        return by_src
    for assessment in outcome.reconciliation.candidate_assessments:
        for axis_name, _ in _AXIS_ORDER:
            axis = getattr(assessment.axes, axis_name)
            for ev in axis.evidence:
                by_src.setdefault(ev.source_id, []).append(ev.quote)
    return by_src


def _render_report(title: str, full_text: str, quotes: list[str]) -> str:
    return (
        f'<div class="report"><div class="report-title">{html.escape(title)}</div>'
        f'<pre class="report-text">{highlight(full_text, quotes)}</pre></div>'
    )


def _render_axes(assessment) -> str:
    rows = []
    for axis_name, axis_label in _AXIS_ORDER:
        axis = getattr(assessment.axes, axis_name)
        extra = ""
        if axis_name == "terminal_event" and axis.type.value != "none":
            extra = f' <span class="ttype">({html.escape(axis.type.value)})</span>'
        cites = "".join(
            f'<div class="cite">&ldquo;{html.escape(ev.quote)}&rdquo; '
            f'<span class="src">[{html.escape(ev.source_id)}]</span></div>'
            for ev in axis.evidence
        )
        rows.append(
            f'<div class="axis"><div class="axis-head">{axis_label}: '
            f"{_badge(axis.result.value)}{extra}</div>"
            f'<div class="axis-reason">{html.escape(axis.reason)}</div>{cites}</div>'
        )
    return "".join(rows)


def _render_assessment(assessment) -> str:
    return (
        f'<div class="assessment"><div class="verdict">Verdict: '
        f'<b>{html.escape(assessment.verdict.value)}</b> '
        f'<span class="conf">confidence: {html.escape(assessment.confidence.value)}</span></div>'
        f"{_render_axes(assessment)}"
        f'<div class="rationale">{html.escape(assessment.rationale)}</div></div>'
    )


def _closure_banner(state: ClosureState) -> str:
    cls = {
        ClosureState.ESCALATE: "banner-escalate",
        ClosureState.OPEN_OVERDUE: "banner-escalate",
        ClosureState.SUPERSEDED: "banner-ok",
        ClosureState.COMPLETED: "banner-ok",
    }.get(state, "banner-neutral")
    return f'<div class="banner {cls}">Closure state: {html.escape(state.value.upper())}</div>'


def _render_case(case: HeroCase, outcomes: list[RecommendationOutcome] | None, err: str | None) -> str:
    head = (
        f'<section class="case"><h2>{html.escape(case.title)}</h2>'
        f'<div class="patient">{html.escape(case.patient_name)} '
        f"&middot; {html.escape(case.patient_id)} &middot; as of {html.escape(case.as_of_date)}</div>"
    )
    if case.note:
        head += f'<div class="note">{html.escape(case.note)}</div>'

    if err:
        return head + f'<div class="placeholder">Could not run this case: {html.escape(err)}</div></section>'
    if not outcomes:
        return head + (
            '<div class="placeholder">Not yet populated. Add an ANTHROPIC_API_KEY '
            "to <code>.env</code> and run <code>python -m safety_net.sweep "
            "--write-cache</code>, then re-render.</div></section>"
        )

    id_to_report = {r.report_id: r for r in case.reports}
    body = ""
    for outcome in outcomes:
        rec = outcome.recommendation
        result = outcome.reconciliation
        by_src = _quotes_by_source(outcome)

        body += (
            f'<div class="rec"><div class="rec-head">Follow-up recommendation '
            f"({html.escape(rec.report_date)}): {html.escape(rec.finding)}</div>"
            f'<div class="rec-sub">Recommended: {html.escape(rec.recommended_modality)} '
            f"in {html.escape(rec.recommended_timeframe)} &middot; "
            f'naive date logic: {"OVERDUE" if outcome.overdue else "not overdue"}</div>'
        )

        # Source report, with the recommendation text highlighted.
        src = id_to_report.get(rec.source_id)
        if src:
            body += _render_report(
                f"Source report {src.report_id} — {src.modality} ({src.date})",
                src.full_text,
                by_src.get(rec.source_id, []) + [rec.original_text],
            )
        # Candidate reports, with cited evidence highlighted.
        for cand in outcome.candidates:
            crep = id_to_report.get(cand.id)
            if crep:
                body += _render_report(
                    f"Later study {crep.report_id} — {crep.modality} ({crep.date})",
                    crep.full_text,
                    by_src.get(cand.id, []),
                )

        if result:
            body += "".join(_render_assessment(a) for a in result.candidate_assessments)
            body += _closure_banner(result.closure_state)
            if result.escalation.required and result.escalation.question:
                body += (
                    '<div class="escalation"><div class="escalation-label">'
                    "Escalation — needs a human answer</div>"
                    f'<div class="escalation-q">{html.escape(result.escalation.question)}</div></div>'
                )
        # Drafted action + human-approve (audit) step.
        if outcome.action:
            approved, audit = approve_action(outcome.action, approver="Dr. Reviewer (demo)")
            body += (
                f'<div class="action"><div class="action-label">Drafted '
                f"{html.escape(outcome.action.type.value)} (human-gated)</div>"
                f'<div class="action-text">{html.escape(outcome.action.draft_text)}</div>'
                f'<button onclick="this.nextElementSibling.style.display=\'block\';this.disabled=true">'
                f"Approve</button>"
                f'<div class="audit" style="display:none">Approved &middot; '
                f"{html.escape(audit.actor)} &middot; {html.escape(audit.ts)} &middot; "
                f"logged to audit trail</div></div>"
            )
        body += "</div>"
    return head + body + "</section>"


_CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font: 15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
       margin: 0; padding: 0 0 4rem; background: #0f1115; color: #e7e9ee; }
header { padding: 1.5rem 2rem; border-bottom: 1px solid #262a33; }
h1 { margin: 0; font-size: 1.4rem; }
.tagline { color: #98a0ad; margin-top: .25rem; }
.bookend { margin: 1rem 2rem 0; color: #98a0ad; font-size: .9rem; }
.case { margin: 1.5rem 2rem; padding: 1.25rem 1.5rem; background: #161922;
        border: 1px solid #262a33; border-radius: 12px; max-width: 900px; }
h2 { margin: 0 0 .25rem; font-size: 1.15rem; }
.patient { color: #98a0ad; font-size: .9rem; }
.note { color: #c3c9d4; font-style: italic; margin: .5rem 0 1rem; }
.rec { margin-top: 1rem; }
.rec-head { font-weight: 600; }
.rec-sub { color: #98a0ad; font-size: .85rem; margin-bottom: .75rem; }
.report { background: #0f131b; border: 1px solid #222735; border-radius: 8px;
          margin: .5rem 0; overflow: hidden; }
.report-title { padding: .4rem .75rem; background: #1b2130; font-size: .8rem;
                color: #9aa4b4; border-bottom: 1px solid #222735; }
.report-text { margin: 0; padding: .75rem; white-space: pre-wrap; font-size: .82rem;
               font-family: ui-monospace,SFMono-Regular,Menlo,monospace; color: #cfd5df; }
mark { background: #f5d90a55; color: #fff2a8; border-radius: 3px; padding: 0 2px; }
.assessment { margin: .75rem 0; padding: .75rem 1rem; background: #12161f;
              border: 1px solid #222735; border-radius: 8px; }
.verdict { font-size: 1rem; margin-bottom: .5rem; }
.conf { color: #98a0ad; font-size: .8rem; }
.axis { margin: .4rem 0; }
.axis-head { font-weight: 600; font-size: .9rem; }
.axis-reason { color: #c3c9d4; font-size: .85rem; }
.cite { color: #9fd0ff; font-size: .82rem; margin: .15rem 0 .15rem .5rem; }
.src { color: #6b7280; }
.ttype { color: #98a0ad; font-size: .8rem; }
.rationale { margin-top: .5rem; color: #e7e9ee; font-style: italic; }
.badge { display: inline-block; padding: .05rem .5rem; border-radius: 999px;
         font-size: .78rem; font-weight: 600; }
.badge.good { background: #12351f; color: #6ee7a8; }
.badge.bad  { background: #3a1720; color: #ff8fa3; }
.badge.warn { background: #33290f; color: #ffcf6b; }
.banner { margin: .75rem 0; padding: .5rem .9rem; border-radius: 8px; font-weight: 700; }
.banner-escalate { background: #3a1720; color: #ff8fa3; }
.banner-ok { background: #12351f; color: #6ee7a8; }
.banner-neutral { background: #1b2130; color: #c3c9d4; }
.escalation { margin: .75rem 0; padding: .75rem 1rem; border: 1px solid #ff8fa3;
              border-radius: 8px; background: #2a1218; }
.escalation-label { font-size: .78rem; text-transform: uppercase; color: #ff8fa3; }
.escalation-q { font-size: 1rem; margin-top: .25rem; }
.action { margin: .75rem 0; padding: .75rem 1rem; border: 1px solid #262a33;
          border-radius: 8px; background: #12161f; }
.action-label { font-size: .78rem; text-transform: uppercase; color: #9aa4b4; }
.action-text { margin: .4rem 0 .6rem; white-space: pre-wrap; }
button { background: #2563eb; color: #fff; border: 0; padding: .4rem .9rem;
         border-radius: 6px; font-size: .85rem; cursor: pointer; }
button:disabled { background: #12351f; color: #6ee7a8; cursor: default; }
.audit { margin-top: .5rem; color: #6ee7a8; font-size: .82rem; }
.placeholder { padding: 1rem; color: #ffcf6b; }
code { background: #1b2130; padding: .1rem .3rem; border-radius: 4px; }
"""


def build_html(cases_with_outcomes: list[tuple[HeroCase, list[RecommendationOutcome] | None, str | None]],
               report_count: int) -> str:
    sections = "".join(_render_case(c, o, e) for c, o, e in cases_with_outcomes)
    reconciled = sum(len(o or []) for _, o, _ in cases_with_outcomes)
    bookend = (
        f"Swept {report_count} finished reports &middot; {reconciled} hero "
        "recommendation(s) reconciled live. (Aggregate is a bookend, not the point.)"
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Safety Net — reconciliation</title>
<style>{_CSS}</style></head>
<body>
<header>
  <h1>Safety Net</h1>
  <div class="tagline">Was the finding actually addressed — not just whether a study happened.</div>
</header>
<div class="bookend">{bookend}</div>
{sections}
</body></html>
"""


def main() -> int:
    from safety_net.sweep import backlog_reports

    cases = load_hero_cases()
    rows: list[tuple[HeroCase, list[RecommendationOutcome] | None, str | None]] = []
    use_cache = not has_api_key()
    for case in cases:
        outcomes: list[RecommendationOutcome] | None = None
        err: str | None = None
        can_run = has_api_key() or read_cache(case.case_id) is not None
        if can_run:
            try:
                outcomes = run_hero_case(case, draft=True, use_cache=use_cache)
            except Exception as exc:  # noqa: BLE001
                err = str(exc)
        rows.append((case, outcomes, err))

    try:
        report_count = len(backlog_reports())
    except Exception:  # noqa: BLE001
        report_count = 0

    _OUT.write_text(build_html(rows, report_count), encoding="utf-8")
    print(f"Wrote {_OUT}")
    if use_cache:
        print("(rendered from cache / placeholder — no API key set)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
