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


def save_registry(
    registry: dict[str, dict[str, Any]], path: Path | None = None
) -> None:
    reg_path = path or (repo_root() / "characters" / "registry.yaml")
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(
        yaml.safe_dump(registry, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )


def upsert_character(
    registry: dict[str, dict[str, Any]],
    character_id: str,
    *,
    voice_id: str,
    sheet: Path | str,
    prompt: str | None = None,
    hero: Path | str | None = None,
) -> None:
    sheet_str = str(sheet)
    root = repo_root()
    try:
        rel = Path(sheet_str).resolve().relative_to(root.resolve())
        sheet_str = rel.as_posix()
    except ValueError:
        pass
    entry: dict[str, Any] = {"voice_id": voice_id, "sheet": sheet_str}
    if prompt:
        entry["prompt"] = prompt
    if hero:
        hero_str = str(hero)
        try:
            rel_h = Path(hero_str).resolve().relative_to(root.resolve())
            hero_str = rel_h.as_posix()
        except ValueError:
            pass
        entry["hero"] = hero_str
    registry[character_id] = entry
