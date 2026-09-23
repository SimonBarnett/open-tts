"""Interview overlays: background plate, title card, scrolling credits."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from open_tts.characters import repo_root

# Same canvas as M:\open-tts full_* / dual_* talking-head loops.
SIZE = (736, 400)
TITLE_DURATION_SEC = 3.0
SCROLL_PX_PER_SEC = 64.0


@dataclass(frozen=True)
class OverlaySpec:
    background: Path | None
    title_text: str
    title_image: Path | None
    title_duration: float
    scroll_text: str
    scroll_duration: float

    @property
    def has_title(self) -> bool:
        return bool(self.title_text.strip() or (self.title_image and self.title_image.is_file()))

    @property
    def has_scroll(self) -> bool:
        return bool(self.scroll_text.strip())


def _resolve(raw: str | None, yaml_path: Path | None) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if path.is_file():
        return path.resolve()
    if yaml_path is not None:
        cand = (yaml_path.parent / path).resolve()
        if cand.is_file():
            return cand
    cand = (repo_root() / path).resolve()
    return cand if cand.is_file() else path


def overlay_spec(data: dict[str, Any], yaml_path: Path | None = None) -> OverlaySpec:
    raw = data.get("overlays") or {}
    title = raw.get("title") or {}
    scroll = raw.get("scroll") or {}
    if isinstance(title, str):
        title = {"text": title}
    if isinstance(scroll, str):
        scroll = {"text": scroll}
    title_text = str(title.get("text") or "")
    scroll_text = str(scroll.get("text") or "")
    title_dur = float(title.get("duration") or TITLE_DURATION_SEC)
    lines = [ln for ln in scroll_text.splitlines() if ln.strip()]
    default_scroll = max(4.0, 2.0 + len(lines) * 0.9)
    scroll_dur = float(scroll.get("duration") or default_scroll)
    return OverlaySpec(
        background=_resolve(raw.get("background"), yaml_path),
        title_text=title_text,
        title_image=_resolve(title.get("image"), yaml_path),
        title_duration=max(0.5, title_dur),
        scroll_text=scroll_text,
        scroll_duration=max(1.0, scroll_dur),
    )


def overlays_to_yaml(spec: OverlaySpec, yaml_path: Path | None = None) -> dict[str, Any]:
    """Serialize for interview YAML; store repo-relative paths when possible."""
    root = repo_root()
    base = yaml_path.parent if yaml_path else root

    def rel(path: Path | None) -> str | None:
        if path is None:
            return None
        for origin in (base, root):
            try:
                return path.resolve().relative_to(origin.resolve()).as_posix()
            except ValueError:
                continue
        return str(path)

    out: dict[str, Any] = {}
    bg = rel(spec.background)
    if bg:
        out["background"] = bg
    title: dict[str, Any] = {}
    if spec.title_text.strip():
        title["text"] = spec.title_text.strip()
    img = rel(spec.title_image)
    if img:
        title["image"] = img
    if spec.title_duration and spec.has_title:
        title["duration"] = spec.title_duration
    if title:
        out["title"] = title
    if spec.scroll_text.strip():
        out["scroll"] = {
            "text": spec.scroll_text.strip(),
            "duration": spec.scroll_duration,
        }
    return out


def import_drop(src: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if src.resolve() != dest.resolve():
        dest.write_bytes(src.read_bytes())
    return dest.resolve()


def load_background(path: Path | None, size: tuple[int, int] = SIZE) -> Image.Image:
    """Transparent plate unless the user dropped a still background."""
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    if path is None or not path.is_file():
        return canvas
    if path.suffix.lower() in {".mp4", ".mov", ".webm", ".mkv"}:
        return canvas
    bg = Image.open(path).convert("RGBA")
    bg = bg.resize(size, Image.Resampling.LANCZOS)
    canvas.paste(bg, (0, 0))
    return canvas


def composite_on_background(
    foreground: Image.Image,
    dest: Path,
    size: tuple[int, int],
    background: Path | None,
    offset: tuple[int, int] | None = None,
) -> None:
    canvas = load_background(background, size)
    fg = foreground.convert("RGBA")
    if offset is None:
        ox = (size[0] - fg.width) // 2
        oy = (size[1] - fg.height) // 2
    else:
        ox, oy = offset
    canvas.paste(fg, (ox, oy), fg)
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest)
    canvas.close()


def ffmpeg_escape_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def title_drawtext(text: str) -> str:
    safe = ffmpeg_escape_text(text.strip() or "Interview")
    return (
        f"drawtext=text='{safe}':fontcolor=white:fontsize=48:"
        "x=(w-text_w)/2:y=(h-text_h)/2:borderw=3:bordercolor=black"
    )


def scroll_drawtext(textfile: Path, height: int, duration: float) -> str:
    path = str(textfile.resolve()).replace("\\", "/").replace(":", "\\:")
    speed = max(24.0, (height + 400) / max(duration, 1.0))
    return (
        f"drawtext=textfile='{path}':fontcolor=white:fontsize=28:"
        f"x=(w-text_w)/2:y=h-{speed}*t:line_spacing=12:borderw=2:bordercolor=black"
    )
