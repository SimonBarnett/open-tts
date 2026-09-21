"""Character registry (voice + sprite sheet paths)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from open_tts.sprite import CharacterSheet, ensure_placeholder_sheet


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_registry(path: Path | None = None) -> dict[str, dict[str, Any]]:
    reg_path = path or (repo_root() / "characters" / "registry.yaml")
    if not reg_path.is_file():
        return _default_registry()
    data = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    return data or {}


def _default_registry() -> dict[str, dict[str, Any]]:
    root = repo_root()
    return {
        "leo": {"voice_id": "leo", "sheet": str(root / "characters" / "leo.png")},
        "eve": {"voice_id": "eve", "sheet": str(root / "characters" / "eve.png")},
    }


def sheet_for(character_id: str, registry: dict[str, dict[str, Any]]) -> CharacterSheet:
    entry = registry.get(character_id)
    if not entry:
        raise KeyError(f"Unknown character id: {character_id}")
    sheet_path = Path(entry["sheet"])
    if not sheet_path.is_absolute():
        sheet_path = repo_root() / sheet_path
    ensure_placeholder_sheet(sheet_path, character_id)
    return CharacterSheet(sheet_path)


def voice_for(character_id: str, registry: dict[str, dict[str, Any]]) -> str:
    entry = registry.get(character_id)
    if not entry:
        raise KeyError(f"Unknown character id: {character_id}")
    return str(entry.get("voice_id", character_id))
