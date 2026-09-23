"""On-model cartoon mouths for the Leo/Eve robot loops."""

from __future__ import annotations

from PIL import Image, ImageDraw

from open_tts.sprite import fit_cover

FACE_PLATE = (46, 49, 60, 255)
REST_MOUTHS = frozenset({"pause", "smile", "listen", "attentive"})
WHITE = (255, 255, 255, 255)
RED = (220, 8, 18, 255)

# Cue → rest/talk hint only; speech visemes own lip-sync.
CUE_MOUTH = {
    "surprise": "o",
    "laugh": "a",
    "smile": "pause",
    "concern": "mbp",
    "think": "pause",
    "listen": "pause",
    "attentive": "pause",
    "pause": "pause",
}

# width, height as fractions of inter-pupil distance; tongue; kind.
_VISEME_DRAW = {
    "a": (1.00, 0.46, True, "open"),
    "e": (1.08, 0.30, False, "open"),
    "i": (1.02, 0.20, False, "open"),
    "o": (0.62, 0.48, True, "open"),
    "u": (0.48, 0.34, False, "open"),
    "mbp": (0.90, 0.10, False, "line"),
    "fv": (1.00, 0.22, False, "open"),
    "th": (0.88, 0.28, True, "open"),
    "l": (0.90, 0.34, True, "open"),
    "sz": (0.92, 0.20, False, "open"),
    "sh": (0.70, 0.36, False, "open"),
    "pause": (1.55, 0.28, False, "smile"),
    "smile": (1.55, 0.28, False, "smile"),
}


def mouth_from_cell(cell: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Take the lip region from a viseme still and mask it to an oval."""
    src = cell.convert("RGBA")
    w, h = src.size
    mw = max(8, int(w * 0.44))
    mh = max(6, int(h * 0.24))
    cx, cy = w // 2, int(h * 0.68)
    crop = src.crop((cx - mw // 2, cy - mh // 2, cx + mw // 2, cy + mh // 2))
    patch = fit_cover(crop, size)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse((1, 1, size[0] - 2, size[1] - 2), fill=255)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(patch, (0, 0))
    out.putalpha(mask)
    return out


def cell_is_overlay(cell: Image.Image) -> bool:
    """True when the cell is a transparent mouth stamp, not a full portrait."""
    src = cell.convert("RGBA")
    alpha = src.getchannel("A")
    lo, _hi = alpha.getextrema()
    if lo >= 40:
        return False
    clear = sum(1 for p in alpha.getdata() if p < 40)
    return clear > src.width * src.height * 0.3


def mouth_shape(viseme: str, size: tuple[int, int]) -> Image.Image:
    """Draw a robot-style mouth into a transparent patch (tests + overlays)."""
    w, h = max(8, size[0]), max(6, size[1])
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    key = (viseme or "pause").lower()
    wf = _VISEME_DRAW.get(key, (0.92, 0.34, True, "open"))[0]
    ipd = max(8, int(w / max(wf, 0.4)))
    return paint_cartoon_mouth(out, viseme, (w // 2, h // 2), ipd)


def stamp_mouth(
    frame: Image.Image,
    mouth: Image.Image,
    center: tuple[int, int],
) -> Image.Image:
    canvas = frame.convert("RGBA")
    cx, cy = center
    x = int(cx - mouth.width / 2)
    y = int(cy - mouth.height / 2)
    canvas.paste(mouth, (x, y), mouth)
    return canvas


def paint_cartoon_mouth(
    frame: Image.Image,
    viseme: str,
    center: tuple[int, int],
    ipd: int,
) -> Image.Image:
    """Draw the original-loop mouth (smile arc or white+red capsule)."""
    canvas = frame.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    key = (viseme or "pause").lower()
    wf, hf, tongue, kind = _VISEME_DRAW.get(key, (0.92, 0.34, True, "open"))
    mw = max(8, int(ipd * wf))
    mh = max(4, int(ipd * hf))
    cx, cy = center
    x0, y0 = cx - mw // 2, cy - mh // 2
    x1, y1 = x0 + mw, y0 + mh
    if kind == "smile":
        box = (x0, y0, x1, y1 + mh // 2)
        draw.arc(box, start=20, end=160, fill=WHITE, width=max(3, ipd // 16))
    elif kind == "line":
        draw.line((x0 + 2, cy, x1 - 2, cy), fill=WHITE, width=max(3, ipd // 18))
    else:
        rad = max(2, mh // 2)
        draw.rounded_rectangle((x0, y0, x1, y1), radius=rad, fill=WHITE)
        if tongue and mh > 8:
            inset = max(3, mw // 6)
            ty0 = y0 + int(mh * 0.48)
            draw.rounded_rectangle(
                (x0 + inset, ty0, x1 - inset, y1 - 1),
                radius=max(2, (y1 - ty0) // 2),
                fill=RED,
            )
    return canvas


def erase_native_mouth(
    frame: Image.Image,
    box: tuple[int, int, int, int],
) -> Image.Image:
    """Wipe the loop's smile/teeth/tongue; keep a tight capsule, not a face blob."""
    canvas = frame.convert("RGBA")
    x0, y0, x1, y1 = box
    w, h = canvas.size
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    pix = canvas.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = pix[x, y][:3]
            teeth = r > 145 and g > 145 and b > 145 and (r + g + b) > 460
            tongue = r > 140 and g < 100 and b < 100 and r > g + 40
            if teeth or tongue:
                pix[x, y] = FACE_PLATE
    if bh <= 48 and bw <= 140:
        ImageDraw.Draw(canvas).rounded_rectangle(
            (x0, y0, x1, y1),
            radius=max(2, bh // 2),
            fill=FACE_PLATE,
        )
    return canvas
