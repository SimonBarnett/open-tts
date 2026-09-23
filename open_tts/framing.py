"""Full-screen monologue vs left/right half-screen crops.

Original Leo cells are tight talking-head stills (monologue).
Original Eve cells are wider interview shots with the person on one side
(half-screen). Both versions are derived from the same source cell.

Dual screen is always two halves of the plate (left | right). There is no
separate "split talking" mode — two characters means two halves.

Before generating viseme / clip video, the studio can pan and size the
model on the initial still via Placement (zoom + pan).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from open_tts.sprite import fit_contain

STAGE_SIZE = (736, 400)
STAGE_BG = (8, 10, 20, 255)
STAGE_GRID = (24, 28, 42, 255)


@dataclass
class Placement:
    """Pan/zoom of the model inside the initial still before clip gen."""

    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0

    def clamped(self) -> "Placement":
        return Placement(
            zoom=max(1.0, min(4.0, float(self.zoom))),
            pan_x=max(-1.0, min(1.0, float(self.pan_x))),
            pan_y=max(-1.0, min(1.0, float(self.pan_y))),
        )


def apply_placement(img: Image.Image, placement: Placement | None = None) -> Image.Image:
    """Crop and zoom the still. zoom=1 keeps the full image; pan shifts the crop."""
    src = img.convert("RGBA")
    if placement is None:
        return src
    p = placement.clamped()
    if abs(p.zoom - 1.0) < 1e-6 and abs(p.pan_x) < 1e-6 and abs(p.pan_y) < 1e-6:
        return src
    w, h = src.size
    cw = max(1, int(round(w / p.zoom)))
    ch = max(1, int(round(h / p.zoom)))
    max_ox = max(0, (w - cw) / 2)
    max_oy = max(0, (h - ch) / 2)
    cx = w / 2 + p.pan_x * max_ox
    cy = h / 2 + p.pan_y * max_oy
    x0 = int(round(cx - cw / 2))
    y0 = int(round(cy - ch / 2))
    x0 = max(0, min(w - cw, x0))
    y0 = max(0, min(h - ch, y0))
    crop = src.crop((x0, y0, x0 + cw, y0 + ch))
    return crop.resize((w, h), Image.Resampling.LANCZOS)


def placement_path(hero: Path) -> Path:
    """JSON beside the hero still: characters/heroes/<id>.placement.json."""
    return Path(hero).with_suffix(".placement.json")


def save_placement(hero: Path, placement: Placement) -> Path:
    path = placement_path(hero)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(placement.clamped()), indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_placement(hero: Path | None) -> Placement:
    if hero is None:
        return Placement()
    path = placement_path(Path(hero))
    if not path.is_file():
        return Placement()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return Placement(
            zoom=float(raw.get("zoom", 1.0)),
            pan_x=float(raw.get("pan_x", 0.0)),
            pan_y=float(raw.get("pan_y", 0.0)),
        ).clamped()
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return Placement()


def is_stage_aspect(size: tuple[int, int], tol: float = 0.12) -> bool:
    """True when the plate already matches the 736×400 Full / Left / Right stage."""
    w, h = size
    if h <= 0 or w <= 0:
        return False
    return abs((w / h) - (STAGE_SIZE[0] / STAGE_SIZE[1])) <= tol


def is_stage_pixel(r: int, g: int, b: int) -> bool:
    """Dark navy plate / faint grid, not face, body, or nameplate black."""
    if r < 3 and g < 3 and b < 8:
        return False
    plate = r <= 16 and g <= 18 and b <= 32 and b >= r - 2
    grid = 18 <= r <= 26 and 18 <= g <= 26 and 32 <= b <= 42 and abs(r - g) <= 3
    return plate or grid


def knockout_stage(img: Image.Image) -> Image.Image:
    """Make the original loop's dark grid transparent."""
    canvas = img.convert("RGBA")
    pix = canvas.load()
    w, h = canvas.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if a and is_stage_pixel(r, g, b):
                pix[x, y] = (r, g, b, 0)
    return canvas


def _is_skin(r: int, g: int, b: int) -> bool:
    return r > 90 and g > 40 and b > 30 and r >= g and r > b and (r - g) > 12


