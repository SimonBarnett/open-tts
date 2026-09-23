"""Shared sprite-sheet layout for all characters (visemes, cues, animations)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from PIL import Image

# Grid contract: 6 columns; same (col, row) for every character sheet.
# Row 0: vowels + pause. Row 1: shared consonant mouths. Row 2: expressions. Row 3+: animation strips.
COLS = 6
VISEME_ROW = 0
CONSONANT_ROW = 1
EXPRESSION_ROW = 2
ANIMATION_START_ROW = 3
ANIMATION_FRAMES = COLS  # six frames across one row per expression

VISEME_COL = {
    "a": 0,
    "e": 1,
    "i": 2,
    "o": 3,
    "u": 4,
    "pause": 5,
}

CONSONANT_VISEME_COL = {
    "mbp": 0,
    "fv": 1,
    "th": 2,
    "l": 3,
    "sz": 4,
    "sh": 5,
}

EXPRESSION_COL = {
    "surprise": 0,
    "laugh": 1,
    "smile": 2,
    "concern": 3,
    "think": 4,
    "listen": 5,
}

SHEET_ROWS = ANIMATION_START_ROW + len(EXPRESSION_COL)

DEFAULT_CELL_PX = 128
# Vowels, consonants, expressions — the viseme-set preview (not animation strips).
PREVIEW_ROWS = 3


def fit_cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Scale so ``img`` covers ``size`` and center-crop. No letterbox."""
    tw, th = size
    src = img.convert("RGBA")
    if tw < 1 or th < 1 or src.width < 1 or src.height < 1:
        return Image.new("RGBA", (max(1, tw), max(1, th)), (0, 0, 0, 0))
    scale = max(tw / src.width, th / src.height)
    nw = max(1, int(round(src.width * scale)))
    nh = max(1, int(round(src.height * scale)))
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, (nw - tw) // 2)
    top = max(0, (nh - th) // 2)
    return resized.crop((left, top, left + tw, top + th))


def fit_contain(
    img: Image.Image,
    size: tuple[int, int],
    fill: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> Image.Image:
    """Scale so ``img`` fits inside ``size``. Keep aspect; do not crop or stretch."""
    tw, th = size
    src = img.convert("RGBA")
    canvas = Image.new("RGBA", (max(1, tw), max(1, th)), fill)
    if tw < 1 or th < 1 or src.width < 1 or src.height < 1:
        return canvas
    scale = min(tw / src.width, th / src.height)
    nw = max(1, int(round(src.width * scale)))
    nh = max(1, int(round(src.height * scale)))
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (tw - nw) // 2
    top = (th - nh) // 2
    canvas.paste(resized, (left, top), resized)
    return canvas


@dataclass(frozen=True)
class Cell:
    col: int
    row: int


class CharacterSheet:
    """Character-agnostic API: visemes and cues resolve to fixed cell indices."""

    def __init__(self, sheet_path: Path, cell_px: int = DEFAULT_CELL_PX):
        self.sheet_path = sheet_path
        self.cell_px = cell_px
        self._image: Image.Image | None = None

    def _load(self) -> Image.Image:
        if self._image is None:
            if not self.sheet_path.is_file():
                raise FileNotFoundError(f"Character sheet not found: {self.sheet_path}")
            self._image = Image.open(self.sheet_path).convert("RGBA")
        return self._image

    def cell(self, col: int, row: int) -> Image.Image:
        img = self._load()
        x0 = col * self.cell_px
        y0 = row * self.cell_px
        return img.crop((x0, y0, x0 + self.cell_px, y0 + self.cell_px))

    def viseme(self, name: str) -> Image.Image:
        key = name.lower()
        if key in CONSONANT_VISEME_COL:
            return self.cell(CONSONANT_VISEME_COL[key], CONSONANT_ROW)
        if key not in VISEME_COL:
            key = "pause"
        return self.cell(VISEME_COL[key], VISEME_ROW)

    def pause(self) -> Image.Image:
        return self.viseme("pause")

    def surprise(self) -> Image.Image:
        return self.cell(EXPRESSION_COL["surprise"], EXPRESSION_ROW)

    def laugh(self) -> Image.Image:
        return self.cell(EXPRESSION_COL["laugh"], EXPRESSION_ROW)

    def smile(self) -> Image.Image:
        return self.cell(EXPRESSION_COL["smile"], EXPRESSION_ROW)

    def concern(self) -> Image.Image:
        return self.cell(EXPRESSION_COL["concern"], EXPRESSION_ROW)

    def think(self) -> Image.Image:
        return self.cell(EXPRESSION_COL["think"], EXPRESSION_ROW)

    def listen(self) -> Image.Image:
        return self.cell(EXPRESSION_COL["listen"], EXPRESSION_ROW)

    def attentive(self) -> Image.Image:
        """Split-screen listener pose (same cell as listen)."""
        return self.listen()

    def expression_frames(self, expression: str) -> list[Image.Image]:
        key = "listen" if expression == "attentive" else expression
        expr_col = EXPRESSION_COL.get(key)
        if expr_col is None:
            return [self.pause()]
        anim_row = ANIMATION_START_ROW + expr_col
        return [self.cell(frame_col, anim_row) for frame_col in range(ANIMATION_FRAMES)]

    @staticmethod
    def viseme_col(name: str) -> int:
        key = name.lower()
        if key in CONSONANT_VISEME_COL:
            return CONSONANT_VISEME_COL[key]
        return VISEME_COL.get(key, VISEME_COL["pause"])


def viseme_sequence_for_text(text: str) -> list[str]:
    """Simple vowel-driven viseme list for a line of speech."""
    vowels = [c for c in text.lower() if c in "aeiou"]
    if not vowels:
        return ["pause"]
    return vowels


def ensure_placeholder_sheet(path: Path, label: str, cell_px: int = DEFAULT_CELL_PX) -> None:
    """Create a minimal valid sheet (vowel, consonant, expression, and animation rows)."""
    expected_w = COLS * cell_px
    expected_h = SHEET_ROWS * cell_px
    if path.is_file():
        with Image.open(path) as existing:
            if existing.width >= expected_w and existing.height >= expected_h:
                return
    path.parent.mkdir(parents=True, exist_ok=True)
    w, h = expected_w, expected_h
    img = Image.new("RGBA", (w, h), (40, 44, 52, 255))
    colors = {
        "a": (220, 80, 80),
        "e": (80, 200, 120),
        "i": (80, 160, 220),
        "o": (220, 180, 60),
        "u": (180, 100, 220),
        "pause": (120, 120, 130),
    }
    for name, col in VISEME_COL.items():
        _fill_cell(img, col, VISEME_ROW, cell_px, colors[name])
    consonant_colors = {
        "mbp": (200, 90, 110),
        "fv": (90, 200, 200),
        "th": (160, 160, 90),
        "l": (140, 110, 200),
        "sz": (110, 200, 140),
        "sh": (200, 140, 200),
    }
    for name, col in CONSONANT_VISEME_COL.items():
        _fill_cell(img, col, CONSONANT_ROW, cell_px, consonant_colors[name])
    expression_colors = {
        "surprise": (255, 200, 80),
        "laugh": (255, 120, 180),
        "smile": (120, 220, 140),
        "concern": (200, 140, 100),
        "think": (140, 160, 240),
        "listen": (180, 200, 220),
    }
    for name, col in EXPRESSION_COL.items():
        _fill_cell(img, col, EXPRESSION_ROW, cell_px, expression_colors[name])
    for expr_col in EXPRESSION_COL.values():
        anim_row = ANIMATION_START_ROW + expr_col
        for col in range(COLS):
            shade = 60 + (anim_row + col) * 8
            _fill_cell(img, col, anim_row, cell_px, (shade, shade + 20, shade + 40))
    _draw_label(img, label, cell_px)
    img.save(path)


def _fill_cell(img: Image.Image, col: int, row: int, cell_px: int, rgb: tuple[int, int, int]) -> None:
    x0, y0 = col * cell_px, row * cell_px
    for y in range(y0, y0 + cell_px):
        for x in range(x0, x0 + cell_px):
            img.putpixel((x, y), (*rgb, 255))


def _draw_label(img: Image.Image, label: str, cell_px: int) -> None:
    # Tiny marker in pause cell — no external font dependency.
    x0 = VISEME_COL["pause"] * cell_px + cell_px // 2
    y0 = VISEME_ROW * cell_px + cell_px // 2
    for dx in range(-4, 5):
        for dy in range(-4, 5):
            if 0 <= x0 + dx < img.width and 0 <= y0 + dy < img.height:
                img.putpixel((x0 + dx, y0 + dy), (255, 255, 255, 255))
