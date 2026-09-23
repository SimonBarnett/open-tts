"""Cartoon stills for new people: described look, transparent plate."""

from __future__ import annotations

import hashlib
import re

from PIL import Image, ImageDraw

CARTOON_STYLE = (
    "Flat 2D cartoon character, thick clean outlines, cel-shaded kids-TV style. "
    "Not photoreal, not a photograph, not 3D, not cinematic. "
    "Head and shoulders, facing the camera, isolated figure. "
    "Solid magenta background hex #FF00FF, no scenery, no floor, no text, no logo."
)

CHROMA = (255, 0, 255)
_COLOR_WORDS = {
    "navy": (30, 50, 110),
    "blue": (50, 90, 180),
    "red": (200, 40, 40),
    "green": (40, 140, 70),
    "pink": (230, 120, 160),
    "black": (32, 32, 38),
    "white": (236, 236, 242),
    "brown": (110, 70, 40),
    "blonde": (220, 190, 90),
    "gold": (210, 170, 50),
    "orange": (220, 120, 40),
    "purple": (110, 60, 160),
    "grey": (120, 124, 130),
    "gray": (120, 124, 130),
    "teal": (20, 140, 150),
    "cyan": (0, 200, 210),
}


def wrap_cartoon_prompt(user: str) -> str:
    body = (user or "").strip() or "friendly studio presenter"
    return f"{CARTOON_STYLE} Character described as: {body}"


_SLOT_HINT = {
    "full": "Full-screen centered talking-head loop.",
    "split": "Half-screen interview: character on the LEFT half only, right half solid magenta.",
    "a": "Mouth shape AH, same character, tiny loop.",
    "e": "Mouth shape EH, same character, tiny loop.",
    "i": "Mouth shape EE, same character, tiny loop.",
    "o": "Mouth shape OH, same character, tiny loop.",
    "u": "Mouth shape OO, same character, tiny loop.",
    "pause": "Resting closed mouth, same character, tiny idle loop.",
    "mbp": "Lips together for M/B/P, same character, tiny loop.",
    "fv": "Lower lip under teeth for F/V, same character, tiny loop.",
    "th": "Tongue at teeth for TH, same character, tiny loop.",
    "l": "Tongue up for L, same character, tiny loop.",
    "sz": "Teeth for S/Z, same character, tiny loop.",
    "sh": "Pushed lips for SH, same character, tiny loop.",
    "surprise": "Surprised cartoon eyes, same character, loop first equals last.",
    "laugh": "Laughing cartoon eyes, same character, loop first equals last.",
    "smile": "Smiling cartoon eyes, same character, loop first equals last.",
    "concern": "Concerned cartoon eyes, same character, loop first equals last.",
    "think": "Thinking cartoon eyes, same character, loop first equals last.",
    "listen": "Attentive listening eyes, same character, loop first equals last.",
}


def wrap_cartoon_video_prompt(user: str, slot: str = "full") -> str:
    body = (user or "").strip() or "friendly studio presenter"
    hint = _SLOT_HINT.get((slot or "full").lower(), "Tiny talking-head viseme loop.")
    return (
        f"{CARTOON_STYLE} "
        "This is ONE VIDEO viseme clip, not a still and not a full set. "
        f"{hint} "
        "Seamless loop — first and last frame are the same pose. "
        f"Character described as: {body}"
    )


