"""SRT helpers with millisecond-safe formatting."""

from __future__ import annotations

from pathlib import Path


def format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp; milliseconds never reach 1000."""
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000.0))
    h = total_ms // 3_600_000
    rem = total_ms % 3_600_000
    m = rem // 60_000
    rem %= 60_000
    s = rem // 1000
    ms = rem % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(path: Path, segments: list[dict]) -> None:
    lines: list[str] = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(
            f"{format_srt_time(seg['start'])} --> {format_srt_time(seg['end'])}"
        )
        lines.append(seg["text"])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def last_end_seconds(segments: list[dict]) -> float:
    if not segments:
        return 0.0
    return float(segments[-1]["end"])
