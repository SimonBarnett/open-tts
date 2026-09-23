"""Club Madeira widget audio tutorials (*-audiotour.json)."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from open_tts.characters import repo_root

TOUR_GLOB = "*-audiotour.json"
PLACEHOLDER_MARK = "BASE64_PLACEHOLDER"
MIN_REAL_B64 = 200


def list_tours(root: Path | None = None) -> list[Path]:
    base = root or repo_root()
    found = sorted(base.glob(TOUR_GLOB))
    processed = base / "processed"
    if processed.is_dir():
        found.extend(sorted(processed.glob(TOUR_GLOB)))
    seen: set[str] = set()
    out: list[Path] = []
    for path in found:
        key = path.name
        if key in seen:
            continue
        seen.add(key)
        out.append(path.resolve())
    return out


def load_tour(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Tour JSON must be an object: {path}")
    data.setdefault("messages", [])
    return data


def message_text(msg: dict[str, Any]) -> str:
    return str(msg.get("dialog-text") or msg.get("text") or "").strip()


def has_real_audio(msg: dict[str, Any]) -> bool:
    raw = str(msg.get("base64") or "")
    if not raw or raw.startswith(PLACEHOLDER_MARK):
        return False
    return len(raw) >= MIN_REAL_B64


def encode_audio_b64(path: Path) -> str:
    data = path.read_bytes()
    if len(data) < 44:
        raise ValueError(f"Audio file is empty: {path}")
    return base64.b64encode(data).decode("ascii")


def decode_audio_b64(raw: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(base64.b64decode(raw))
    return dest


def apply_take(data: dict[str, Any], index: int, wav_path: Path) -> dict[str, Any]:
    messages = data.get("messages") or []
    if index < 0 or index >= len(messages):
        raise IndexError(f"Tour step {index} is out of range")
    messages[index]["base64"] = encode_audio_b64(wav_path)
    return data


def preferred_tour_file(path: Path, root: Path | None = None) -> Path:
    """Use the processed copy when one exists so recorded takes survive."""
    proc = processed_path(path, root)
    return proc if proc.is_file() else path.resolve()


def processed_path(src: Path, root: Path | None = None) -> Path:
    base = root or src.parent
    if src.parent.name == "processed":
        return src.resolve()
    dest_dir = base / "processed"
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / src.name


def take_wav_path(src: Path, index: int, root: Path | None = None) -> Path:
    base = processed_path(src, root).parent
    folder = base / "tours" / src.stem
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"step_{index:03d}.wav"


def save_processed(src: Path, data: dict[str, Any], root: Path | None = None) -> Path:
    dest = processed_path(src, root)
    payload = dict(data)
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return dest
