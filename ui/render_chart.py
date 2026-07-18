#!/usr/bin/env python3
"""Whole-Chart Review UI — reasoning-first, not a dashboard.

Renders a single self-contained ``ui/whole_chart.html`` (no server, no network,
system fonts) from the whole-chart review result. Reuses the Safety Net UI
shell: the whitespace/smart-quote-tolerant ``highlight()`` "money shot" and the
human-approve -> audit step (``approve_action`` + ``AuditEvent``).

Layout (per the UI brief + iteration doc §3): a 2-second summary bookend, then
the ranked findings — each expands to the connection (reasoning), the evidence
timeline (verbatim excerpts highlighted in their source notes; the absence made
legible on the discharge documents), and the escalation question (the hero
element). H4's drafted action is approvable live. The correctly-suppressed
look-alike sits in a calm, collapsed "cleared" section — the noise-discipline
proof. Safety Net's own UI (ui/render.py) is untouched.
"""

from __future__ import annotations

import html
import importlib.util
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from safety_net.actions import approve_action  # noqa: E402
from safety_net.chart_review import load_chart, run_review  # noqa: E402
from safety_net.models import (  # noqa: E402
    ActionDraft,
    ActionType,
    ChartBundle,
    ChartReviewResult,
    Finding,
)

_OUT = _ROOT / "ui" / "whole_chart.html"