def _is_face_hsv(h: int, s: int, v: int) -> bool:
    """Tight face-skin in HSV (0-255). Excludes Eve's desk/plants."""
    return h <= 16 and 85 <= s <= 175 and 80 <= v <= 220


def _is_studio_bg(r: int, g: int, b: int, a: int) -> bool:
    if a < 24:
        return True
    return r > 232 and g > 232 and b > 232


def _bbox_from_mask(points: list[tuple[int, int]], w: int, h: int) -> tuple[int, int, int, int]:
    if not points:
        return (0, 0, w, h)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def skin_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    rgba = img.convert("RGBA")
    hsv = rgba.convert("HSV")
    w, h = rgba.size
    rgb_px = rgba.load()
    hsv_px = hsv.load()
    hits: list[tuple[int, int]] = []
    step = max(1, min(w, h) // 64)
    for y in range(0, int(h * 0.62), step):
        for x in range(0, w, step):
            r, g, b, a = rgb_px[x, y]
            if _is_studio_bg(r, g, b, a):
                continue
            hh, s, v = hsv_px[x, y][:3]
            if _is_face_hsv(hh, s, v) or _is_skin(r, g, b):
                if _is_face_hsv(hh, s, v):
                    hits.append((x, y))
    if len(hits) < 6:
        return None
    xs = sorted(p[0] for p in hits)
    mid = xs[len(xs) // 2]
    clustered = [p for p in hits if abs(p[0] - mid) <= max(8, w * 0.22)]
    if len(clustered) >= 6:
        hits = clustered
    return _bbox_from_mask(hits, w, h)


def subject_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    rgba = img.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    hits: list[tuple[int, int]] = []
    step = max(1, min(w, h) // 64)
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b, a = px[x, y]
            if _is_studio_bg(r, g, b, a):
                continue
            hits.append((x, y))
    return _bbox_from_mask(hits, w, h)


def _area(box: tuple[int, int, int, int]) -> int:
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def _is_flat_studio(r: int, g: int, b: int, a: int) -> bool:
    if a < 40:
        return True
    mx, mn = max(r, g, b), min(r, g, b)
    return mx > 170 and (mx - mn) < 20


def is_closeup(img: Image.Image) -> bool:
    """True for Leo-style headshots (flat studio above the shoulders)."""
    rgba = img.convert("RGBA")
    w, h = rgba.size
    cw, ch = max(1, w // 6), max(1, h // 6)
    px = rgba.load()
    empty = 0
    for x0, y0, x1, y1 in ((0, 0, cw, ch), (w - cw, 0, w, ch)):
        n = bg = 0
        for y in range(y0, y1, 2):
            for x in range(x0, x1, 2):
                r, g, b, a = px[x, y]
                n += 1
                if _is_flat_studio(r, g, b, a) or _is_studio_bg(r, g, b, a):
                    bg += 1
        if n and bg / n > 0.6:
            empty += 1
    return empty >= 2


def _expand_box(
    box: tuple[int, int, int, int],
    size: tuple[int, int],
    pad_x: float,
    pad_y_top: float,
    pad_y_bot: float,
) -> tuple[int, int, int, int]:
    w, h = size
    x0, y0, x1, y1 = box
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    x0 = max(0, int(x0 - bw * pad_x))
    x1 = min(w, int(x1 + bw * pad_x))
    y0 = max(0, int(y0 - bh * pad_y_top))
    y1 = min(h, int(y1 + bh * pad_y_bot))
    if x1 <= x0:
        x0, x1 = 0, w
    if y1 <= y0:
        y0, y1 = 0, h
    return (x0, y0, x1, y1)


def monologue_box(img: Image.Image) -> tuple[int, int, int, int]:
    """Tight head-and-shoulders window (original Leo)."""
    skin = skin_bbox(img)
    if skin is not None and _area(skin) > 20:
        return _expand_box(skin, img.size, pad_x=0.45, pad_y_top=0.55, pad_y_bot=1.15)
    return _expand_box(subject_bbox(img), img.size, pad_x=0.08, pad_y_top=0.08, pad_y_bot=0.12)


def make_stage(size: tuple[int, int]) -> Image.Image:
    """Dark grid plate used by the original full_* / dual_* loops."""
    w, h = size
    img = Image.new("RGBA", (max(1, w), max(1, h)), STAGE_BG)
    draw = ImageDraw.Draw(img)
    step = max(12, min(w, h) // 12)
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h - 1)], fill=STAGE_GRID, width=1)
    for y in range(0, h, step):
        draw.line([(0, y), (w - 1, y)], fill=STAGE_GRID, width=1)
    return img


def _prepared_head(img: Image.Image, slot: str) -> Image.Image:
    src = img.convert("RGBA")
    side = "right" if slot == "right" else "left"
    if is_closeup(src) or slot == "full":
        if is_closeup(src) or slot != "full":
            return src
        x0, y0, x1, y1 = monologue_box(src)
        return src.crop((x0, y0, x1, y1))
    box = skin_bbox(src) or subject_bbox(src)
    cx = (box[0] + box[2]) / 2
    w = src.width
    crop = src
    if side == "left" and cx > w * 0.55:
        crop = src.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    elif side == "right" and cx < w * 0.45:
        crop = src.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return crop


def _head_box(size: tuple[int, int], slot: str) -> tuple[int, int]:
    w, h = size
    if slot == "full":
        return (max(8, int(w * 0.40)), max(8, int(h * 0.70)))
    return (max(8, int(w * 0.34)), max(8, int(h * 0.56)))


def _slot_center(size: tuple[int, int], slot: str) -> tuple[int, int]:
    w, h = size
    cy = int(h * 0.46)
    if slot == "left":
        return (w // 4, cy)
    if slot == "right":
        return ((3 * w) // 4, cy)
    return (w // 2, cy)


def place_character(canvas: Image.Image, img: Image.Image, slot: str) -> Image.Image:
    """Sit a talking-head on the wide stage (original 736x400 dual/full layout)."""
    slot = str(slot).lower()
    if slot in ("guest",):
        slot = "right"
    elif slot in ("host",):
        slot = "left"
    elif slot not in ("full", "left", "right"):
        slot = "full"
    head = _prepared_head(img, slot)
    fitted = fit_contain(head, _head_box(canvas.size, slot))
    cx, cy = _slot_center(canvas.size, slot)
    x = cx - fitted.width // 2
    y = cy - fitted.height // 2
    canvas.paste(fitted, (x, y), fitted)
    return canvas


def add_nameplate(canvas: Image.Image, text: str, side: str) -> Image.Image:
    """Lower-third bar like the original LEOO / EVEVE plates."""
    label = (text or "").strip()
    if not label:
        return canvas
    w, h = canvas.size
    bar_h = max(18, int(h * 0.10))
    bar_w = max(48, int(w * 0.28))
    y0 = h - bar_h
    if str(side).lower() in ("right", "guest"):
        x0 = w - bar_w - max(4, w // 40)
    else:
        x0 = max(4, w // 40)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([x0, y0, x0 + bar_w, h], fill=(4, 4, 8, 230))
    accent = (120, 200, 255, 255) if side != "right" else (230, 160, 220, 255)
    draw.rectangle([x0, y0, x0 + max(3, bar_w // 24), h], fill=accent)
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None
    draw.text((x0 + 10, y0 + max(2, bar_h // 5)), label.upper(), fill=(240, 240, 244, 255), font=font)
    return canvas


def frame_monologue(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Full-screen talking-head on the original wide stage; do not crop to 16:9."""
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    return place_character(canvas, img, "full")


def frame_half(img: Image.Image, size: tuple[int, int], side: str) -> Image.Image:
    """One side of the original dual stage."""
    side = "right" if str(side).lower() in ("right", "guest") else "left"
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    return place_character(canvas, img, side)


def compose_split_pair(
    left: Image.Image,
    right: Image.Image,
    size: tuple[int, int],
    left_name: str | None = None,
    right_name: str | None = None,
) -> Image.Image:
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    place_character(canvas, left, "left")
    place_character(canvas, right, "right")
    if left_name:
        add_nameplate(canvas, left_name, "left")
    if right_name:
        add_nameplate(canvas, right_name, "right")
    return canvas
