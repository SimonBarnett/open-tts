"""Compose interview video from sprite sheets + timings."""

from __future__ import annotations

import shutil
import subprocess
from itertools import groupby
from pathlib import Path

from PIL import Image

from open_tts.audio import media_duration
from open_tts.characters import load_registry, sheet_for
from open_tts.overlays import (
    OverlaySpec,
    SIZE,
    composite_on_background,
    scroll_drawtext,
    title_drawtext,
)
from open_tts.cues import resolve_cue
from open_tts.script import apply_cast_overrides
from open_tts.framing import (
    add_nameplate,
    compose_split_pair,
    frame_monologue,
    knockout_stage,
)
from open_tts.loops import (
    find_eyes,
    find_native_mouth,
    frame_at,
    looped_frames,
    mouth_anchor,
    mouth_from_eyes,
    mouth_size,
    place_character,
    resolve_loop,
    talker_bbox,
)
from open_tts.emotes import apply_emote, emote_for_line
from open_tts.mouth import (
    REST_MOUTHS,
    cell_is_overlay,
    erase_native_mouth,
    mouth_from_cell,
    mouth_shape,
    paint_cartoon_mouth,
    stamp_mouth,
)
from open_tts.sprite import EXPRESSION_COL, CharacterSheet
from open_tts.visemes import phones_for_line, sheet_viseme, viseme_at_time


def run(cmd: list) -> None:
    subprocess.run(cmd, check=True)


def line_is_split(
    line: dict,
    n_lines: int,
    dual_start: int,
    dual_end: int,
    *,
    can_split: bool = True,
) -> bool:
    """Per-utterance split, else intro/outro dual_* defaults. Solo cast stays full."""
    if not can_split:
        return False
    if "split" in line and line["split"] is not None:
        return bool(line["split"])
    screen = str(line.get("screen") or "").strip().lower()
    if screen in ("split", "dual", "both"):
        return True
    if screen in ("full", "solo"):
        return False
    lid = int(line.get("id") or 0)
    if dual_start <= 0 and dual_end <= 0:
        return False
    return (lid <= dual_start) or (lid > n_lines - dual_end)


def merged_speaker_blocks(
    segments: list[dict],
    audio_duration: float,
    dual_start: int,
    dual_end: int,
    left: str | None = None,
    right: str | None = None,
) -> list[dict]:
    n = len(segments)
    staged = apply_cast_overrides(segments, left, right)
    keyed: list[tuple[str, str, str, str, dict]] = []
    for seg in staged:
        pair_ok = bool(seg["_left"] and seg["_right"] and seg["_left"] != seg["_right"])
        mode = (
            "split"
            if line_is_split(seg, n, dual_start, dual_end, can_split=pair_ok)
            else "full"
        )
        keyed.append((seg["speaker"], mode, seg["_left"], seg["_right"], seg))

    merged: list[dict] = []
    groups = []
    for (speaker, mode, left_id, right_id), group in groupby(
        keyed, key=lambda x: (x[0], x[1], x[2], x[3])
    ):
        groups.append((speaker, mode, left_id, right_id, [item[4] for item in group]))

    for i, (speaker, mode, left_id, right_id, group) in enumerate(groups):
        start = group[0]["start"]
        end = groups[i + 1][4][0]["start"] if i + 1 < len(groups) else audio_duration
        merged.append(
            {
                "speaker": speaker,
                "start": start,
                "end": end,
                "duration": end - start,
                "mode": mode,
                "left": left_id,
                "right": right_id,
                "lines": group,
            }
        )
    return merged


_PAUSE_LINE = {"id": 0, "text": "", "cue": "pause"}
_ATTENTIVE_LINE = {"id": 0, "text": "", "cue": "attentive"}


def _frame_for_line(sheet: CharacterSheet, line: dict, t_in_line: float) -> Path:
    cue = resolve_cue(line.get("cue") or "")
    cache_tag: str
    if cue in EXPRESSION_COL:
        frames = looped_frames(sheet.expression_frames(cue))
        idx = int(t_in_line * 8) % len(frames)
        img = frames[idx]
        cache_tag = f"{cue}:{idx}"
    elif cue == "pause":
        img = sheet.pause()
        cache_tag = "pause"
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


