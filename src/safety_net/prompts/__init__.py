"""Prompt loading.

The reconciliation system prompt is copied VERBATIM from
``docs/reconciliation-prompt.md`` into ``reconciliation_system.txt``; do not
paraphrase or edit it here. The extraction and action-draft prompts live
alongside it as plain-text files so all prompt text is versioned and diffable.
"""

from __future__ import annotations

from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


def _load(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8")


def reconciliation_system() -> str:
    """The Opus reconciliation system prompt (verbatim from the docs)."""
    return _load("reconciliation_system.txt")


def extraction_system() -> str:
    """The Haiku bulk-extraction system prompt."""
    return _load("extraction_system.txt")


def action_draft_system() -> str:
    """The Opus action-drafting system prompt."""
    return _load("action_draft_system.txt")


# ---- Whole-chart review prompts ---------------------------------------


def whole_chart_extraction_system() -> str:
    """The Haiku widened-extraction system prompt (note -> ExtractedSignal[])."""
    return _load("whole_chart_extraction_system.txt")


def whole_chart_reasoning_system() -> str:
    """The Opus whole-chart reconciliation prompt (verbatim from doc 03 +
    the two few-shot anchors)."""
    return _load("whole_chart_reasoning_system.txt")


# Eagerly loaded constants for convenience.
RECONCILIATION_SYSTEM = reconciliation_system()
EXTRACTION_SYSTEM = extraction_system()
ACTION_DRAFT_SYSTEM = action_draft_system()
WHOLE_CHART_EXTRACTION_SYSTEM = whole_chart_extraction_system()
WHOLE_CHART_REASONING_SYSTEM = whole_chart_reasoning_system()

__all__ = [
    "reconciliation_system",
    "extraction_system",
    "action_draft_system",
    "whole_chart_extraction_system",
    "whole_chart_reasoning_system",
    "RECONCILIATION_SYSTEM",
    "EXTRACTION_SYSTEM",
    "ACTION_DRAFT_SYSTEM",
    "WHOLE_CHART_EXTRACTION_SYSTEM",
    "WHOLE_CHART_REASONING_SYSTEM",
]
