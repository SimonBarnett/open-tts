"""Tiny full/dual talking-head loops that viseme mouths are stamped onto."""

from __future__ import annotations

import math
import subprocess
from collections import defaultdict
from pathlib import Path

from PIL import Image

from open_tts.cartoon import opaque_bbox
from open_tts.characters import repo_root
from open_tts.overlays import SIZE
from open_tts.sprite import (
    CONSONANT_VISEME_COL,
    EXPRESSION_COL,
    VISEME_COL,
    fit_contain,
)

LOOP_FILES = {
    ("leo", "full"): "full_leo_talking.mp4",
    ("eve", "full"): "full_eve_talking.mp4",
    ("leo", "split"): "dual_leo_talking_eve_idle.mp4",
    ("eve", "split"): "dual_eve_talking_leo_idle.mp4",
}

# Mouth centres on the 736x400 original loops (full vs left/right dual).
MOUTH_ANCHOR = {
    ("full", "leo"): (368, 202),
    ("full", "eve"): (368, 202),
    ("split", "leo"): (190, 180),
    ("split", "eve"): (552, 185),
}

MOUTH_SIZE = {
    "full": (56, 40),
    "split": (44, 32),
}


def loop_search_roots(root: Path | None = None) -> list[Path]:
    base = root or repo_root()
    return [
        base / "characters" / "loops",
        Path("M:/open-tts"),
        base,
    ]


def custom_loop_name(speaker: str, mode: str) -> str:
    kind = "dual" if mode == "split" else "full"
    return f"{kind}_{str(speaker).lower()}_talking.mp4"


def clip_slots() -> list[tuple[str, str]]:
    """Independent VIDEO visemes — update one without regenerating the set."""
    slots = [("full", "Full talking"), ("split", "Split talking")]
    slots.extend((name, f"Mouth {name}") for name in VISEME_COL)
    slots.extend((name, f"Mouth {name}") for name in CONSONANT_VISEME_COL)
    slots.extend((name, f"Emote {name}") for name in EXPRESSION_COL)
    return slots


def clip_filename(speaker: str, slot: str) -> str:
    who = str(speaker).lower()
    key = (slot or "full").lower()
    if key in {"full", "split"}:
        return custom_loop_name(who, key)
    return f"{key}_{who}.mp4"


def clip_side(slot: str) -> str:
    return "left" if slot == "split" else "full"


def resolve_clip(
    speaker: str,
    slot: str,
    root: Path | None = None,
) -> Path | None:
    """Exact clip file only — no fallback to a different slot."""
    base = root or repo_root()
    name = clip_filename(speaker, slot or "full")
    local = [base / "characters" / "loops", base]
    for folder in local:
        path = folder / name
        if path.is_file() and path.stat().st_size > 1000:
            return path.resolve()
        cache = loop_frame_cache(path, base)
        if any(cache.glob("frame_*.png")):
            return path
    key = (slot or "full").lower()
    if key in {"full", "split"}:
        stock = LOOP_FILES.get((str(speaker).lower(), key))
        if stock:
            for folder in loop_search_roots(root):
                path = folder / stock
                if path.is_file() and path.stat().st_size > 1000:
                    return path.resolve()
    return None


def list_character_clips(
    speaker: str,
    root: Path | None = None,
) -> list[dict]:
    out = []
    for slot, label in clip_slots():
        path = resolve_clip(speaker, slot, root)
        out.append(
            {
                "slot": slot,
                "label": label,
                "path": path,
                "ready": path is not None,
            }
        )
    return out


def resolve_loop(
    speaker: str,
    mode: str,
    root: Path | None = None,
) -> Path | None:
    speaker = str(speaker).lower()
    kind = "split" if mode == "split" else "full"
    names = []
    stock = LOOP_FILES.get((speaker, kind))
    if stock:
        names.append(stock)
    names.append(custom_loop_name(speaker, kind))
    if kind == "split":
        names.append(custom_loop_name(speaker, "full"))
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        for folder in loop_search_roots(root):
            path = folder / name
            if path.is_file() and path.stat().st_size > 1000:
                return path.resolve()
            cache = loop_frame_cache(path, root)
            if any(cache.glob("frame_*.png")):
                return path
    return None


def loops_available(root: Path | None = None) -> bool:
    return all(
        resolve_loop(speaker, mode, root) is not None
        for speaker, mode in LOOP_FILES
    )


def mouth_anchor(mode: str, speaker: str) -> tuple[int, int]:
    key = ("split" if mode == "split" else "full", str(speaker).lower())
    return MOUTH_ANCHOR.get(key, MOUTH_ANCHOR[("full", "leo")])