def _viseme_image(sheet: CharacterSheet, line: dict, t_in_line: float) -> Image.Image:
    with Image.open(_frame_for_line(sheet, line, t_in_line)) as src:
        return src.convert("RGBA")


def _viseme_key(line: dict, t_in_line: float) -> str:
    """Speech viseme only — emotes do not replace lip-sync."""
    phones = phones_for_line(line)
    return sheet_viseme(viseme_at_time(phones, t_in_line))


def _mouth_patch(
    sheet: CharacterSheet,
    line: dict,
    t_in_line: float,
    size: tuple[int, int],
) -> Image.Image:
    vis = _viseme_key(line, t_in_line)
    with _viseme_image(sheet, line, t_in_line) as cell:
        if cell_is_overlay(cell):
            return mouth_from_cell(cell, size)
    return mouth_shape(vis, size)


def _stamp_talker(
    frame: Image.Image,
    sheet: CharacterSheet,
    line: dict,
    t_in_line: float,
    mode: str,
    speaker: str,
    eyes: tuple[tuple[int, int], tuple[int, int], int] | None = None,
    left_id: str | None = None,
    right_id: str | None = None,
) -> Image.Image:
    vis = _viseme_key(line, t_in_line)
    if vis in REST_MOUTHS:
        return frame
    box = talker_bbox(speaker, mode, frame.size, left_id, right_id)
    found = eyes or find_eyes(frame, box)
    if found:
        native = find_native_mouth(frame, found, box)
        slot = mouth_from_eyes(found, vis, native)
        center = slot["center"]
        size = slot["stamp_size"]
        ipd = found[2]
        frame = erase_native_mouth(frame, slot["erase_box"])
    else:
        center = mouth_anchor(mode, speaker)
        size = mouth_size(mode)
        ipd = max(size)
    if cell_is_overlay(_viseme_image(sheet, line, t_in_line)):
        return stamp_mouth(frame, mouth_from_cell(_viseme_image(sheet, line, t_in_line), size), center)
    return paint_cartoon_mouth(frame, vis, center, ipd)


def _paint_actors(
    frame: Image.Image,
    *,
    speaker: str,
    mode: str,
    line: dict,
    t_in_line: float,
    left_id: str,
    right_id: str,
    sheet: CharacterSheet,
) -> Image.Image:
    talker_box = talker_bbox(speaker, mode, frame.size, left_id, right_id)
    talker_eyes = find_eyes(frame, talker_box)
    emote = emote_for_line(line)
    if emote and talker_eyes:
        frame = apply_emote(frame, emote, t_in_line, talker_box, speaker, talker_eyes)
    if mode == "split":
        other = right_id if str(speaker).lower() == str(left_id).lower() else left_id
        if other and other != speaker:
            other_box = talker_bbox(other, mode, frame.size, left_id, right_id)
            other_eyes = find_eyes(frame, other_box)
            if other_eyes:
                frame = apply_emote(
                    frame, "listen", t_in_line, other_box, other, other_eyes
                )
    return _stamp_talker(
        frame,
        sheet,
        line,
        t_in_line,
        mode,
        speaker,
        eyes=talker_eyes,
        left_id=left_id,
        right_id=right_id,
    )


def _compose_loop_frame(
    *,
    speaker: str,
    mode: str,
    sheet: CharacterSheet,
    line: dict,
    t_in_line: float,
    frame_index: int,
    dest: Path,
    size: tuple[int, int],
    background: Path | None,
    left_id: str,
    right_id: str,
) -> bool:
    pair = {str(left_id).lower(), str(right_id).lower()}
    original_dual = mode == "split" and pair == {"leo", "eve"}
    if mode == "split" and not original_dual:
        left_loop = resolve_loop(left_id, "full")
        right_loop = resolve_loop(right_id, "full")
        if left_loop is None or right_loop is None:
            return False
        with Image.open(frame_at(left_loop, frame_index)) as src_l:
            left = knockout_stage(src_l)
        with Image.open(frame_at(right_loop, frame_index)) as src_r:
            right = knockout_stage(src_r)
        base = Image.new("RGBA", size, (0, 0, 0, 0))
        base.alpha_composite(place_character(left, size, "left"))
        base.alpha_composite(place_character(right, size, "right"))
        left.close()
        right.close()
        base = _paint_actors(
            base,
            speaker=speaker,
            mode=mode,
            line=line,
            t_in_line=t_in_line,
            left_id=left_id,
            right_id=right_id,
            sheet=sheet,
        )
        composite_on_background(base, dest, size, background)
        base.close()
        return True
    loop = resolve_loop(speaker, mode)
    if loop is None:
        return False
    with Image.open(frame_at(loop, frame_index)) as src:
        base = knockout_stage(src)
    if base.size != size:
        base = base.resize(size, Image.Resampling.LANCZOS)
    base = _paint_actors(
        base,
        speaker=speaker,
        mode=mode,
        line=line,
        t_in_line=t_in_line,
        left_id=left_id,
        right_id=right_id,
        sheet=sheet,
    )
    composite_on_background(base, dest, size, background)
    base.close()
    return True