def knockout_generated(img: Image.Image) -> Image.Image:
    """Turn chroma / studio white into real alpha. Keeps the cartoon."""
    canvas = img.convert("RGBA")
    pix = canvas.load()
    w, h = canvas.size
    corners = [pix[0, 0], pix[w - 1, 0], pix[0, h - 1], pix[w - 1, h - 1]]
    keyed = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if a == 0:
                continue
            if _is_chroma(r, g, b) or _is_plate(r, g, b) or _near_corner(r, g, b, corners):
                pix[x, y] = (r, g, b, 0)
                keyed += 1
    if keyed < max(32, w * h // 40):
        return canvas
    return canvas


def _is_chroma(r: int, g: int, b: int) -> bool:
    magenta = r > 180 and b > 180 and g < 80
    green = g > 180 and r < 80 and b < 80
    return magenta or green


def _is_plate(r: int, g: int, b: int) -> bool:
    return r > 236 and g > 236 and b > 236


def _near_corner(
    r: int, g: int, b: int, corners: list[tuple[int, ...]], tol: int = 14
) -> bool:
    for cr, cg, cb, *_rest in corners:
        if abs(r - cr) <= tol and abs(g - cg) <= tol and abs(b - cb) <= tol:
            if cr > 200 and cg > 200 and cb > 200:
                return True
            if _is_chroma(cr, cg, cb):
                return True
    return False


def draw_cartoon_still(prompt: str, size: int = 512) -> Image.Image:
    """Offline cartoon of the described person — never a flat color square."""
    look = _look(prompt)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = size // 2, int(size * 0.42)
    head_r = int(size * 0.22)
    # shoulders / jacket
    body = (
        cx - int(size * 0.34),
        cy + int(head_r * 0.85),
        cx + int(size * 0.34),
        size - 8,
    )
    draw.rounded_rectangle(body, radius=36, fill=look["jacket"], outline=(20, 22, 28, 255), width=4)
    # head
    head = (cx - head_r, cy - head_r, cx + head_r, cy + head_r)
    draw.ellipse(head, fill=look["skin"], outline=(20, 22, 28, 255), width=4)
    # hair cap
    hair = (
        cx - head_r,
        cy - head_r - int(head_r * 0.15),
        cx + head_r,
        cy - int(head_r * 0.15),
    )
    draw.pieslice(hair, 180, 360, fill=look["hair"], outline=(20, 22, 28, 255))
    # eyes — white sclera so lip/eye tools can lock on
    eye_r = max(10, head_r // 5)
    for side in (-1, 1):
        ex = cx + side * int(head_r * 0.38)
        ey = cy - int(head_r * 0.08)
        draw.ellipse((ex - eye_r, ey - eye_r, ex + eye_r, ey + eye_r), fill=(232, 237, 251, 255))
        ir = max(4, eye_r // 2)
        draw.ellipse((ex - ir, ey - ir, ex + ir, ey + ir), fill=look["iris"])
        pr = max(2, ir // 2)
        draw.ellipse((ex - pr, ey - pr, ex + pr, ey + pr), fill=(22, 28, 40, 255))
    # smile
    mw = int(head_r * 0.55)
    my = cy + int(head_r * 0.38)
    draw.arc((cx - mw, my - 12, cx + mw, my + 18), 20, 160, fill=(20, 22, 28, 255), width=4)
    return canvas


def _look(prompt: str) -> dict[str, tuple[int, int, int, int]]:
    text = (prompt or "").lower()
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    words = set(re.findall(r"[a-z]+", text))
    jacket = _COLOR_WORDS.get("navy")
    hair = _COLOR_WORDS.get("brown")
    for word, rgb in _COLOR_WORDS.items():
        if word not in words:
            continue
        if word in {"blonde", "brown", "black", "red", "pink", "gold", "orange"}:
            hair = rgb
        if word in {"navy", "blue", "green", "red", "purple", "teal", "grey", "gray", "white"}:
            jacket = rgb
    if jacket is None:
        jacket = (80 + digest[0] % 120, 50 + digest[1] % 80, 90 + digest[2] % 100)
    if hair is None:
        hair = (60 + digest[3] % 100, 40 + digest[4] % 70, 30 + digest[5] % 60)
    iris = (digest[6] % 80, 80 + digest[7] % 140, 140 + digest[8] % 80)
    skin = (232, 196, 164)
    if "robot" in words or "android" in words:
        skin = (46, 49, 60)
        iris = (0, 236, 242) if "leo" in words or "cyan" in words else (255, 168, 205)
    return {
        "jacket": (*jacket[:3], 255),
        "hair": (*hair[:3], 255),
        "iris": (*iris[:3], 255),
        "skin": (*skin[:3], 255),
    }


def opaque_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    rgba = img.convert("RGBA")
    w, h = rgba.size
    pix = rgba.load()
    xs: list[int] = []
    ys: list[int] = []
    step = max(1, min(w, h) // 96)
    for y in range(0, h, step):
        for x in range(0, w, step):
            if pix[x, y][3] > 16:
                xs.append(x)
                ys.append(y)
    if not xs:
        return (0, 0, w, h)
    pad = max(2, step)
    return (
        max(0, min(xs) - pad),
        max(0, min(ys) - pad),
        min(w, max(xs) + pad + 1),
        min(h, max(ys) + pad + 1),
    )

