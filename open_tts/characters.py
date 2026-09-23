"""Character registry (voice + sprite sheet paths)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from PIL import Image, ImageDraw

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
    viseme_set = str(entry.get("viseme_set") or "").strip()
    if viseme_set:
        from open_tts.viseme_sets import viseme_set_path

        sheet_path = viseme_set_path(viseme_set)
    else:
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


def slug_character_id(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (slug[:32] or "person")


def upsert_character(
    registry: dict[str, dict[str, Any]],
    character_id: str,
    *,
    voice_id: str,
    sheet: Path | str,
    prompt: str | None = None,
    hero: Path | str | None = None,
    viseme_set: str | None = None,
    display_name: str | None = None,
) -> None:
    sheet_str = str(sheet)
    root = repo_root()
    try:
        rel = Path(sheet_str).resolve().relative_to(root.resolve())
        sheet_str = rel.as_posix()
    except ValueError:
        pass
    entry: dict[str, Any] = {"voice_id": voice_id, "sheet": sheet_str}
    if viseme_set:
        entry["viseme_set"] = viseme_set
    if display_name:
        entry["display_name"] = display_name
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


ORIGINAL_IDS = ("leo", "eve")
MIN_REAL_IMAGE_BYTES = 20_000


def original_viseme_path(character_id: str, root: Path | None = None) -> Path:
    return (root or repo_root()) / "characters" / "visemes" / f"{character_id}.png"


def _usable_image(path: Path, min_bytes: int = 400) -> bool:
    """True for a real still/grid, not the 128px grey pause-cell stub."""
    try:
        if not path.is_file() or path.stat().st_size < min_bytes:
            return False
        with Image.open(path) as im:
            return im.width >= 256 and im.height >= 256
    except OSError:
        return False


def best_original_sheet(character_id: str, root: Path | None = None) -> Path | None:
    """Photoreal Leo/Eve viseme grid, if present; else a large characters/<id>.png."""
    base = root or repo_root()
    viseme = original_viseme_path(character_id, base)
    if _usable_image(viseme):
        return viseme.resolve()
    sheet = original_sheet_path(character_id, base)
    if _usable_image(sheet):
        return sheet.resolve()
    return None


def original_pause_cell(character_id: str, root: Path | None = None) -> Image.Image | None:
    """Pause cell from the original viseme grid (Leo full / Eve half composition)."""
    sheet = best_original_sheet(character_id, root)
    if sheet is None:
        return None
    return CharacterSheet(sheet).pause()


def _face_from_sheet(sheet_path: Path, dest: Path) -> Path:
    face = CharacterSheet(sheet_path).pause()
    if face.width < 256 or face.height < 256:
        face = face.resize((512, 512), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    face.save(dest)
    return dest


STAGE_KINDS = ("full", "left", "right")
STAGE_FULL_SIZE = (360, 360)
STAGE_HALF_SIZE = (360, 360)


def default_stage_path(character_id: str, kind: str, root: Path | None = None) -> Path:
    kind = str(kind).strip().lower()
    if kind not in STAGE_KINDS:
        kind = "full"
    return (root or repo_root()) / "characters" / "defaults" / f"{character_id}_{kind}.png"


def stage_source_image(
    character_id: str,
    entry: dict[str, Any] | None = None,
    extra: Path | str | None = None,
    root: Path | None = None,
) -> Image.Image | None:
    """Kept hero if present; else the original viseme pause cell."""
    base = root or repo_root()
    for path in (
        hero_still_path(character_id, base),
        Path(str(entry["hero"])) if entry and entry.get("hero") else None,
        Path(extra) if extra else None,
    ):
        if path is None:
            continue
        listed = path if path.is_absolute() else base / path
        if listed.is_file() and listed.stat().st_size >= 200:
            try:
                return Image.open(listed).convert("RGBA")
            except OSError:
                continue
    cell = original_pause_cell(character_id, base)
    if cell is not None:
        return cell.convert("RGBA")
    portraits = ensure_default_portraits(base)
    if character_id in portraits and portraits[character_id].is_file():
        return Image.open(portraits[character_id]).convert("RGBA")
    return None


def native_stage_kind(character_id: str, root: Path | None = None) -> str:
    """Leo-style close-up is full; Eve-style interview is the right half."""
    from open_tts.framing import is_closeup

    src = original_pause_cell(character_id, root)
    if src is not None and not is_closeup(src):
        return "right"
    return "full"


def ensure_default_stage_stills(root: Path | None = None) -> dict[str, dict[str, Path]]:
    """Bake original full / left / right stills used as the default base models."""
    from open_tts.framing import frame_half, frame_monologue

    base = root or repo_root()
    ensure_default_portraits(base)
    out: dict[str, dict[str, Path]] = {}
    for char_id in ORIGINAL_IDS:
        src = original_pause_cell(char_id, base)
        if src is None:
            portraits = ensure_default_portraits(base)
            if char_id not in portraits:
                continue
            src = Image.open(portraits[char_id]).convert("RGBA")
        paths: dict[str, Path] = {}
        jobs = (
            ("full", lambda: frame_monologue(src, STAGE_FULL_SIZE)),
            ("left", lambda: frame_half(src, STAGE_HALF_SIZE, "left")),
            ("right", lambda: frame_half(src, STAGE_HALF_SIZE, "right")),
        )
        for kind, render in jobs:
            dest = default_stage_path(char_id, kind, base)
            dest.parent.mkdir(parents=True, exist_ok=True)
            want = STAGE_FULL_SIZE if kind == "full" else STAGE_HALF_SIZE
            stale = True
            if dest.is_file():
                try:
                    with Image.open(dest) as existing:
                        stale = existing.size != want
                except OSError:
                    stale = True
            if stale:
                render().save(dest)
            paths[kind] = dest
        out[char_id] = paths
    return out


def resolve_stage_still(
    character_id: str,
    kind: str,
    entry: dict[str, Any] | None = None,
    extra: Path | str | None = None,
    root: Path | None = None,
) -> Path | None:
    """Framed full/left/right still: custom hero when kept, else original bake."""
    from open_tts.framing import frame_half, frame_monologue

    base = root or repo_root()
    kind = str(kind).strip().lower()
    if kind not in STAGE_KINDS:
        kind = native_stage_kind(character_id, base)
    hero = hero_still_path(character_id, base)
    custom = hero.is_file() and hero.stat().st_size >= 200
    if not custom and extra and Path(extra).is_file():
        custom = True
    if not custom and entry and entry.get("hero"):
        listed = Path(str(entry["hero"]))
        if not listed.is_absolute():
            listed = base / listed
        custom = listed.is_file()
    if custom:
        src = stage_source_image(character_id, entry, extra, base)
        if src is None:
            return None
        dest = base / "characters" / "defaults" / f"{character_id}_{kind}_custom.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if kind == "full":
            frame_monologue(src, STAGE_FULL_SIZE).save(dest)
        else:
            frame_half(src, STAGE_HALF_SIZE, kind).save(dest)
        return dest.resolve()
    baked = ensure_default_stage_stills(base).get(character_id, {}).get(kind)
    return baked.resolve() if baked and baked.is_file() else None


_PORTRAIT = {
    "leo": {
        "bg": (36, 48, 72),
        "skin": (222, 184, 148),
        "hair": (62, 42, 32),
        "jacket": (28, 42, 78),
        "shirt": (230, 232, 240),
    },
    "eve": {
        "bg": (72, 40, 52),
        "skin": (236, 196, 168),
        "hair": (42, 26, 22),
        "jacket": (140, 48, 72),
        "shirt": (248, 236, 230),
    },
}


def default_portrait_path(character_id: str, root: Path | None = None) -> Path:
    return (root or repo_root()) / "characters" / "defaults" / f"{character_id}.png"


def _draw_default_portrait(character_id: str) -> Image.Image:
    c = _PORTRAIT.get(character_id, _PORTRAIT["leo"])
    img = Image.new("RGBA", (512, 512), (*c["bg"], 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([40, 330, 472, 640], fill=(*c["jacket"], 255))
    draw.rectangle([208, 370, 304, 470], fill=(*c["shirt"], 255))
    if character_id == "eve":
        draw.ellipse([96, 70, 416, 360], fill=(*c["hair"], 255))
        draw.ellipse([148, 118, 364, 372], fill=(*c["skin"], 255))
        draw.pieslice([96, 200, 170, 420], 90, 270, fill=(*c["hair"], 255))
        draw.pieslice([342, 200, 416, 420], 270, 90, fill=(*c["hair"], 255))
    else:
        draw.ellipse([148, 96, 364, 360], fill=(*c["skin"], 255))
        draw.pieslice([148, 70, 364, 230], 180, 360, fill=(*c["hair"], 255))
        draw.rectangle([148, 96, 364, 150], fill=(*c["hair"], 255))
    draw.ellipse([200, 206, 232, 238], fill=(40, 36, 32, 255))
    draw.ellipse([280, 206, 312, 238], fill=(40, 36, 32, 255))
    draw.arc([214, 258, 298, 318], 15, 165, fill=(120, 64, 64, 255), width=5)
    return img


def ensure_default_portraits(root: Path | None = None) -> dict[str, Path]:
    """Leo/Eve stills: pause cell from the original viseme grid, else a drawn fallback."""
    base = root or repo_root()
    out: dict[str, Path] = {}
    for char_id in ORIGINAL_IDS:
        dest = default_portrait_path(char_id, base)
        dest.parent.mkdir(parents=True, exist_ok=True)
        source = best_original_sheet(char_id, base)
        if source is not None:
            if not dest.is_file() or dest.stat().st_size < MIN_REAL_IMAGE_BYTES:
                _face_from_sheet(source, dest)
        elif not dest.is_file() or dest.stat().st_size < 200:
            _draw_default_portrait(char_id).save(dest)
        out[char_id] = dest
    return out


def original_sheet_path(character_id: str, root: Path | None = None) -> Path:
    return (root or repo_root()) / "characters" / f"{character_id}.png"


def ensure_original_sheets(root: Path | None = None) -> dict[str, Path]:
    """Restore characters/<id>.png from the original viseme grid when one exists."""
    base = root or repo_root()
    portraits = ensure_default_portraits(base)
    ensure_default_stage_stills(base)
    out: dict[str, Path] = {}
    for char_id in ORIGINAL_IDS:
        path = original_sheet_path(char_id, base)
        viseme = original_viseme_path(char_id, base)
        custom = hero_still_path(char_id, base)
        if _usable_image(viseme):
            if not path.is_file() or path.stat().st_size != viseme.stat().st_size:
                path.write_bytes(viseme.read_bytes())
        elif not path.is_file() or not custom.is_file():
            from open_tts.imagine import build_sheet_from_hero

            build_sheet_from_hero(portraits[char_id], path)
        else:
            ensure_placeholder_sheet(path, char_id)
        out[char_id] = path
    return out


def original_face_path(character_id: str, root: Path | None = None) -> Path | None:
    """Pause-cell still from the original viseme grid, for thumbs when no Keep exists."""
    base = root or repo_root()
    sheet_path = best_original_sheet(character_id, base) or original_sheet_path(
        character_id, base
    )
    if character_id in ORIGINAL_IDS:
        if not sheet_path.is_file():
            ensure_placeholder_sheet(sheet_path, character_id)
    elif not sheet_path.is_file():
        return None
    dest = base / "characters" / "original" / f"{character_id}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if (
        dest.is_file()
        and dest.stat().st_mtime >= sheet_path.stat().st_mtime
        and dest.stat().st_size >= 200
    ):
        return dest.resolve()
    CharacterSheet(sheet_path).pause().save(dest)
    return dest.resolve()


def hero_still_path(character_id: str, root: Path | None = None) -> Path:
    safe = re.sub(r"[^a-z0-9-]+", "-", character_id.lower()).strip("-") or "draft"
    return (root or repo_root()) / "characters" / "heroes" / f"{safe}.png"


def persist_hero(src: Path, character_id: str, root: Path | None = None) -> Path:
    """Copy a generated still out of temp into characters/heroes/<id>.png."""
    dest = hero_still_path(character_id, root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(Path(src).read_bytes())
    return dest.resolve()


def set_character_hero(
    registry: dict[str, dict[str, Any]],
    character_id: str,
    hero: Path,
    root: Path | None = None,
) -> None:
    """Write hero on an existing entry without wiping voice / viseme / sheet."""
    base = root or repo_root()
    entry = registry.setdefault(character_id, {"voice_id": character_id})
    hero_str = str(hero)
    try:
        hero_str = Path(hero).resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        hero_str = str(Path(hero).resolve())
    entry["hero"] = hero_str
    if "sheet" not in entry:
        entry["sheet"] = f"characters/{character_id}.png"


def resolve_hero(
    character_id: str,
    entry: dict[str, Any] | None = None,
    extra: Path | str | None = None,
    root: Path | None = None,
) -> Path | None:
    """Keep/heroes first; else the original Leo/Eve viseme face."""
    base = root or repo_root()
    candidates: list[Path] = [hero_still_path(character_id, base)]
    if entry and entry.get("hero"):
        listed = Path(str(entry["hero"]))
        if not listed.is_absolute():
            listed = base / listed
        candidates.append(listed)
    if extra:
        candidates.append(Path(extra))
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.is_file():
            return path.resolve()
    portraits = ensure_default_portraits(base)
    if character_id in portraits:
        return portraits[character_id].resolve()
    return original_face_path(character_id, base)