def _compose_split_frame(
    left_path: Path,
    right_path: Path,
    size: tuple[int, int],
    dest: Path,
    background: Path | None = None,
    left_name: str | None = None,
    right_name: str | None = None,
) -> None:
    pair = compose_split_pair(
        Image.open(left_path),
        Image.open(right_path),
        size,
        left_name=left_name,
        right_name=right_name,
    )
    composite_on_background(pair, dest, size, background)


def _compose_full_frame(
    frame_path: Path,
    size: tuple[int, int],
    dest: Path,
    background: Path | None = None,
    label: str | None = None,
) -> None:
    face = frame_monologue(Image.open(frame_path), size)
    if label:
        add_nameplate(face, label, "left")
    composite_on_background(face, dest, size, background)


def render_block_clip(
    block: dict,
    sheets: dict[str, CharacterSheet],
    fps: int,
    size: tuple[int, int],
    out_path: Path,
    host_id: str,
    guest_id: str,
    background: Path | None = None,
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
        left_id = str(block.get("left") or host_id)
        right_id = str(block.get("right") or guest_id)
        if _compose_loop_frame(
            speaker=speaker,
            mode=str(block.get("mode") or "full"),
            sheet=sheet,
            line=line,
            t_in_line=t_line,
            frame_index=fi,
            dest=dest,
            size=size,
            background=background,
            left_id=left_id,
            right_id=right_id,
        ):
            continue
        if block.get("mode") == "split":
            left_sheet = sheets.get(left_id) or sheet
            right_sheet = sheets.get(right_id) or sheet
            if speaker == left_id:
                left_path = _frame_for_line(sheet, line, t_line)
                right_path = _frame_for_line(right_sheet, _ATTENTIVE_LINE, t)
            elif speaker == right_id:
                left_path = _frame_for_line(left_sheet, _ATTENTIVE_LINE, t)
                right_path = _frame_for_line(sheet, line, t_line)
            else:
                left_path = _frame_for_line(left_sheet, _PAUSE_LINE, 0.0)
                right_path = _frame_for_line(right_sheet, _PAUSE_LINE, 0.0)
            _compose_split_frame(
                left_path,
                right_path,
                size,
                dest,
                background,
                left_name=left_id,
                right_name=right_id,
            )
        else:
            frame_path = _frame_for_line(sheet, line, t_line)
            _compose_full_frame(frame_path, size, dest, background, label=speaker)

    encode_alpha_clip(frame_dir / "frame_%06d.png", fps, duration, out_path)
    shutil.rmtree(frame_dir, ignore_errors=True)


def encode_alpha_clip(
    frame_pattern: Path,
    fps: int,
    duration: float,
    out_path: Path,
) -> None:
    """PNG sequence → QuickTime Animation so the background stays transparent."""
    run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frame_pattern),
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "qtrle",
            "-pix_fmt",
            "argb",
            "-an",
            str(out_path),
        ]
    )


def _still_clip(
    dest: Path,
    duration: float,
    size: tuple[int, int],
    vf: str,
    image: Path | None = None,
) -> None:
    w, h = size
    dest = dest.with_suffix(".mov")
    if image is not None and image.is_file():
        run(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(image.resolve()),
                "-t",
                f"{duration:.3f}",
                "-vf",
                f"scale={w}:{h}:flags=lanczos,format=rgba,{vf}",
                "-c:v",
                "qtrle",
                "-pix_fmt",
                "argb",
                "-an",
                str(dest),
            ]
        )
        return
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black@0.0:s={w}x{h}:d={duration:.3f},format=rgba",
            "-vf",
            vf,
            "-c:v",
            "qtrle",
            "-pix_fmt",
            "argb",
            "-an",
            str(dest),
        ]
    )


