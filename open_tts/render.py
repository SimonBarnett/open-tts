"""Interview render pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path

from open_tts.audio import (
    MAX_SRT_AUDIO_DRIFT_SEC,
    build_full_interview,
    check_caption_drift,
    decode_to_wav,
    export_mp3_from_wav,
    write_timings,
)
from open_tts.characters import load_registry, voice_for
from open_tts.script import layout_options, load_interview, normalized_lines
from open_tts.srt import write_srt
from open_tts.tts import ensure_sentence_audio
from open_tts.project import (
    default_output_dir,
    interview_yaml_in_project,
    is_project_directory,
    touch_last_render,
)
from open_tts.video import build_video


def sentence_audio_paths(output_dir: Path, speaker: str, line_index: int) -> tuple[Path, Path]:
    """1-based line_index → (mp3, wav) under output_dir/sentences."""
    speech_dir = output_dir / "sentences"
    stem = f"{speaker}_{line_index:03d}"
    return speech_dir / f"{stem}.mp3", speech_dir / f"{stem}.wav"


def invalidate_sentence_audio(
    output_dir: Path, line_index: int, *speakers: str
) -> None:
    """Remove cached sentence audio for 1-based line_index (all speakers given)."""
    for sp in speakers:
        mp3, wav = sentence_audio_paths(output_dir, sp, line_index)
        mp3.unlink(missing_ok=True)
        wav.unlink(missing_ok=True)


def render_interview(
    yaml_path: Path,
    output_dir: Path | None = None,
    skip_tts: bool = False,
    video: bool = True,
    check_only: bool = False,
) -> Path:
    data = load_interview(yaml_path)
    lines = normalized_lines(data)
    layout = layout_options(data)
    out = output_dir or default_output_dir(yaml_path)
    out.mkdir(parents=True, exist_ok=True)

    registry = load_registry()
    speech_dir = out / "sentences"
    speech_dir.mkdir(parents=True, exist_ok=True)

    speech_wavs: list[Path] = []
    for i, line in enumerate(lines, 1):
        sp = line["speaker"]
        mp3 = speech_dir / f"{sp}_{i:03d}.mp3"
        wav = speech_dir / f"{sp}_{i:03d}.wav"
        voice = voice_for(sp, registry)
        ensure_sentence_audio(line["text"], voice, mp3, skip_tts=skip_tts)
        if not wav.is_file() or wav.stat().st_mtime < mp3.stat().st_mtime:
            decode_to_wav(mp3, wav)
        line["file"] = mp3.name
        speech_wavs.append(wav)

    work = out / "_work"
    full_wav, segments = build_full_interview(lines, work, speech_wavs)
    full_wav_out = out / "full_interview.wav"
    shutil.copy2(full_wav, full_wav_out)
    full_mp3 = out / "full_interview.mp3"
    export_mp3_from_wav(full_wav, full_mp3)

    timings_path = out / "timings.json"
    write_timings(timings_path, segments)

    srt_path = out / "interview.srt"
    write_srt(srt_path, segments)

    drift = check_caption_drift(segments, lines, full_wav)
    if drift > MAX_SRT_AUDIO_DRIFT_SEC:
        raise RuntimeError(
            f"Caption drift {drift * 1000:.1f} ms exceeds "
            f"{MAX_SRT_AUDIO_DRIFT_SEC * 1000:.0f} ms budget"
        )

    if check_only:
        return out

    if video:
        video_out = out / "interview.mp4"
        build_video(
            out,
            segments,
            full_wav,
            srt_path,
            layout["dual_start_turns"],
            layout["dual_end_turns"],
            str(layout["host"]),
            str(layout["guest"]),
            video_out,
        )

    if interview_yaml_in_project(yaml_path) and is_project_directory(out):
        touch_last_render(out)

    return out


def render_line(
    yaml_path: Path,
    output_dir: Path | None,
    line_id: int,
    *,
    previous_speaker: str | None = None,
) -> Path:
    """Re-render after a single-line edit (sentence cache cleared on Save when text/speaker change)."""
    out = output_dir or default_output_dir(yaml_path)
    data = load_interview(yaml_path)
    lines = normalized_lines(data)
    if line_id < 1 or line_id > len(lines):
        raise ValueError(f"Invalid line id {line_id}")
    if previous_speaker:
        line = lines[line_id - 1]
        if previous_speaker != line["speaker"]:
            invalidate_sentence_audio(out, line_id, previous_speaker, line["speaker"])
    return render_interview(yaml_path, output_dir=out, skip_tts=False, video=True)


def render_cues_only(yaml_path: Path, output_dir: Path | None = None) -> Path:
    return render_interview(
        yaml_path, output_dir=output_dir, skip_tts=True, video=True
    )


def render_full(yaml_path: Path, output_dir: Path | None = None) -> Path:
    return render_interview(
        yaml_path, output_dir=output_dir, skip_tts=False, video=True
    )
