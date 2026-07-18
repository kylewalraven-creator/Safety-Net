#!/usr/bin/env python3
"""Whole-Chart Review UI — "1a Ward" redesign (Claude Design UI overhaul).

Renders a single self-contained ``ui/whole_chart.html`` (no server, no network,
system-font fallback) from the whole-chart review result. Reasoning-first, not a
dashboard: a master-detail worklist, an evidence timeline of verbatim quote-cards
(teal nodes for presence, a rose GAP card for the absence), a creatinine
sparkline, the escalation question as the highest-contrast panel, a human-gated
Approve -> audit line, and a validation footer.

Visual system per docs/ui-design-brief.md + the Claude Design proposal: dark
"1a Ward" tokens, IBM Plex (named first, robust system fallback so it renders
offline), semantic colors that always pair with a text label + glyph, and motion
gated behind prefers-reduced-motion. Content (findings, ordering, citations,
questions, actions) is unchanged — the nodule leads, per clinical review.

Safety Net's own UI (ui/render.py) is untouched.
"""

from __future__ import annotations

import html
import pathlib
import re
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from safety_net.actions import approve_action  # noqa: E402
from safety_net.chart_review import load_chart, load_ground_truth, run_review  # noqa: E402
from safety_net.eval_harness import score, validate_all_citations  # noqa: E402
from safety_net.models import (  # noqa: E402
    ActionDraft,
    ActionType,
    ChartBundle,
    ChartReviewResult,
    EvidenceKind,
    Finding,
)

_OUT = _ROOT / "ui" / "whole_chart.html"

# Short, factual domain labels for the worklist subline (not clinical claims).
_DOMAIN = {
    "pulmonary_nodule_lll": "imaging",
    "apixaban": "anticoagulation",
    "blood_culture_d11": "microbiology",
    "creatinine_series": "renal trend",
    "colonoscopy_followup": "GI follow-up",
}


def _esc(s: str) -> str:
    return html.escape(s or "")


def _domain(f: Finding) -> str:
    entity = f.thread_id[2:] if f.thread_id.startswith("t_") else f.thread_id
    return _DOMAIN.get(entity, entity.replace("_", " "))


def _risk_class(risk: str) -> str:
    return {"High": "risk-high", "Medium": "risk-med", "Low": "risk-low"}.get(risk, "risk-med")


# ---------------------------------------------------------------------------
# Worklist (left, sticky)
# ---------------------------------------------------------------------------


def _worklist_row(f: Finding, rank: int, active: bool) -> str:
    n = len(f.timeline)
    return (
        f'<button class="wl-row{" active" if active else ""}" data-row="{_esc(f.thread_id)}" '
        f'onclick="sel(\'{_esc(f.thread_id)}\')">'
        f'<div class="wl-badges">'
        f'<span class="pill {_risk_class(f.risk.value)}">{_esc(f.risk.value.upper())}</span>'
        f'<span class="pill pill-status">{_esc(f.status.value.replace("_"," "))}</span>'
        f'<span class="wl-rank">{rank:02d}</span></div>'
        f'<div class="wl-title">{_esc(f.title)}</div>'
        f'<div class="wl-sub">{_esc(_domain(f))} · {n} citation{"" if n==1 else "s"}</div>'
        f"</button>"
    )


def _worklist_cleared_row(f: Finding, active: bool) -> str:
    return (
        f'<button class="wl-row wl-cleared{" active" if active else ""}" data-row="{_esc(f.thread_id)}" '
        f'onclick="sel(\'{_esc(f.thread_id)}\')">'
        f'<div class="wl-badges"><span class="pill pill-cleared">✓ CLEARED</span>'
        f'<span class="wl-rank">—</span></div>'
        f'<div class="wl-title">{_esc(f.title)}</div>'
        f'<div class="wl-sub">suppressed · same plan, other words</div>'
        f"</button>"
    )


# ---------------------------------------------------------------------------
# Evidence timeline
# ---------------------------------------------------------------------------

