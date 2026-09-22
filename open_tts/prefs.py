"""Studio prefs (last left/right cast). Gitignored; not a secret store."""

from __future__ import annotations

import json
import os
from pathlib import Path

from open_tts.characters import repo_root

PREFS_NAME = ".studio-prefs.json"
DEFAULT_HOST = "leo"
DEFAULT_GUEST = "eve"


def prefs_path(root: Path | None = None) -> Path:
    override = os.environ.get("OPEN_TTS_PREFS_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return (root or repo_root()) / PREFS_NAME


def load_prefs(root: Path | None = None) -> dict:
    path = prefs_path(root)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_prefs(data: dict, root: Path | None = None) -> Path:
    path = prefs_path(root)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def last_cast(root: Path | None = None) -> tuple[str, str]:
    data = load_prefs(root)
    host = str(data.get("last_host") or DEFAULT_HOST)
    guest = str(data.get("last_guest") or DEFAULT_GUEST)
    return host, guest


def remember_cast(host: str, guest: str, root: Path | None = None) -> None:
    data = load_prefs(root)
    data["last_host"] = host
    data["last_guest"] = guest
    save_prefs(data, root)


def last_project(root: Path | None = None) -> str | None:
    value = load_prefs(root).get("last_project")
    return str(value) if value else None


def remember_project(path: Path, root: Path | None = None) -> None:
    data = load_prefs(root)
    data["last_project"] = str(path)
    save_prefs(data, root)


def last_model(root: Path | None = None) -> str | None:
    value = load_prefs(root).get("last_model")
    return str(value) if value else None


def remember_model(char_id: str, root: Path | None = None) -> None:
    data = load_prefs(root)
    data["last_model"] = char_id
    save_prefs(data, root)


def last_hero(root: Path | None = None) -> str | None:
    value = load_prefs(root).get("last_hero")
    return str(value) if value else None


def remember_hero(path: Path, root: Path | None = None) -> None:
    data = load_prefs(root)
    data["last_hero"] = str(path)
    save_prefs(data, root)


def last_heroes(root: Path | None = None) -> dict[str, str]:
    raw = load_prefs(root).get("last_heroes") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items() if key and value}


def remember_hero_for(char_id: str, path: Path, root: Path | None = None) -> None:
    data = load_prefs(root)
    heroes = data.get("last_heroes")
    if not isinstance(heroes, dict):
        heroes = {}
    heroes[char_id] = str(path)
    data["last_heroes"] = heroes
    data["last_hero"] = str(path)
    save_prefs(data, root)


def hero_pref_for(char_id: str, root: Path | None = None) -> Path | None:
    value = last_heroes(root).get(char_id)
    if not value:
        return None
    path = Path(value)
    return path if path.is_file() else None
