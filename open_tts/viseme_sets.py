"""Central viseme-set catalog. Characters pick a set unless they bake a new one."""

from __future__ import annotations

from pathlib import Path

from open_tts.characters import repo_root
from open_tts.sprite import ensure_placeholder_sheet

DEFAULT_VISEME_SET = "default"
NONE_MODEL = "(none)"


def visemes_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "characters" / "visemes"


def viseme_set_path(set_id: str, root: Path | None = None) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in set_id.strip())
    if not safe:
        safe = DEFAULT_VISEME_SET
    return visemes_dir(root) / f"{safe}.png"


def ensure_default_viseme_set(root: Path | None = None) -> Path:
    path = viseme_set_path(DEFAULT_VISEME_SET, root)
    ensure_placeholder_sheet(path, DEFAULT_VISEME_SET)
    return path


def list_viseme_sets(root: Path | None = None) -> list[str]:
    ensure_default_viseme_set(root)
    names = {DEFAULT_VISEME_SET}
    folder = visemes_dir(root)
    if folder.is_dir():
        names.update(p.stem for p in folder.glob("*.png"))
    return sorted(names)


def sides_to_characters(left: str, right: str) -> dict[str, str]:
    """Map interview stage slots to host/guest. One, the other, or both."""
    left = "" if left == NONE_MODEL else left.strip()
    right = "" if right == NONE_MODEL else right.strip()
    if left and right:
        return {"host": left, "guest": right}
    only = left or right
    if only:
        return {"host": only, "guest": only}
    return {"host": "leo", "guest": "eve"}


def characters_to_sides(characters: dict, layout: dict | None = None) -> tuple[str, str]:
    layout = layout or {}
    left = str(layout.get("left") or characters.get("host") or "leo")
    right = str(layout.get("right") or characters.get("guest") or "eve")
    if left == right:
        return left, NONE_MODEL
    return left, right