_NOTE_LABELS = {
    "med_reconciliation": "MED REC", "progress_note": "PROGRESS", "radiology_report": "RADIOLOGY",
    "lab_result": "LAB", "micro_result": "MICROBIOLOGY", "consult_note": "CONSULT",
    "discharge_summary": "DISCHARGE", "discharge_addendum": "ADDENDUM", "pcp_letter": "PCP LETTER",
    "procedure_note": "PROCEDURE", "nursing_note": "NURSING", "med_admin": "MED ADMIN",
}


def _note_label(note_type: str) -> str:
    return _NOTE_LABELS.get(note_type, note_type.replace("_", " ").upper())


def _evidence_row(ev, *, last: bool, closure: bool) -> str:
    presence = ev.evidence_kind is EvidenceKind.PRESENCE
    src = _esc(ev.source_note_id)
    label = _note_label(ev.note_type)
    if presence:
        tag_right = "MATCH — SAME PLAN" if closure else "verbatim"
        head_right_cls = "ev-match" if closure else "ev-head-dim"
        node_cls = "node-teal"
        card_cls = "ev-card"
        head = (
            f'<div class="ev-head"><span>{_esc(label)} · {src}</span>'
            f'<span class="{head_right_cls}">{_esc(tag_right)}</span></div>'
        )
        quote = f'<div class="ev-quote">&ldquo;{_esc(ev.excerpt)}&rdquo;</div>'
    else:
        node_cls = "node-rose"
        card_cls = "ev-card ev-gap"
        head = (
            f'<div class="ev-head ev-head-gap"><span>{_esc(label)} · {src}</span>'
            f'<span class="ev-gaptag">GAP — DROPPED</span></div>'
        )
        quote = f'<div class="ev-quote">&ldquo;{_esc(ev.excerpt)}&rdquo;</div>'
    day_cls = "ev-day ev-day-gap" if not presence else "ev-day"
    return (
        f'<div class="ev-row{" ev-last" if last else ""}">'
        f'<div class="{day_cls}">Day {ev.day}</div>'
        f'<div class="ev-node"><span class="ev-dot {node_cls}"></span></div>'
        f'<div class="{card_cls}">{head}{quote}</div></div>'
    )


def _timeline(f: Finding) -> str:
    # The closure citation (equivalence match) is the PCP letter for a suppress.
    rows = []
    n = len(f.timeline)
    for i, ev in enumerate(f.timeline):
        closure = (
            f.status.value == "CONFIRMED_ADDRESSED"
            and ev.evidence_kind is EvidenceKind.PRESENCE
            and ev.source_note_id == "n_pcp_d14"
        )
        rows.append(_evidence_row(ev, last=(i == n - 1), closure=closure))
    return f'<div class="ev-label">Evidence timeline · verbatim citations</div><div class="timeline">{"".join(rows)}</div>'


# ---------------------------------------------------------------------------
# Creatinine sparkline (rendered when the finding cites a mg/dL series)
# ---------------------------------------------------------------------------

_MGDL = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*mg/dL")


def _series_points(f: Finding) -> list[tuple[int, float]]:
    pts = []
    for ev in f.timeline:
        if ev.evidence_kind is EvidenceKind.PRESENCE:
            m = _MGDL.search(ev.excerpt)
            if m:
                pts.append((ev.day, float(m.group(1))))
    return pts


