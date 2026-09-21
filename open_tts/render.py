"""Interview render pipeline."""

from __future__ import annotations

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
from open_tts.video import build_video


def default_output_dir(yaml_path: Path) -> Path:
    return yaml_path.parent / "output" / yaml_path.stem


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

    return out