def _with_silence(clip: Path, dest: Path, duration: float) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(clip.resolve()),
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r=24000:cl=mono:d={duration:.3f}",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(dest),
        ]
    )


def _wrap_title_scroll(
    body: Path, temp: Path, overlays: OverlaySpec | None
) -> Path:
    if overlays is None or not (overlays.has_title or overlays.has_scroll):
        return body
    parts: list[Path] = []
    if overlays.has_title:
        raw = temp / "title.mov"
        _still_clip(
            raw,
            overlays.title_duration,
            SIZE,
            title_drawtext(overlays.title_text or "Interview"),
            overlays.title_image,
        )
        titled = temp / "title_av.mov"
        _with_silence(raw, titled, overlays.title_duration)
        parts.append(titled)
    parts.append(body)
    if overlays.has_scroll:
        raw = temp / "scroll.mov"
        textfile = temp / "scroll.txt"
        textfile.write_text(overlays.scroll_text.strip() + "\n", encoding="utf-8")
        _still_clip(
            raw,
            overlays.scroll_duration,
            SIZE,
            scroll_drawtext(textfile, SIZE[1], overlays.scroll_duration),
        )
        scrolled = temp / "scroll_av.mov"
        _with_silence(raw, scrolled, overlays.scroll_duration)
        parts.append(scrolled)
    listing = temp / "wrap_list.txt"
    listing.write_text(
        "".join(f"file '{p.resolve().as_posix()}'\n" for p in parts),
        encoding="utf-8",
    )
    wrapped = temp / "wrapped.mov"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-c",
            "copy",
            str(wrapped),
        ]
    )
    return wrapped


def mux_final(
    visual: Path,
    audio: Path,
    srt: Path,
    output: Path,
    audio_duration: float,
) -> None:
    # Keep alpha. Burned subtitles would flatten the plate; SRT stays beside the video.
    del srt
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(visual.resolve()),
            "-i",
            str(audio.resolve()),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            f"{audio_duration:.3f}",
            str(output),
        ]
    )


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
    overlays: OverlaySpec | None = None,
) -> None:
    registry = load_registry()
    staged = apply_cast_overrides(segments, host_id, guest_id)
    ids = {host_id, guest_id}
    for seg in staged:
        ids.add(str(seg.get("speaker") or ""))
        ids.add(str(seg.get("_left") or ""))
        ids.add(str(seg.get("_right") or ""))
    sheets: dict[str, CharacterSheet] = {}
    for sp in ids:
        if not sp:
            continue
        try:
            sheets[sp] = sheet_for(sp, registry)
        except KeyError:
            continue

    audio_duration = media_duration(full_audio)
    blocks = merged_speaker_blocks(
        segments, audio_duration, dual_start, dual_end, host_id, guest_id
    )

    temp = output_dir / "_video_segments"
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True)

    clips: list[Path] = []
    for i, block in enumerate(blocks):
        clip = temp / f"seg_{i:02d}.mov"
        render_block_clip(
            block,
            sheets,
            fps=24,
            size=SIZE,
            out_path=clip,
            host_id=host_id,
            guest_id=guest_id,
            background=overlays.background if overlays else None,
        )
        clips.append(clip)

    list_file = temp / "list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    visual = temp / "visual.mov"
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
    body = temp / "body.mov"
    mux_final(visual, full_audio, srt_path, body, audio_duration)
    wrapped = _wrap_title_scroll(body, temp, overlays)
    alpha_out = video_out.with_suffix(".mov")
    shutil.copy2(wrapped, alpha_out)
    flatten_video(alpha_out, video_out.with_suffix(".mp4"))
    shutil.rmtree(temp, ignore_errors=True)
    shutil.rmtree(Path("_frame_cache"), ignore_errors=True)


def flatten_video(src: Path, dest: Path) -> None:
    """Studio-playable H.264 on a black plate; the .mov keeps the alpha."""
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src.resolve()),
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x000000:s={SIZE[0]}x{SIZE[1]}",
            "-filter_complex",
            "[1:v][0:v]overlay=shortest=1:format=auto",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(dest),
        ]
    )