def _sparkline(pts: list[tuple[int, float]]) -> str:
    if len(pts) < 2:
        return ""
    days = [d for d, _ in pts]
    vals = [v for _, v in pts]
    dmin, dmax = min(days), max(days)
    vmin, vmax = min(vals), max(vals)
    span_d = (dmax - dmin) or 1
    span_v = (vmax - vmin) or 1
    peak_v = max(vals)
    peak_day = days[vals.index(peak_v)]

    def X(d):
        return 20 + (d - dmin) / span_d * 520

    def Y(v):
        return 74 - (v - vmin) / span_v * 54

    poly = " ".join(f"{X(d):.0f},{Y(v):.0f}" for d, v in pts)
    dots = "".join(
        f'<circle cx="{X(d):.0f}" cy="{Y(v):.0f}" r="{4.5 if v==peak_v else 3}" '
        f'fill="{"#fcd77f" if v==peak_v else "#35d6c3"}"></circle>'
        for d, v in pts
    )
    halo = f'<circle cx="{X(peak_day):.0f}" cy="{Y(peak_v):.0f}" r="9" fill="none" stroke="rgba(251,191,36,.35)"></circle>'
    return (
        '<div class="spark">'
        f'<div class="spark-head"><span>Creatinine · mg/dL</span>'
        f'<span class="spark-peak">peak {peak_v:g} · Day {peak_day}</span></div>'
        '<svg viewBox="0 0 560 100" preserveAspectRatio="none">'
        f'<line x1="20" y1="{Y(vmin):.0f}" x2="540" y2="{Y(vmin):.0f}" stroke="#2a3340" stroke-width="1" stroke-dasharray="3 5"></line>'
        f'<text x="20" y="{Y(vmin)-5:.0f}" fill="#5f6b7a" font-size="9" font-family="var(--mono)">baseline {vmin:g}</text>'
        f'<polyline points="{poly}" fill="none" stroke="#fcd77f" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"></polyline>'
        f"{halo}{dots}</svg></div>"
    )


# ---------------------------------------------------------------------------
# Action (human-gated) — first finding is live-approvable; rest are queued
# ---------------------------------------------------------------------------


def _action(f: Finding, *, live: bool) -> str:
    sa = f.suggested_action
    if sa is None:
        return ""
    if not live:
        return (
            '<div class="action">'
            f'<div class="act-label">Drafted {_esc(sa.kind)} · human-gated</div>'
            f'<div class="act-text">{_esc(sa.draft_text)}</div>'
            '<div class="queued">◷ Queued for review</div></div>'
        )
    draft = ActionDraft(
        action_id=f"{f.finding_id}-action", rec_id=f.thread_id,
        type=ActionType.PROVIDER_MESSAGE, draft_text=sa.draft_text,
    )
    _, audit = approve_action(draft, approver="Dr. Reviewer (demo)")
    return (
        '<div class="action">'
        f'<div class="act-label">Drafted {_esc(sa.kind)} · human-gated (nothing sends itself)</div>'
        f'<div class="act-text">{_esc(sa.draft_text)}</div>'
        '<button class="btn" onclick="approve(this)">Approve &amp; send</button>'
        f'<div class="audit">✓ Approved · {_esc(audit.actor)} · {_esc(audit.ts)} · logged to audit trail</div>'
        "</div>"
    )


# ---------------------------------------------------------------------------
# Detail panels
# ---------------------------------------------------------------------------


def _detail_surfaced(f: Finding, rank: int, total: int, *, shown: bool, live: bool) -> str:
    spark = _sparkline(_series_points(f)) if f.thread_id == "t_creatinine_series" else ""
    return (
        f'<section class="detail" data-detail="{_esc(f.thread_id)}" '
        f'style="display:{"block" if shown else "none"}">'
        f'<div class="d-head"><div class="d-pills">'
        f'<span class="pill {_risk_class(f.risk.value)}">● {_esc(f.risk.value.upper())}</span>'
        f'<span class="pill pill-status">{_esc(f.status.value.replace("_"," "))}</span></div>'
        f'<span class="d-rank">{rank:02d} / {total:02d}</span></div>'
        f'<h2 class="d-title">{_esc(f.title)}</h2>'
        f'<p class="d-reason">{_esc(f.connection)}</p>'
        f"{spark}"
        f"{_timeline(f)}"
        f'<div class="escalation" role="status">'
        f'<div class="esc-label">Needs a human answer</div>'
        f'<div class="esc-q">{_esc(f.question)}</div></div>'
        f"{_action(f, live=live)}"
        "</section>"
    )


