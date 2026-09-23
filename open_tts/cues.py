"""Cue validation and deterministic auto-suggest for interview scripts."""

from __future__ import annotations

import re

from open_tts.sprite import EXPRESSION_COL

AUTO = "auto"

# Attentive is the split-screen listener pose; same cells as listen.
CUE_ALIASES = {"attentive": "listen"}

VALID_CUES = frozenset({"pause", "attentive", *EXPRESSION_COL.keys()})

# Values shown in the studio combo; ``auto`` omits ``cue`` in saved YAML.
ANIMATION_CHOICES: tuple[str, ...] = (
    AUTO,
    "pause",
    "attentive",
    *sorted(EXPRESSION_COL.keys()),
)


def resolve_cue(cue: str) -> str:
    """Map aliases (attentive → listen) to a sheet expression or pause."""
    key = cue.lower().strip()
    return CUE_ALIASES.get(key, key)


def validate_cue(cue: str) -> None:
    key = cue.lower().strip()
    if key not in VALID_CUES and resolve_cue(key) not in VALID_CUES:
        known = ", ".join(sorted(VALID_CUES))
        raise ValueError(f"Unknown cue '{cue}'. Known cues: {known}")


def suggest_cue(text: str, *, is_listener: bool = False) -> str:
    """Return a cue id or ``auto`` when viseme mouth animation should be used."""
    if is_listener:
        return "attentive"
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
    return AUTO


def cue_from_yaml(entry: dict) -> str:
    """Map a script entry to a studio animation value."""
    cue = entry.get("cue")
    if not cue:
        return AUTO
    return str(cue).lower()


def cue_to_yaml_value(animation: str) -> str | None:
    """Return YAML ``cue`` value or None to omit (renderer vowel visemes)."""
    key = animation.strip().lower()
    if key in ("", AUTO, "none"):
        return None
    validate_cue(key)
    return key
