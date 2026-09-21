"""Deterministic animation cue suggestions for script lines."""

from __future__ import annotations

AUTO = "auto"
PAUSE = "pause"
LAUGH = "laugh"
SURPRISE = "surprise"
SMILE = "smile"
CONCERN = "concern"
THINK = "think"
LISTEN = "listen"

VISEME_CUES = ("a", "e", "i", "o", "u")

EXPRESSION_CUES = (SURPRISE, LAUGH, SMILE, CONCERN, THINK, LISTEN)

# Values shown in the studio combo; `auto` omits `cue` in saved YAML.
ANIMATION_CHOICES: tuple[str, ...] = (
    AUTO,
    PAUSE,
    *VISEME_CUES,
    *EXPRESSION_CUES,
)

VALID_CUES = frozenset({PAUSE, *VISEME_CUES, *EXPRESSION_CUES})


def validate_cue(cue: str) -> None:
    """Reject unknown cue ids at script load (fail closed)."""
    key = cue.strip().lower()
    if key not in VALID_CUES:
        raise ValueError(
            f"Unknown cue '{cue}'; allowed: {', '.join(sorted(VALID_CUES))}"
        )


def suggest_cue(text: str) -> str:
    """Suggest an animation type from line text (deterministic, overridable in UI)."""
    raw = text.strip()
    if not raw or raw in ("…", "..."):
        return LISTEN
    if raw.startswith("(") and raw.endswith(")"):
        return PAUSE

    lower = raw.lower()
    if any(token in lower for token in ("haha", "ha!", "laugh", "enthusiasm", "hilarious")):
        return LAUGH
    if "?" in raw or "!" in raw or "wow" in lower or "really?" in lower or "unusual" in lower:
        return SURPRISE
    if any(
        token in lower
        for token in ("thank", "pleasure", "welcome", "delighted", "great to be")
    ):
        return SMILE
    if any(token in lower for token in ("unfortunately", "oversell", "risk")) or " but " in f" {lower} ":
        return CONCERN
    if any(token in lower for token in ("well", "so", "technically", "database", "vault")):
        return THINK
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