def _detail_cleared(f: Finding, *, shown: bool) -> str:
    return (
        f'<section class="detail" data-detail="{_esc(f.thread_id)}" '
        f'style="display:{"block" if shown else "none"}">'
        f'<div class="d-head"><div class="d-pills">'
        f'<span class="pill pill-cleared">✓ CONFIRMED ADDRESSED</span>'
        f'<span class="d-clabel">CLEARED</span></div></div>'
        f'<h2 class="d-title">{_esc(f.title)}</h2>'
        f'<p class="d-reason">{_esc(f.connection)}</p>'
        f"{_timeline(f)}"
        f'<div class="verdict"><span class="verdict-label">Verdict</span>'
        f'<span class="verdict-main">CLEARED · suppressed to protect precision</span>'
        f'<span class="verdict-sub">— cited to the PCP letter · zero false alarm</span></div>'
        "</section>"
    )


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CSS = """
:root{
  --bg:#090a0d; --panel:#0d1119; --panel2:#12161e; --panel3:#161b23;
  --line:#14181f; --line2:#1a2029; --line3:#232a38; --strong:#2a3340;
  --ink:#e6e9f0; --ink2:#eef1f5; --body:#c2c9d4; --body2:#aab3c2;
  --dim:#8b94a4; --dim2:#7c8698; --dim3:#5f6b7a; --dot:#39424f;
  --teal:#35d6c3; --teal2:#5eead4; --teal3:#6ff0e0; --teal-deep:#5eb8b0;
  --rose:#fda4b4; --rose-dim:#c99aa4; --amber:#fcd77f;
  --mono:'IBM Plex Mono',ui-monospace,'SF Mono',Menlo,monospace;
  --sans:'IBM Plex Sans',ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased;}
::selection{background:rgba(53,214,195,.28);}
@keyframes gate{0%,100%{box-shadow:0 0 0 0 rgba(244,63,94,0);}50%{box-shadow:0 0 0 3px rgba(244,63,94,.13);}}
@keyframes rise{from{opacity:0;transform:translateY(6px);}to{opacity:1;transform:none;}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;}}

/* top bar / bookend */
.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;
  padding:13px 22px;border-bottom:1px solid var(--line);
  background:linear-gradient(180deg,rgba(53,214,195,.05),transparent);}
.brand{display:flex;align-items:center;gap:12px;}
.brand-dot{width:9px;height:9px;border-radius:50%;background:var(--teal);box-shadow:0 0 12px var(--teal);}
.brand-name{font-family:var(--mono);font-size:12.5px;letter-spacing:.2em;font-weight:600;}
.brand-div{width:1px;height:15px;background:var(--line3);}
.brand-sub{font-size:14px;color:var(--body2);}
.meta{font-family:var(--mono);font-size:12.5px;color:var(--dim);display:flex;flex-wrap:wrap;gap:10px;align-items:center;}
.meta b{color:var(--ink);font-weight:600;}
.meta .sep{color:var(--dot);}
.meta .m-surf{color:var(--rose);} .meta .m-clr{color:var(--teal2);}
.tagline{padding:9px 22px 0;font-size:12.5px;color:var(--dim2);font-style:italic;}

/* master-detail */
.layout{display:flex;align-items:flex-start;}
.worklist{flex:none;width:306px;padding:16px 14px 24px;position:sticky;top:0;}
.wl-group{display:flex;align-items:center;gap:10px;margin:2px 2px 10px;}
.wl-group.second{margin-top:20px;}
.wl-gdot{width:6px;height:6px;border-radius:50%;}
.wl-gdot.surf{background:var(--rose);} .wl-gdot.clr{background:var(--teal2);}
.wl-glabel{font-family:var(--mono);font-size:10px;letter-spacing:.16em;color:var(--dim);text-transform:uppercase;}
.wl-gcount{margin-left:auto;font-family:var(--mono);font-size:10px;color:var(--dim3);}
.wl-row{display:block;width:100%;text-align:left;cursor:pointer;
  background:var(--panel);border:1px solid var(--line2);border-radius:12px;
  padding:11px 13px;margin-bottom:9px;color:inherit;font:inherit;transition:border-color .15s,background .15s;}
.wl-row:hover{border-color:var(--strong);}
.wl-row.active{border-color:rgba(53,214,195,.5);background:linear-gradient(180deg,rgba(53,214,195,.06),var(--panel));}
.wl-row:focus-visible{outline:2px solid var(--teal);outline-offset:2px;}
.wl-cleared.active{border-color:rgba(94,234,212,.45);}
.wl-badges{display:flex;align-items:center;gap:6px;margin-bottom:7px;}
.wl-rank{margin-left:auto;font-family:var(--mono);font-size:10px;color:var(--dim3);}
.wl-title{font-size:13px;font-weight:600;line-height:1.35;color:var(--ink);}
.wl-sub{font-family:var(--mono);font-size:10px;color:var(--dim2);margin-top:5px;letter-spacing:.02em;}

/* detail column */
.detail-col{flex:1;min-width:0;padding:18px 24px 40px;border-left:1px solid var(--line);}
.detail{animation:rise .32s ease both;max-width:760px;}
.d-head{display:flex;align-items:center;justify-content:space-between;gap:12px;}
.d-pills{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.d-rank{font-family:var(--mono);font-size:11px;color:var(--dim3);}
.d-clabel{font-family:var(--mono);font-size:11px;color:var(--dim3);}
.d-title{font-size:21px;font-weight:600;letter-spacing:-.01em;line-height:1.25;margin:12px 0 0;}
.d-reason{font-size:14px;line-height:1.62;color:var(--body2);margin:9px 0 4px;}

/* pills — color always paired with text (+ glyph in detail) */
.pill{display:inline-flex;align-items:center;gap:5px;font-family:var(--mono);font-size:10px;
  font-weight:600;letter-spacing:.05em;padding:3px 9px;border-radius:999px;white-space:nowrap;}
.risk-high{background:rgba(244,63,94,.13);color:var(--rose);border:1px solid rgba(244,63,94,.3);}
.risk-med{background:rgba(251,191,36,.12);color:var(--amber);border:1px solid rgba(251,191,36,.28);}
.risk-low{background:rgba(94,234,212,.1);color:var(--teal2);border:1px solid rgba(94,234,212,.28);}
.pill-status{background:rgba(255,255,255,.035);color:var(--body2);border:1px solid var(--strong);}
.pill-cleared{background:rgba(94,234,212,.12);color:var(--teal2);border:1px solid rgba(94,234,212,.3);}

/* evidence timeline */
.ev-label{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--dim2);margin:20px 0 12px;}
.timeline{display:flex;flex-direction:column;}
.ev-row{display:flex;gap:14px;}
.ev-day{flex:none;width:46px;text-align:right;font-family:var(--mono);font-size:11px;color:var(--dim);padding-top:10px;}
.ev-day-gap{color:var(--rose);}
.ev-node{flex:none;width:20px;display:flex;justify-content:center;position:relative;}
.ev-node::before{content:'';position:absolute;top:14px;bottom:-10px;left:50%;width:2px;
  background:var(--line3);transform:translateX(-50%);}
.ev-row.ev-last .ev-node::before{display:none;}
.ev-dot{width:11px;height:11px;border-radius:50%;background:var(--panel);position:relative;z-index:1;margin-top:11px;}
.node-teal{border:2px solid var(--teal);} .node-rose{border:2px solid var(--rose);}
.ev-card{flex:1;min-width:0;border:1px solid var(--line2);border-radius:10px;overflow:hidden;margin-bottom:12px;}
.ev-gap{border-color:rgba(244,63,94,.28);background:rgba(244,63,94,.04);animation:gate 2.8s ease-in-out infinite;}
.ev-head{display:flex;justify-content:space-between;gap:10px;padding:6px 12px;background:var(--panel2);
  font-family:var(--mono);font-size:10.5px;color:var(--dim2);border-bottom:1px solid var(--line2);}
.ev-head-gap{background:#1a1218;color:var(--rose-dim);border-bottom-color:rgba(244,63,94,.18);}
.ev-head-dim span:last-child,.ev-head .ev-head-dim{color:var(--dim3);}
.ev-head-dim{color:var(--dim3);}
.ev-match{color:var(--teal2);font-weight:600;}
.ev-gaptag{color:var(--rose);font-weight:600;}
.ev-quote{padding:10px 12px;font-family:var(--mono);font-size:11.5px;line-height:1.55;color:var(--body);}

/* sparkline */
.spark{margin:14px 0 4px;padding:14px 14px 8px;border:1px solid var(--line2);border-radius:12px;background:var(--panel2);}
.spark-head{display:flex;justify-content:space-between;font-family:var(--mono);font-size:11px;color:var(--dim);margin-bottom:6px;}
.spark-peak{color:var(--amber);}
.spark svg{width:100%;height:82px;overflow:visible;display:block;}

/* escalation — the hero element, most contrast */
.escalation{margin-top:16px;padding:16px 17px;border:1px solid rgba(244,63,94,.32);border-radius:13px;
  background:linear-gradient(180deg,rgba(244,63,94,.08),rgba(244,63,94,.02));}
.esc-label{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--rose);margin-bottom:8px;}
.esc-q{font-size:16px;line-height:1.5;color:var(--ink2);font-weight:500;}

/* action */
.action{margin-top:13px;padding:15px 16px;background:rgba(255,255,255,.02);border:1px solid var(--line2);border-radius:13px;}
.act-label{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim2);margin-bottom:8px;}
.act-text{font-size:13px;line-height:1.58;color:var(--body2);}
.btn{margin-top:13px;background:var(--teal);color:#04231f;border:0;padding:9px 16px;border-radius:8px;
  font-family:var(--sans);font-size:13px;font-weight:600;cursor:pointer;transition:transform .08s,background .15s;}
.btn:hover{background:var(--teal3);} .btn:active{transform:translateY(1px);}
.btn:disabled{background:rgba(94,234,212,.14);color:var(--teal2);cursor:default;}
.btn:focus-visible{outline:2px solid var(--teal);outline-offset:2px;}
.audit{display:none;margin-top:12px;font-family:var(--mono);font-size:11px;color:var(--teal2);line-height:1.5;}
.queued{margin-top:12px;font-family:var(--mono);font-size:11px;color:var(--dim2);}

/* cleared verdict */
.verdict{margin-top:14px;padding:13px 15px;border:1px solid rgba(94,234,212,.24);border-radius:12px;
  background:rgba(94,234,212,.04);display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
.verdict-label{font-family:var(--mono);font-size:10px;letter-spacing:.14em;color:var(--teal-deep);}
.verdict-main{font-size:14px;font-weight:600;color:#8ff0e0;}
.verdict-sub{font-size:12px;color:var(--dim);}

/* footer */
.footer{padding:15px 22px;border-top:1px solid var(--line);display:flex;gap:24px;flex-wrap:wrap;
  align-items:center;justify-content:center;font-family:var(--mono);font-size:11.5px;color:#6f7a8a;}
.footer b{color:var(--teal2);} .footer .c-cited{color:var(--ink);}
"""

