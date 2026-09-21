"""Cue validation and deterministic auto-suggest for interview scripts."""

from __future__ import annotations

import re

from open_tts.sprite import EXPRESSION_COL

VALID_CUES = frozenset({"pause", *EXPRESSION_COL.keys()})


def validate_cue(cue: str) -> None:
    key = cue.lower().strip()
    if key not in VALID_CUES:
        known = ", ".join(sorted(VALID_CUES))
        raise ValueError(f"Unknown cue '{cue}'. Known cues: {known}")


def suggest_cue(text: str, *, is_listener: bool = False) -> str:
    """Return a cue id or ``auto`` when viseme mouth animation should be used."""
    if is_listener:
        return "listen"
    stripped = text.strip()
    if not stripped or stripped in ("…", "..."):
        return "listen"
    low = stripped.lower()
    if any(k in low for k in ("laugh", "haha", "enthusiasm", "hilarious")):
        return "laugh"
    if any(k in low for k in ("?", "wow", "really", "unusual")):
        return "surprise"
    if any(k in low for k in ("thank", "pleasure", "welcome", "delighted", "great to be")):
        return "smile"
    if any(k in low for k in ("unfortunately", "oversell", "risk")) or re.search(
        r"\bbut\b", low
    ):
        return "concern"
    if any(k in low for k in ("well", "technically", "database", "vault")) or re.search(
        r"\bso\b", low
    ):
        return "think"
    return "auto"