def _load_highlight():
    """Reuse the Safety Net UI's evidence-highlight function (the money shot)."""
    spec = importlib.util.spec_from_file_location("sn_ui_render", _ROOT / "ui" / "render.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.highlight


highlight = _load_highlight()


def _esc(s: str) -> str:
    return html.escape(s)


# ---------------------------------------------------------------------------
# Badges (semantic set; every state carries a text label, never color alone)
# ---------------------------------------------------------------------------

_ESCALATE_STATUSES = {"UNCONFIRMED", "CONTRADICTED", "PENDING_AT_DISCHARGE"}


def _risk_badge(risk: str) -> str:
    return f'<span class="badge risk-{_esc(risk)}">{_esc(risk)} risk</span>'


def _status_badge(status: str) -> str:
    cls = "status-escalate" if status in _ESCALATE_STATUSES else "status-cleared"
    label = status.replace("_", " ")
    return f'<span class="badge {cls}">{_esc(label)}</span>'


# ---------------------------------------------------------------------------
# Evidence timeline
# ---------------------------------------------------------------------------


def _render_timeline(finding: Finding, bundle: ChartBundle) -> str:
    rows = []
    for ev in finding.timeline:
        note = bundle.note_by_id(ev.source_note_id)
        meta = (
            f'<div class="ev-meta"><span class="ev-day">Day {ev.day}</span>'
            f'<span class="ev-type">{_esc(ev.note_type)}</span>'
            f'<span class="ev-src">[{_esc(ev.source_note_id)}]</span></div>'
        )
        if ev.evidence_kind.value == "presence":
            # Full source note with the cited quote highlighted in place.
            body = note.body if note else ev.excerpt
            block = (
                '<div class="ev ev-presence">'
                '<div class="ev-tag tag-quote">QUOTE — verbatim from the source note</div>'
                f"{meta}"
                f'<pre class="evidence">{highlight(body, [ev.excerpt])}</pre></div>'
            )
        else:
            # absence_context: the section that SHOULD carry the thread — no highlight.
            block = (
                '<div class="ev ev-absence">'
                '<div class="ev-tag tag-gap">GAP — the thread is absent from this section</div>'
                f"{meta}"
                f'<pre class="evidence">{_esc(ev.excerpt)}</pre></div>'
            )
        rows.append(block)
    return "".join(rows)


def _render_action(finding: Finding) -> str:
    sa = finding.suggested_action
    if sa is None:
        return ""
    # Reuse the Safety Net approve -> audit path for the live human gate.
    draft = ActionDraft(
        action_id=f"{finding.finding_id}-action",
        rec_id=finding.thread_id,
        type=ActionType.PROVIDER_MESSAGE,
        draft_text=sa.draft_text,
    )
    _, audit = approve_action(draft, approver="Dr. Reviewer (demo)")
    return (
        '<div class="action">'
        f'<div class="action-label">Drafted {_esc(sa.kind)} &middot; human-gated (nothing sends itself)</div>'
        f'<div class="action-text">{_esc(sa.draft_text)}</div>'
        '<button onclick="this.nextElementSibling.style.display=\'block\';this.disabled=true">'
        "Approve</button>"
        f'<div class="audit" style="display:none">Approved &middot; {_esc(audit.actor)} '
        f"&middot; {_esc(audit.ts)} &middot; logged to audit trail</div></div>"
    )


def _render_finding(finding: Finding, bundle: ChartBundle, *, open_: bool, cleared: bool) -> str:
    open_attr = " open" if open_ else ""
    q_block = ""
    if finding.question:
        q_block = (
            '<div class="question"><div class="question-label">Needs a human answer</div>'
            f'<div class="question-text">{_esc(finding.question)}</div></div>'
        )
    cleared_note = ""
    if cleared and finding.cleared_reason:
        cleared_note = f'<div class="cleared-reason">{_esc(finding.cleared_reason)}</div>'
    return (
        f'<details class="finding{" finding-cleared" if cleared else ""}"{open_attr}>'
        f'<summary><span class="f-badges">{_risk_badge(finding.risk.value)}'
        f"{_status_badge(finding.status.value)}</span>"
        f'<span class="f-title">{_esc(finding.title)}</span>'
        f'<span class="f-conf">confidence {finding.confidence:.2f}</span></summary>'
        f'<div class="f-body">{cleared_note}'
        f'<div class="connection-label">The connection — why a single-pass discharge review misses this</div>'
        f'<div class="connection">{_esc(finding.connection)}</div>'
        f'<div class="timeline-label">The thread, across the stay</div>'
        f"{_render_timeline(finding, bundle)}"
        f"{q_block}"
        f"{_render_action(finding) if not cleared else ''}"
        "</div></details>"
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

_CSS = """
:root { color-scheme: dark; --bg:#0f1115; --panel:#161922; --panel2:#12161f;
  --line:#262a33; --ink:#e7e9ee; --dim:#98a0ad; --mono:ui-monospace,SFMono-Regular,Menlo,monospace;
  --accent:#5b9dff; --amber:#ffcf6b; --red:#ff8fa3; --green:#6ee7a8; }
* { box-sizing:border-box; }
body { font:16px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
  margin:0; padding:0 0 5rem; background:var(--bg); color:var(--ink); }
header { padding:1.6rem 2rem 1.2rem; border-bottom:1px solid var(--line); }
h1 { margin:0; font-size:1.5rem; letter-spacing:.2px; }
.tagline { color:var(--dim); margin-top:.35rem; max-width:70ch; }
.bookend { margin:1.4rem 2rem 0; font-size:1.05rem; }
.bookend .n { color:var(--accent); font-weight:700; }
.bookend .sub { color:var(--dim); font-size:.86rem; margin-top:.2rem; }
.wrap { max-width:920px; margin:0 auto; padding:0 1rem; }
.section-label { margin:1.6rem 2rem .4rem; text-transform:uppercase; letter-spacing:.08em;
  font-size:.74rem; color:var(--dim); }
.finding { background:var(--panel); border:1px solid var(--line); border-radius:12px;
  margin:.7rem 2rem; overflow:hidden; }
.finding[open] { border-color:#33465f; }
.finding-cleared { background:#10160f; border-color:#20351f; }
summary { list-style:none; cursor:pointer; padding:1rem 1.2rem; display:flex; flex-wrap:wrap;
  align-items:center; gap:.6rem; }
summary::-webkit-details-marker { display:none; }
.f-badges { display:flex; gap:.4rem; flex-shrink:0; }
.f-title { font-weight:600; flex:1 1 60%; min-width:16rem; }
.f-conf { color:var(--dim); font-size:.8rem; }
.badge { display:inline-block; padding:.12rem .6rem; border-radius:999px; font-size:.74rem;
  font-weight:700; border:1px solid transparent; white-space:nowrap; }
.risk-High { background:#3a1720; color:var(--red); border-color:#5e2230; }
.risk-Medium { background:#33290f; color:var(--amber); border-color:#5a4715; }
.risk-Low { background:#12351f; color:var(--green); }
.status-escalate { background:#2a1218; color:var(--red); border-color:#5e2230; }
.status-cleared { background:#12351f; color:var(--green); border-color:#1f5236; }
.f-body { padding:0 1.2rem 1.2rem; border-top:1px solid var(--line); }
.connection-label,.timeline-label { text-transform:uppercase; letter-spacing:.07em;
  font-size:.72rem; color:var(--dim); margin:1rem 0 .35rem; }
.connection { color:#d7dce4; }
.cleared-reason { margin-top:.9rem; color:var(--green); font-size:.9rem; }
.ev { margin:.5rem 0; border:1px solid var(--line); border-radius:9px; overflow:hidden; }
.ev-presence { border-left:3px solid var(--accent); }
.ev-absence { border-left:3px solid var(--amber); }
.ev-tag { font-size:.7rem; text-transform:uppercase; letter-spacing:.06em; padding:.35rem .7rem;
  background:var(--panel2); border-bottom:1px solid var(--line); }
.tag-quote { color:var(--accent); }
.tag-gap { color:var(--amber); }
.ev-meta { display:flex; gap:.7rem; padding:.4rem .7rem 0; font-size:.76rem; color:var(--dim); }
.ev-day { color:var(--ink); font-weight:600; }
.evidence { margin:.35rem 0 0; padding:.7rem; white-space:pre-wrap; font-family:var(--mono);
  font-size:.82rem; color:#cfd5df; background:#0e1219; }
mark { background:#f5d90a55; color:#fff2a8; border-radius:3px; padding:0 2px; }
.question { margin:1.1rem 0 .4rem; padding:.85rem 1rem; border:1px solid var(--red);
  border-radius:10px; background:#2a1218; }
.question-label { font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; color:var(--red); }
.question-text { font-size:1.06rem; margin-top:.3rem; }
.action { margin-top:1rem; padding:.85rem 1rem; border:1px solid var(--line); border-radius:10px;
  background:var(--panel2); }
.action-label { font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; color:var(--dim); }
.action-text { margin:.45rem 0 .7rem; white-space:pre-wrap; }
button { background:var(--accent); color:#04122b; border:0; padding:.5rem 1.1rem; border-radius:7px;
  font-size:.9rem; font-weight:600; cursor:pointer; }
button:disabled { background:#12351f; color:var(--green); cursor:default; }
.audit { margin-top:.6rem; color:var(--green); font-size:.84rem; }
footer { color:var(--dim); font-size:.82rem; margin:2rem 2rem 0; max-width:80ch; }
"""


def build_html(result: ChartReviewResult, bundle: ChartBundle) -> str:
    n = len(result.findings)
    surfaced_html = "".join(
        _render_finding(f, bundle, open_=(i == 0), cleared=False)
        for i, f in enumerate(result.findings)
    )
    cleared_html = "".join(
        _render_finding(f, bundle, open_=False, cleared=True) for f in result.cleared
    )
    cleared_section = ""
    if result.cleared:
        cleared_section = (
            f'<div class="section-label">Considered &amp; correctly cleared '
            f"({len(result.cleared)}) — the look-alikes we did NOT flag</div>{cleared_html}"
        )
    stay = bundle.patient.discharge_day - bundle.patient.admit_day + 1
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Safety Net — Whole-Chart Review</title>
<style>{_CSS}</style></head>
<body>
<header>
  <h1>Safety Net &middot; Whole-Chart Review</h1>
  <div class="tagline">No clinician reads {stay} days of chart end-to-end at discharge.
  We do — every note, every domain, every day — and we only speak up when a thread
  genuinely fell through, with the receipt.</div>
</header>
<div class="bookend"><span class="n">{n}</span> unreconciled thread{'' if n == 1 else 's'}
across a {stay}-day admission surfaced at discharge.
  <div class="sub">A 2-second bookend for scale — the reasoning on each thread is the point, not this number.</div>
</div>
<div class="section-label">Surfaced — ranked by consequence of the miss</div>
{surfaced_html}
{cleared_section}
<footer>Every claim carries a verbatim citation validated as an exact substring of a source note.
The agent reconciles documentation across the stay — it does not diagnose. Findings are hard-capped
at the top {len(result.findings) if result.findings else 4} by risk &times; confidence; the rest collapse into cleared.</footer>
</body></html>
"""


def main() -> int:
    bundle = load_chart()
    result = run_review(bundle, use_cache=True)
    _OUT.write_text(build_html(result, bundle), encoding="utf-8")
    print(f"Wrote {_OUT}")
    print(f"  surfaced: {len(result.findings)}   cleared: {len(result.cleared)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
