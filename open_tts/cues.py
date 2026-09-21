"""Deterministic animation cue suggestions for script lines."""

from __future__ import annotations

AUTO = "auto"
PAUSE = "pause"
LAUGH = "laugh"
SURPRISE = "surprise"

VISEME_CUES = ("a", "e", "i", "o", "u")

# Values shown in the studio combo; `auto` omits `cue` in saved YAML.
ANIMATION_CHOICES: tuple[str, ...] = (
    AUTO,
    PAUSE,
    *VISEME_CUES,
    LAUGH,
    SURPRISE,
)


def suggest_cue(text: str) -> str:
    """Suggest an animation type from line text (deterministic, overridable in UI)."""
    raw = text.strip()
    if not raw or raw in ("…", "..."):
        return PAUSE
    if raw.startswith("(") and raw.endswith(")"):
        return PAUSE

    lower = raw.lower()
    if any(
        token in lower
        for token in ("haha", "ha!", "laugh", "enthusiasm")
    ):
        return LAUGH
    if "?" in raw or "!" in raw or "wow" in lower or "really?" in lower:
        return SURPRISE
    return AUTO


def cue_from_yaml(entry: dict) -> str:
    """Map a script entry to a studio animation value."""
    cue = entry.get("cue")
    if not cue:
        return AUTO
    return str(cue).lower()


def cue_to_yaml_value(animation: str) -> str | None:
    """Return YAML `cue` value or None to omit (renderer vowel visemes)."""
    key = animation.strip().lower()
    if key in ("", AUTO, "none"):
        return None
    return key
