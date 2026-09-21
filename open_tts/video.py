"""Compose interview video from sprite sheets + timings."""

from __future__ import annotations

import shutil
import subprocess
from itertools import groupby
from pathlib import Path

from PIL import Image

from open_tts.audio import media_duration
from open_tts.characters import load_registry, sheet_for
from open_tts.sprite import EXPRESSION_COL, CharacterSheet
from open_tts.visemes import phones_for_line, sheet_viseme, viseme_at_time


def run(cmd: list) -> None:
    subprocess.run(cmd, check=True)


def merged_speaker_blocks(
    segments: list[dict], audio_duration: float, dual_start: int, dual_end: int
) -> list[dict]:
    merged: list[dict] = []
    groups = []
    for speaker, group in groupby(segments, key=lambda x: x["speaker"]):
        groups.append((speaker, list(group)))

    n = len(segments)
    for i, (speaker, group) in enumerate(groups):
        start = group[0]["start"]
        end = groups[i + 1][1][0]["start"] if i + 1 < len(groups) else audio_duration
        first_id = group[0]["id"]
        is_dual = (first_id <= dual_start) or (first_id > n - dual_end)
        merged.append(
            {
                "speaker": speaker,
                "start": start,
                "end": end,
                "duration": end - start,
                "mode": "split" if is_dual else "full",
                "lines": group,
            }
        )
    return merged


_LISTENER_LINE = {"id": 0, "text": "", "cue": "listen"}


def _frame_for_line(sheet: CharacterSheet, line: dict, t_in_line: float) -> Path:
    cue = (line.get("cue") or "").lower()
    cache_tag: str
    if cue in EXPRESSION_COL:
        frames = sheet.expression_frames(cue)
        idx = int(t_in_line * 8) % len(frames)
        img = frames[idx]
        cache_tag = f"{cue}:{idx}"
    elif cue == "pause":
        img = sheet.pause()
        cache_tag = "pause"
    elif cue:
        raise ValueError(f"Unknown cue '{line.get('cue')}'")
    else:
        phones = phones_for_line(line)
        vis = viseme_at_time(phones, t_in_line)
        vis_key = sheet_viseme(vis)
        img = sheet.viseme(vis_key)
        cache_tag = f"{vis_key}:{round(t_in_line, 4)}"
    tmp = Path("_frame_cache")
    tmp.mkdir(exist_ok=True)
    out = tmp / f"f_{hash((line['id'], cache_tag, cue)) & 0xfffffff}.png"
    if not out.is_file():
        img.save(out)
    return out


def _compose_split_frame(
    left_path: Path, right_path: Path, size: tuple[int, int], dest: Path
) -> None:
    w, h = size
    half_w = w // 2
    left = Image.open(left_path).convert("RGBA").resize(
        (half_w, h), Image.Resampling.LANCZOS
    )
    right = Image.open(right_path).convert("RGBA").resize(
        (half_w, h), Image.Resampling.LANCZOS
    )
    canvas = Image.new("RGBA", (w, h))
    canvas.paste(left, (0, 0))
    canvas.paste(right, (half_w, 0))
    canvas.convert("RGB").save(dest)


def render_block_clip(
    block: dict,
    sheets: dict[str, CharacterSheet],
    fps: int,
    size: tuple[int, int],
    out_path: Path,
    host_id: str,
    guest_id: str,
) -> None:
    w, h = size
    duration = block["duration"]
    nframes = max(1, int(duration * fps))
    frame_dir = out_path.parent / f"_frames_{out_path.stem}"
    if frame_dir.exists():
        shutil.rmtree(frame_dir)
    frame_dir.mkdir(parents=True)

    speaker = block["speaker"]
    sheet = sheets[speaker]
    lines = block["lines"]
    line_durations = [ln["duration"] for ln in lines]
    line_starts: list[float] = []
    acc = 0.0
    for d in line_durations:
        line_starts.append(acc)
        acc += d

    for fi in range(nframes):
        t = fi / fps
        line = lines[-1]
        t_line = t
        for j, ln in enumerate(lines):
            if t >= line_starts[j]:
                line = ln
                t_line = t - line_starts[j]
        dest = frame_dir / f"frame_{fi:06d}.png"
        if block.get("mode") == "split":
            if speaker == host_id:
                left_path = _frame_for_line(sheet, line, t_line)
                right_path = _frame_for_line(sheets[guest_id], _LISTENER_LINE, 0.0)
            elif speaker == guest_id:
                left_path = _frame_for_line(sheets[host_id], _LISTENER_LINE, 0.0)
                right_path = _frame_for_line(sheet, line, t_line)
            else:
                left_path = _frame_for_line(sheets[host_id], _LISTENER_LINE, 0.0)
                right_path = _frame_for_line(sheets[guest_id], _LISTENER_LINE, 0.0)
            _compose_split_frame(left_path, right_path, size, dest)
        else:
            frame_path = _frame_for_line(sheet, line, t_line)
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(frame_path),
                    "-vf",
                    f"scale={w}:{h}:flags=lanczos",
                    str(dest),
                ],
                check=True,
                capture_output=True,
            )

    run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frame_dir / "frame_%06d.png"),
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(out_path),
        ]
    )
    shutil.rmtree(frame_dir, ignore_errors=True)


def mux_final(
    visual: Path,
    audio: Path,
    srt: Path,
    output: Path,
    audio_duration: float,
) -> None:
    local_srt = output.parent / "_burn.srt"
    shutil.copy2(srt, local_srt)
    srt_esc = str(local_srt.resolve()).replace("\\", "/").replace(":", "\\:")
    vf = (
        f"subtitles='{srt_esc}':"
        "force_style='FontSize=16,PrimaryColour=&HFFFFFF&,"
        "OutlineColour=&H000000&,BorderStyle=3'"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(visual.resolve()),
            "-i",
            str(audio.resolve()),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            f"{audio_duration:.3f}",
            str(output),
        ]
    )
    local_srt.unlink(missing_ok=True)


def build_video(
    output_dir: Path,
    segments: list[dict],
    full_audio: Path,
    srt_path: Path,
    dual_start: int,
    dual_end: int,
    host_id: str,
    guest_id: str,
    video_out: Path,
) -> None:
    registry = load_registry()
    speakers = {s["speaker"] for s in segments}
    sheets = {sp: sheet_for(sp, registry) for sp in speakers}

    audio_duration = media_duration(full_audio)
    blocks = merged_speaker_blocks(segments, audio_duration, dual_start, dual_end)

    temp = output_dir / "_video_segments"
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True)

    clips: list[Path] = []
    for i, block in enumerate(blocks):
        clip = temp / f"seg_{i:02d}.mp4"
        render_block_clip(
            block,
            sheets,
            fps=24,
            size=(1280, 720),
            out_path=clip,
            host_id=host_id,
            guest_id=guest_id,
        )
        clips.append(clip)

    list_file = temp / "list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    visual = temp / "visual.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(visual),
        ]
    )

    video_out.parent.mkdir(parents=True, exist_ok=True)
    mux_final(visual, full_audio, srt_path, video_out, audio_duration)
    shutil.rmtree(temp, ignore_errors=True)
    shutil.rmtree(Path("_frame_cache"), ignore_errors=True)