_JS = """
function sel(id){
  document.querySelectorAll('[data-detail]').forEach(function(d){
    d.style.display = (d.getAttribute('data-detail')===id) ? 'block' : 'none';
  });
  document.querySelectorAll('[data-row]').forEach(function(r){
    r.classList.toggle('active', r.getAttribute('data-row')===id);
  });
  window.scrollTo({top:0,behavior:'instant'});
}
function approve(btn){ btn.disabled = true; btn.parentElement.querySelector('.audit').style.display='block'; }
"""


def build_html(result: ChartReviewResult, bundle: ChartBundle, stats: dict) -> str:
    surfaced = result.findings
    cleared = result.cleared
    first_id = surfaced[0].thread_id if surfaced else (cleared[0].thread_id if cleared else "")

    wl = ['<div class="wl-group"><span class="wl-gdot surf"></span>'
          '<span class="wl-glabel">Surfaced</span>'
          f'<span class="wl-gcount">ranked · {len(surfaced)}</span></div>']
    wl += [_worklist_row(f, i + 1, active=(f.thread_id == first_id)) for i, f in enumerate(surfaced)]
    if cleared:
        wl.append('<div class="wl-group second"><span class="wl-gdot clr"></span>'
                  '<span class="wl-glabel">Cleared</span>'
                  f'<span class="wl-gcount">precision proof · {len(cleared)}</span></div>')
        wl += [_worklist_cleared_row(f, active=(f.thread_id == first_id and not surfaced)) for f in cleared]

    details = [
        _detail_surfaced(f, i + 1, len(surfaced), shown=(f.thread_id == first_id), live=(i == 0))
        for i, f in enumerate(surfaced)
    ]
    details += [_detail_cleared(f, shown=(f.thread_id == first_id and not surfaced)) for f in cleared]

    p = stats
    footer = (
        f'<span>precision <b>{p["precision"]}</b></span>'
        f'<span>recall <b>{p["recall"]}</b></span>'
        f'<span>citations validated <b class="c-cited">{p["cit_pass"]} / {p["cit_checked"]}</b></span>'
        f'<span>hallucinated <b>{p["cit_failed"]}</b></span>'
        f'<span>every quote is an exact substring of the chart</span>'
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Safety Net — Whole-Chart Review</title>
<style>{_CSS}</style></head>
<body>
<div class="topbar">
  <div class="brand"><span class="brand-dot"></span>
    <span class="brand-name">SAFETY NET</span><span class="brand-div"></span>
    <span class="brand-sub">Whole-Chart Review</span></div>
  <div class="meta"><span><b>14-day admission</b></span><span class="sep">·</span>
    <span><b class="m-surf">{len(surfaced)}</b> surfaced</span><span class="sep">·</span>
    <span><b class="m-clr">{len(cleared)}</b> cleared</span><span class="sep">·</span>
    <span><b>{p["cit_pass"]}/{p["cit_checked"]}</b> citations valid</span></div>
</div>
<div class="tagline">Discharge isn't the finish line. Safety Net re-read all 14 days — every note, lab, and consult — and surfaced only what fell through.</div>
<div class="layout">
  <nav class="worklist">{"".join(wl)}</nav>
  <div class="detail-col">{"".join(details)}</div>
</div>
<div class="footer">{footer}</div>
<script>{_JS}</script>
</body></html>
"""


def _compute_stats(result: ChartReviewResult, bundle: ChartBundle) -> dict:
    checked, passed, failed, _ = validate_all_citations(result, bundle)
    stats = {"cit_checked": checked, "cit_pass": passed, "cit_failed": failed,
             "precision": "—", "recall": "—"}
    try:
        gt = load_ground_truth()
        summ = score(result, gt, bundle)
        stats["precision"] = f"{summ.precision:g}"
        stats["recall"] = f"{summ.recall:g}"
    except Exception:  # noqa: BLE001 — footer degrades to citation stats if no manifest
        pass
    return stats


def main() -> int:
    bundle = load_chart()
    result = run_review(bundle, use_cache=True)
    stats = _compute_stats(result, bundle)
    _OUT.write_text(build_html(result, bundle, stats), encoding="utf-8")
    print(f"Wrote {_OUT}")
    print(f"  surfaced: {len(result.findings)}   cleared: {len(result.cleared)}   "
          f"precision: {stats['precision']}   citations: {stats['cit_pass']}/{stats['cit_checked']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
