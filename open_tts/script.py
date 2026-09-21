"""Load interview YAML scripts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


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
            line["cue"] = str(entry["cue"])
        lines.append(line)
    return lines


def save_interview(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def interview_document(
    *,
    title: str,
    characters: dict[str, str],
    layout: dict[str, int],
    script_rows: list[dict[str, str]],
) -> dict[str, Any]:
    script: list[dict[str, str]] = []
    for row in script_rows:
        entry: dict[str, str] = {
            "speaker": row["speaker"],
            "text": row["text"],
        }
        cue = row.get("cue")
        if cue:
            entry["cue"] = cue
        script.append(entry)
    return {
        "title": title,
        "characters": characters,
        "layout": layout,
        "script": script,
    }


def layout_options(data: dict[str, Any]) -> dict[str, str | int]:
    layout = data.get("layout") or {}
    characters = data.get("characters") or {}
    host_raw = characters.get("host", "leo")
    guest_raw = characters.get("guest", "eve")
    return {
        "dual_start_turns": int(layout.get("dual_start_turns", 4)),
        "dual_end_turns": int(layout.get("dual_end_turns", 5)),
        "host": resolve_speaker(str(host_raw), characters),
        "guest": resolve_speaker(str(guest_raw), characters),
    }
