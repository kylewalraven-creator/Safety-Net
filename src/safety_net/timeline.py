"""Timeline / entity threading — Stage 2 of the whole-chart pipeline (NEW).

Deterministic code, no LLM (per the schema contract and build plan). Groups
``ExtractedSignal``s by their canonical ``entity`` key, sorts each group by
time, and emits one ``Thread`` per entity. Event ordering is load-bearing
downstream, so the sort is stable and total: (day, note timestamp, signal_id).

This is the small, genuinely-new module the build plan calls out — it is what
lets the reasoner see a whole thread across days/domains that no single note
holds. Keeping it in code (not an LLM) is what makes it reliable.
"""

from __future__ import annotations

from collections import Counter

from .models import ChartBundle, ExtractedSignal, SignalType, Thread


def _timestamp_of(signal: ExtractedSignal, bundle: ChartBundle | None) -> str:
    """The source note's timestamp, used as the within-day sort key. Falls back
    to empty string if the note can't be resolved (ordering still total via the
    signal_id tiebreak)."""
    if bundle is None:
        return ""
    note = bundle.note_by_id(signal.source_note_id)
    return note.timestamp if note is not None else ""


def _dominant_type(signals: list[ExtractedSignal]) -> SignalType:
    """The most common signal_type across the thread, ties broken by first
    appearance (Counter.most_common preserves insertion order on ties in 3.7+)."""
    counts = Counter(s.signal_type for s in signals)
    return counts.most_common(1)[0][0]


def build_threads(
    signals: list[ExtractedSignal], bundle: ChartBundle | None = None
) -> list[Thread]:
    """Group signals by entity, sort by time, emit one Thread per entity.

    Threads with a single event are valid (e.g. a lone incidental nodule).
    Threads are returned in a stable order (earliest first_day, then entity)."""
    by_entity: dict[str, list[ExtractedSignal]] = {}
    for s in signals:
        by_entity.setdefault(s.entity, []).append(s)

    threads: list[Thread] = []
    for entity, group in by_entity.items():
        ordered = sorted(
            group,
            key=lambda s: (s.day, _timestamp_of(s, bundle), s.signal_id),
        )
        days = [s.day for s in ordered]
        threads.append(
            Thread(
                thread_id=f"t_{entity}",
                entity=entity,
                signal_type=_dominant_type(ordered),
                event_signal_ids=[s.signal_id for s in ordered],
                first_day=min(days),
                last_day=max(days),
            )
        )

    threads.sort(key=lambda t: (t.first_day, t.entity))
    return threads