def mouth_size(mode: str) -> tuple[int, int]:
    return MOUTH_SIZE["split" if mode == "split" else "full"]


def talker_bbox(
    speaker: str,
    mode: str,
    size: tuple[int, int],
    left_id: str | None = None,
    right_id: str | None = None,
) -> tuple[int, int, int, int]:
    w, h = size
    if mode != "split":
        return (0, 0, w, h)
    who = str(speaker).lower()
    if right_id and who == str(right_id).lower():
        return (w // 2, 0, w, h)
    if left_id and who == str(left_id).lower():
        return (0, 0, w // 2, h)
    if who == "eve":
        return (w // 2, 0, w, h)
    return (0, 0, w // 2, h)


def _is_white(rgb: tuple[int, ...]) -> bool:
    r, g, b = rgb[:3]
    return r > 190 and g > 200 and b > 210


def _is_face(rgb: tuple[int, ...]) -> bool:
    r, g, b = rgb[:3]
    return 28 <= r <= 80 and 30 <= g <= 90 and 40 <= b <= 110 and abs(r - g) < 25


def find_eyes(
    frame: Image.Image,
    bbox: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int], tuple[int, int], int] | None:
    """Two eye centres and inter-pupil distance on a robot loop frame."""
    rgb = frame.convert("RGB")
    w, h = rgb.size
    x0, y0, x1, y1 = bbox or (0, 0, w, h)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    pix = rgb.load()
    pts: list[tuple[int, int]] = []
    for y in range(y0 + 8, max(y0 + 9, y1 - 8)):
        for x in range(x0 + 8, max(x0 + 9, x1 - 8)):
            if not _is_white(pix[x, y]):
                continue
            dirs = 0
            for dx, dy in ((0, -5), (0, 5), (-5, 0), (5, 0), (0, -8), (0, 8)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < h and _is_face(pix[xx, yy]):
                    dirs += 1
            if dirs >= 2:
                pts.append((x, y))
    clusters = _proximity_clusters(pts, gap=12)
    best = None
    for i, a in enumerate(clusters[:8]):
        for b in clusters[i + 1 : 8]:
            ca = _centroid(a)
            cb = _centroid(b)
            if ca[0] > cb[0]:
                ca, cb = cb, ca
            ipd = cb[0] - ca[0]
            dy = abs(ca[1] - cb[1])
            if ipd < 28 or ipd > 120 or dy > 28:
                continue
            score = len(a) + len(b) - dy
            if best is None or score > best[0]:
                best = (score, (int(ca[0]), int(ca[1])), (int(cb[0]), int(cb[1])), int(ipd))
    if best is None:
        return _eyes_from_silhouette(frame, (x0, y0, x1, y1))
    return best[1], best[2], best[3]


def _eyes_from_silhouette(
    frame: Image.Image,
    bbox: tuple[int, int, int, int],
) -> tuple[tuple[int, int], tuple[int, int], int] | None:
    """Guess eye centres on a custom cartoon when the robot detector misses."""
    x0, y0, x1, y1 = opaque_bbox(frame.crop(bbox))
    x0 += bbox[0]
    x1 += bbox[0]
    y0 += bbox[1]
    y1 += bbox[1]
    w, h = x1 - x0, y1 - y0
    if w < 24 or h < 24:
        return None
    eye_y = y0 + int(h * 0.32)
    left = (x0 + int(w * 0.32), eye_y)
    right = (x0 + int(w * 0.68), eye_y)
    ipd = right[0] - left[0]
    if ipd < 16:
        return None
    return left, right, ipd


def _is_mouth_pixel(rgb: tuple[int, ...]) -> bool:
    r, g, b = rgb[:3]
    if r > 150 and g > 150 and b > 150 and (r + g + b) > 480:
        return True
    return r > 140 and g < 100 and b < 100 and r > g + 40


def find_native_mouth(
    frame: Image.Image,
    eyes: tuple[tuple[int, int], tuple[int, int], int],
    bbox: tuple[int, int, int, int] | None = None,
) -> tuple[int, int, int, int] | None:
    """Bounding box of the loop's own smile/open, below the eyes."""
    rgb = frame.convert("RGB")
    w, h = rgb.size
    left, right, ipd = eyes
    cx = (left[0] + right[0]) // 2
    eye_y = (left[1] + right[1]) // 2
    x0, y0, x1, y1 = bbox or (0, 0, w, h)
    x0 = max(x0, cx - int(ipd * 1.15))
    x1 = min(x1, cx + int(ipd * 1.15))
    y0 = max(y0, eye_y + max(5, int(ipd * 0.16)))
    y1 = min(y1, eye_y + int(ipd * 1.55))
    pix = rgb.load()
    eye_r2 = max(64, int((ipd * 0.40) ** 2))
    xs: list[int] = []
    ys: list[int] = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if not _is_mouth_pixel(pix[x, y]):
                continue
            if (x - left[0]) ** 2 + (y - left[1]) ** 2 < eye_r2:
                continue
            if (x - right[0]) ** 2 + (y - right[1]) ** 2 < eye_r2:
                continue
            xs.append(x)
            ys.append(y)
    if len(xs) < 8:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def mouth_from_eyes(
    eyes: tuple[tuple[int, int], tuple[int, int], int],
    viseme: str = "pause",
    native: tuple[int, int, int, int] | None = None,
) -> dict:
    """Stamp size/centre from the loop mouth slot, else an eye-relative fallback."""
    left, right, ipd = eyes
    cx = (left[0] + right[0]) // 2
    eye_y = (left[1] + right[1]) // 2
    key = (viseme or "pause").lower()
    openish = key in {"a", "o", "u", "e", "l", "sh", "th"}
    if native:
        nx0, ny0, nx1, ny1 = native
        cx = (nx0 + nx1) // 2
        cy = (ny0 + ny1) // 2
        nw, nh = max(8, nx1 - nx0), max(6, ny1 - ny0)
        if openish:
            stamp = (max(nw + 8, int(ipd * 0.95)), max(nh + 6, int(ipd * 0.42)))
        elif key in {"i", "sz", "fv"}:
            stamp = (max(int(ipd * 1.05), nw), max(10, int(ipd * 0.32)))
        else:
            stamp = (max(int(ipd * 1.50), nw), max(10, int(ipd * 0.32)))
        erase = (nx0 - 2, ny0 - 2, nx1 + 2, ny1 + 4)
    else:
        if openish:
            stamp = (max(14, int(ipd * 1.00)), max(12, int(ipd * 0.55)))
            cy = eye_y + int(ipd * 0.38)
        elif key in {"i", "sz", "fv"}:
            stamp = (max(14, int(ipd * 1.20)), max(10, int(ipd * 0.36)))
            cy = eye_y + int(ipd * 0.34)
        else:
            stamp = (max(16, int(ipd * 1.55)), max(10, int(ipd * 0.34)))
            cy = eye_y + int(ipd * 0.30)
        erase = (
            cx - int(ipd * 0.90),
            eye_y + int(ipd * 0.20),
            cx + int(ipd * 0.90),
            eye_y + int(ipd * 0.72),
        )
    return {"center": (cx, cy), "stamp_size": stamp, "erase_box": erase}


def _centroid(pts: list[tuple[int, int]]) -> tuple[float, float]:
    return (
        sum(p[0] for p in pts) / len(pts),
        sum(p[1] for p in pts) / len(pts),
    )


def _proximity_clusters(
    pts: list[tuple[int, int]],
    gap: int = 12,
) -> list[list[tuple[int, int]]]:
    if not pts:
        return []
    grid: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i, (x, y) in enumerate(pts):
        grid[(x // gap, y // gap)].append(i)
    used = [False] * len(pts)
    out: list[list[tuple[int, int]]] = []

    def neighbours(i: int):
        x, y = pts[i]
        gx, gy = x // gap, y // gap
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                for j in grid[(gx + ox, gy + oy)]:
                    if used[j]:
                        continue
                    dx = pts[j][0] - x
                    dy = pts[j][1] - y
                    if dx * dx + dy * dy <= gap * gap:
                        yield j

    for i in range(len(pts)):
        if used[i]:
            continue
        stack = [i]
        used[i] = True
        cluster = []
        while stack:
            k = stack.pop()
            cluster.append(pts[k])
            for j in neighbours(k):
                used[j] = True
                stack.append(j)
        out.append(cluster)
    out.sort(key=len, reverse=True)
    return out


def extract_loop_frames(video: Path, dest_dir: Path) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(dest_dir.glob("frame_*.png"))
    if existing:
        return existing
    if not video.is_file():
        return []
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video.resolve()),
            str(dest_dir / "frame_%04d.png"),
        ],
        check=True,
        capture_output=True,
    )
    return sorted(dest_dir.glob("frame_*.png"))


def loop_frame_cache(video: Path, root: Path | None = None) -> Path:
    base = root or repo_root()
    return base / "characters" / "loops" / "_frames" / video.stem


def looped_frames(frames: list) -> list:
    """Playable strip: last frame is the first, so the cycle does not jump."""
    if len(frames) < 2:
        return list(frames)
    return [*frames[:-1], frames[0]]


def frame_at(video: Path, index: int, root: Path | None = None) -> Path:
    frames = extract_loop_frames(video, loop_frame_cache(video, root))
    if not frames:
        raise FileNotFoundError(f"No frames from {video}")
    playable = looped_frames(frames)
    return playable[index % len(playable)]


LOOP_FRAME_COUNT = 24


def place_character(
    src: Image.Image,
    size: tuple[int, int] = SIZE,
    side: str = "full",
    bounce: int = 0,
) -> Image.Image:
    """Sit the opaque cartoon on a transparent 736×400 plate."""
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    crop = src.convert("RGBA").crop(opaque_bbox(src))
    if side == "left":
        box = (max(8, size[0] // 2 - 12), int(size[1] * 0.94))
        origin_x = 8
    elif side == "right":
        box = (max(8, size[0] // 2 - 12), int(size[1] * 0.94))
        origin_x = size[0] // 2 + 4
    else:
        box = (int(size[0] * 0.58), int(size[1] * 0.94))
        origin_x = None
    placed = fit_contain(crop, box)
    x = (size[0] - placed.width) // 2 if origin_x is None else origin_x
    y = size[1] - placed.height + bounce
    canvas.alpha_composite(placed, (max(0, x), max(0, y)))
    return canvas


def build_viseme_loops(
    hero: Path,
    character_id: str,
    root: Path | None = None,
    frames: int = LOOP_FRAME_COUNT,
) -> dict[str, Path]:
    """Tiny looping VIDEO visemes from the cartoon still. First frame == last."""
    base = root or repo_root()
    hero_img = Image.open(hero).convert("RGBA")
    safe = "".join(ch for ch in character_id.lower() if ch.isalnum() or ch in "-_")
    out: dict[str, Path] = {}
    for mode, side in (("full", "full"), ("split", "left")):
        dest = (base / "characters" / "loops" / custom_loop_name(safe, mode))
        dest.parent.mkdir(parents=True, exist_ok=True)
        cache = loop_frame_cache(dest, base)
        if cache.exists():
            for old in cache.glob("frame_*.png"):
                old.unlink()
        cache.mkdir(parents=True, exist_ok=True)
        n = max(2, frames)
        written: list[Path] = []
        for i in range(n):
            bounce = 0 if i in (0, n - 1) else int(round(3 * math.sin(2 * math.pi * i / (n - 1))))
            frame = place_character(hero_img, SIZE, side, bounce)
            path = cache / f"frame_{i + 1:04d}.png"
            frame.save(path)
            written.append(path)
        if written:
            # last image is the first so the cycle does not jump
            Image.open(written[0]).save(written[-1])
        _encode_loop_mp4(cache, dest)
        out[mode] = dest
    hero_img.close()
    return out


def install_generated_video(
    src: Path,
    character_id: str,
    root: Path | None = None,
    slots: list[str] | None = None,
) -> dict[str, Path]:
    """Install one (or more) VIDEO viseme clips. Default: only the named slot."""
    from open_tts.cartoon import knockout_generated

    wanted = [str(s).lower() for s in (slots or ("full",))]
    base = root or repo_root()
    safe = "".join(ch for ch in character_id.lower() if ch.isalnum() or ch in "-_")
    work = base / "characters" / "loops" / "_work" / f"{safe}_{wanted[0]}"
    if work.exists():
        for old in work.glob("frame_*.png"):
            old.unlink()
    raw = extract_loop_frames(src, work)
    if not raw:
        raise FileNotFoundError(f"Generated video had no frames: {src}")
    plates: list[Image.Image] = []
    for path in raw:
        with Image.open(path) as src_im:
            plates.append(place_character(knockout_generated(src_im), SIZE, "full"))
    if plates:
        plates[-1] = plates[0].copy()
    out: dict[str, Path] = {}
    for slot in wanted:
        side = clip_side(slot)
        dest = base / "characters" / "loops" / clip_filename(safe, slot)
        dest.parent.mkdir(parents=True, exist_ok=True)
        cache = loop_frame_cache(dest, base)
        if cache.exists():
            for old in cache.glob("frame_*.png"):
                old.unlink()
        cache.mkdir(parents=True, exist_ok=True)
        for i, plate in enumerate(plates):
            frame = plate if side == "full" else place_character(plate, SIZE, side)
            frame.save(cache / f"frame_{i + 1:04d}.png")
        _encode_loop_mp4(cache, dest)
        out[slot] = dest
    for plate in plates:
        plate.close()
    return out


def _encode_loop_mp4(frame_dir: Path, dest: Path) -> None:
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                "24",
                "-i",
                str(frame_dir / "frame_%04d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-an",
                str(dest),
            ],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return
