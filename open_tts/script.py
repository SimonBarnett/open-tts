"""Load interview YAML scripts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from open_tts.cues import validate_cue

SCREEN_AUTO = "auto"
SCREEN_FULL = "full"
SCREEN_SPLIT = "split"
SCREEN_CHOICES: tuple[str, ...] = (SCREEN_AUTO, SCREEN_FULL, SCREEN_SPLIT)
STAGE_AUTO = "auto"


def side_override(entry: dict[str, Any], key: str) -> str | None:
    """Explicit left/right on a line, or None to inherit the previous stage."""
    if key not in entry or entry[key] is None:
        return None
    raw = str(entry[key]).strip()
    if raw in ("", STAGE_AUTO):
        return None
    if raw in ("(none)", "none"):
        return ""
    return raw


def apply_cast_overrides(
    lines: list[dict[str, Any]],
    default_left: str | None = None,
    default_right: str | None = None,
) -> list[dict[str, Any]]:
    """Resolve left/right for every line. ``swap: true`` flips sides from that line on."""
    seen: list[str] = []
    for line in lines:
        sp = str(line.get("speaker") or "")
        if sp and sp not in seen:
            seen.append(sp)
    left = default_left or (seen[0] if seen else "leo")
    right = default_right or (seen[1] if len(seen) > 1 else (seen[0] if seen else "eve"))
    out: list[dict[str, Any]] = []
    for raw in lines:
        line = dict(raw)
        new_left = side_override(line, "left")
        new_right = side_override(line, "right")
        if line.get("swap") and new_left is None and new_right is None:
            left, right = right, left
        else:
            if new_left is not None:
                left = new_left
            if new_right is not None:
                right = new_right
        line["_left"] = left
        line["_right"] = right
        out.append(line)
    return out


def screen_from_entry(entry: dict[str, Any]) -> str:
    """Per-utterance screen: auto (layout default), full, or split."""
    if "split" in entry and entry["split"] is not None:
        return SCREEN_SPLIT if bool(entry["split"]) else SCREEN_FULL
    raw = str(entry.get("screen") or "").strip().lower()
    if raw in (SCREEN_FULL, SCREEN_SPLIT, "solo"):
        return SCREEN_FULL if raw in (SCREEN_FULL, "solo") else SCREEN_SPLIT
    if raw in ("dual", "both"):
        return SCREEN_SPLIT
    return SCREEN_AUTO


def split_yaml_value(screen: str) -> bool | None:
    """True/False to write ``split``; None omits the key (auto)."""
    key = (screen or "").strip().lower()
    if key == SCREEN_SPLIT:
        return True
    if key in (SCREEN_FULL, "solo"):
        return False
    return None


def load_interview(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Interview YAML must be a mapping: {path}")
    for key in ("title", "characters", "script"):
        if key not in data:
            raise ValueError(f"Interview missing required key '{key}': {path}")
    return data


def resolve_speaker(raw: str, characters: dict[str, str]) -> str:
    """Map role aliases (host/guest) to character ids."""
    if raw in characters:
        return characters[raw]
    return raw


def normalized_lines(data: dict[str, Any]) -> list[dict]:
    characters = data["characters"]
    lines: list[dict] = []
    for entry in data["script"]:
        if isinstance(entry, str):
            raise ValueError("Script entries must be mappings with speaker and text")
        speaker = resolve_speaker(str(entry["speaker"]), characters)
        line = {
            "speaker": speaker,
            "text": str(entry["text"]),
        }
        if "cue" in entry and entry["cue"]:
            cue = str(entry["cue"])
            validate_cue(cue)
            line["cue"] = cue
        screen = screen_from_entry(entry)
        if screen == SCREEN_SPLIT:
            line["split"] = True
        elif screen == SCREEN_FULL:
            line["split"] = False
        for key in ("left", "right"):
            side = side_override(entry, key)
            if side is not None:
                line[key] = resolve_speaker(side, characters) if side else ""
        if entry.get("swap"):
            line["swap"] = True
        lines.append(line)
    return lines


def apply_line_to_script(
    data: dict[str, Any],
    line_index: int,
    *,
    speaker: str,
    text: str,
    cue: str | None,
    split: bool | None = None,
    left: str | None = None,
    right: str | None = None,
    swap: bool | None = None,
) -> None:
    """Update one script entry in place (#1 schema). line_index is 0-based."""
    script = data["script"]
    if line_index < 0 or line_index >= len(script):
        raise IndexError(f"Line index out of range: {line_index}")
    entry = script[line_index]
    if not isinstance(entry, dict):
        raise ValueError("Script entry must be a mapping")
    entry["speaker"] = speaker
    entry["text"] = text
    if cue:
        entry["cue"] = cue
    elif "cue" in entry:
        del entry["cue"]
    if split is True:
        entry["split"] = True
    elif split is False:
        entry["split"] = False
    if left is not None:
        if left in ("", STAGE_AUTO):
            entry.pop("left", None)
        else:
            entry["left"] = left
    if right is not None:
        if right in ("", STAGE_AUTO):
            entry.pop("right", None)
        else:
            entry["right"] = right
    if swap is True:
        entry["swap"] = True
    elif swap is False:
        entry.pop("swap", None)


def save_interview(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def interview_document(
    *,
    title: str,
    characters: dict[str, str],
    layout: dict[str, Any],
    script_rows: list[dict[str, Any]],
    overlays: dict[str, Any] | None = None,
) -> dict[str, Any]:
    script: list[dict[str, Any]] = []
    for row in script_rows:
        entry: dict[str, Any] = {
            "speaker": row["speaker"],
            "text": row["text"],
        }
        cue = row.get("cue")
        if cue:
            entry["cue"] = cue
        if "split" in row and row["split"] is not None:
            entry["split"] = bool(row["split"])
        if "left" in row and row["left"] not in (None, STAGE_AUTO):
            entry["left"] = row["left"]
        if "right" in row and row["right"] not in (None, STAGE_AUTO):
            entry["right"] = row["right"]
        if row.get("swap"):
            entry["swap"] = True
        script.append(entry)
    doc: dict[str, Any] = {
        "title": title,
        "characters": characters,
        "layout": layout,
        "script": script,
    }
    if overlays:
        doc["overlays"] = overlays
    return doc


def layout_options(data: dict[str, Any]) -> dict[str, str | int]:
    layout = data.get("layout") or {}
    characters = data.get("characters") or {}
    host_raw = characters.get("host", "leo")
    guest_raw = characters.get("guest", "eve")
    host = resolve_speaker(str(host_raw), characters)
    guest = resolve_speaker(str(guest_raw), characters)
    return {
        "dual_start_turns": int(layout.get("dual_start_turns", 4)),
        "dual_end_turns": int(layout.get("dual_end_turns", 5)),
        "host": host,
        "guest": guest,
        "left": str(layout.get("left") or host),
        "right": str(layout.get("right") or guest),
    }
