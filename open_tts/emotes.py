"""Cartoon face acting on the Leo/Eve loops — same eye recipe as the source art."""

from __future__ import annotations

from PIL import Image, ImageDraw

from open_tts.cues import resolve_cue
from open_tts.loops import find_eyes
from open_tts.mouth import FACE_PLATE
from open_tts.sprite import ANIMATION_FRAMES, EXPRESSION_COL

EMOTE_FPS = 8
SCLERA = (232, 237, 251, 255)
PUPIL = (22, 28, 40, 255)
IRIS = {
    "leo": (0, 236, 242, 255),
    "eve": (255, 168, 205, 255),
}


def emote_for_line(line: dict) -> str | None:
    cue = resolve_cue(line.get("cue") or "")
    if cue in EXPRESSION_COL:
        return cue
    return None


def emote_phase(t: float) -> int:
    return int(max(0.0, t) * EMOTE_FPS) % ANIMATION_FRAMES


def _base_pose() -> dict:
    return {
        "scale_x": 1.0,
        "scale_y": 1.0,
        "look": (0, 0),
        "bounce": 0,
        "blink": False,
        "happy": False,
        "pupil": 0.38,
    }


def _with(**updates) -> dict:
    pose = _base_pose()
    pose.update(updates)
    return pose


# Six frames; last is a copy of first so the cycle loops without a jump.
_LOOP: dict[str, tuple[dict, ...]] = {
    "surprise": (
        _with(),
        _with(scale_x=1.08, scale_y=1.08, pupil=0.30, look=(0, -1)),
        _with(scale_x=1.22, scale_y=1.22, pupil=0.22, look=(0, -1)),
        _with(scale_x=1.22, scale_y=1.22, pupil=0.22, look=(0, -1)),
        _with(scale_x=1.08, scale_y=1.08, pupil=0.30, look=(0, -1)),
        _with(),
    ),
    "laugh": (
        _with(scale_y=0.86),
        _with(happy=True, bounce=-2, scale_y=0.72),
        _with(happy=True, bounce=2, scale_y=0.72),
        _with(happy=True, bounce=-2, scale_y=0.72),
        _with(happy=True, bounce=1, scale_y=0.78),
        _with(scale_y=0.86),
    ),
    "smile": (
        _with(scale_y=0.92, look=(0, 1)),
        _with(scale_y=0.84, look=(0, 1)),
        _with(scale_y=0.78, happy=True, look=(0, 1)),
        _with(scale_y=0.78, happy=True, look=(0, 1)),
        _with(scale_y=0.84, look=(0, 1)),
        _with(scale_y=0.92, look=(0, 1)),
    ),
    "concern": (
        _with(scale_x=0.96, scale_y=0.94, look=(0, 1), pupil=0.40),
        _with(scale_x=0.94, scale_y=0.90, look=(0, 2), pupil=0.42),
        _with(scale_x=0.92, scale_y=0.86, look=(0, 2), pupil=0.42),
        _with(scale_x=0.92, scale_y=0.86, look=(0, 2), pupil=0.42),
        _with(scale_x=0.94, scale_y=0.90, look=(0, 1), pupil=0.42),
        _with(scale_x=0.96, scale_y=0.94, look=(0, 1), pupil=0.40),
    ),
    "think": (
        _with(look=(1, -1), scale_y=1.02),
        _with(look=(2, -2), scale_y=1.04),
        _with(look=(3, -2), scale_y=1.06),
        _with(look=(3, -2), scale_y=1.06, blink=True),
        _with(look=(2, -1), scale_y=1.04),
        _with(look=(1, -1), scale_y=1.02),
    ),
    "listen": (
        _with(),
        _with(look=(-1, 0)),
        _with(blink=True),
        _with(look=(1, 0)),
        _with(),
        _with(),
    ),
}


def apply_emote(
    frame: Image.Image,
    emote: str,
    t: float,
    bbox: tuple[int, int, int, int],
    speaker: str,
    eyes: tuple[tuple[int, int], tuple[int, int], int] | None = None,
) -> Image.Image:
    """Redraw eyes in the source cartoon language. Mouth stays for lip-sync."""
    key = "listen" if emote == "attentive" else emote
    if key not in EXPRESSION_COL:
        return frame
    found = eyes or find_eyes(frame, bbox)
    if found is None:
        return frame
    left, right, ipd = found
    canvas = frame.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    r = max(6, int(ipd * 0.23))
    phase = emote_phase(t)
    iris = IRIS.get(str(speaker).lower(), IRIS["leo"])
    pose = _pose(key, phase)
    _cover_eyes(draw, left, right, r)
    _eye(draw, left[0], left[1] + pose["bounce"], r, iris, pose, side=-1)
    _eye(draw, right[0], right[1] + pose["bounce"], r, iris, pose, side=1)
    return canvas


def _pose(emote: str, phase: int) -> dict:
    frames = _LOOP.get(emote)
    if not frames:
        return _base_pose()
    return dict(frames[phase % len(frames)])


def _cover_eyes(
    draw: ImageDraw.ImageDraw,
    left: tuple[int, int],
    right: tuple[int, int],
    r: int,
) -> None:
    pad = int(r * 1.25)
    for cx, cy in (left, right):
        draw.ellipse((cx - pad, cy - pad, cx + pad, cy + pad), fill=FACE_PLATE)


def _eye(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    r: int,
    iris: tuple[int, int, int, int],
    pose: dict,
    side: int,
) -> None:
    rx = max(4, int(r * pose["scale_x"]))
    ry = max(4, int(r * pose["scale_y"]))
    if pose["blink"]:
        draw.line((cx - rx, cy, cx + rx, cy), fill=SCLERA, width=max(3, r // 3))
        return
    if pose["happy"]:
        box = (cx - rx, cy - ry // 2, cx + rx, cy + ry)
        draw.arc(box, start=200, end=340, fill=SCLERA, width=max(3, r // 3))
        return
    draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=SCLERA)
    ox, oy = pose["look"]
    irx = max(3, int(rx * 0.62))
    iry = max(3, int(ry * 0.62))
    draw.ellipse(
        (cx + ox - irx, cy + oy - iry, cx + ox + irx, cy + oy + iry),
        fill=iris,
    )
    pr = max(2, int(min(irx, iry) * pose["pupil"] / 0.38 * 0.45))
    draw.ellipse((cx + ox - pr, cy + oy - pr, cx + ox + pr, cy + oy + pr), fill=PUPIL)
    hx, hy = cx + ox - pr, cy + oy - pr
    draw.ellipse((hx - 1, hy - 1, hx + 1, hy + 1), fill=SCLERA)
