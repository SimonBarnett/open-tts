"""Sample-accurate WAV concat and timeline derivation."""

from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path

SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2  # 16-bit PCM
CHANNELS = 1

PAUSE_BETWEEN_SPEAKERS_MS = 950
PAUSE_BETWEEN_SENTENCES_MS = 350

MAX_SRT_AUDIO_DRIFT_SEC = 0.030


def media_duration(path: Path) -> float:
    if path.suffix.lower() == ".wav":
        return wav_duration_seconds(path)
    return ffprobe_duration(path)


def ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path.resolve()),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def decode_to_wav(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src.resolve()),
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            str(CHANNELS),
            "-sample_fmt",
            "s16",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )


def write_silence_wav(path: Path, duration_ms: int) -> None:
    nframes = int(SAMPLE_RATE * duration_ms / 1000)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"\x00\x00" * nframes)


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def concat_wavs(paths: list[Path], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dest), "wb") as out:
        out.setnchannels(CHANNELS)
        out.setsampwidth(SAMPLE_WIDTH)
        out.setframerate(SAMPLE_RATE)
        for p in paths:
            with wave.open(str(p), "rb") as wf:
                if (
                    wf.getnchannels() != CHANNELS
                    or wf.getsampwidth() != SAMPLE_WIDTH
                    or wf.getframerate() != SAMPLE_RATE
                ):
                    raise ValueError(f"Incompatible WAV format: {p}")
                out.writeframes(wf.readframes(wf.getnframes()))


def export_mp3_from_wav(wav_path: Path, mp3_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(wav_path.resolve()),
            "-codec:a",
            "libmp3lame",
            "-qscale:a",
            "2",
            str(mp3_path),
        ],
        check=True,
        capture_output=True,
    )


def pause_ms_between(prev_speaker: str, next_speaker: str) -> int:
    if prev_speaker == next_speaker:
        return PAUSE_BETWEEN_SENTENCES_MS
    return PAUSE_BETWEEN_SPEAKERS_MS


def build_full_interview(
    lines: list[dict],
    work_dir: Path,
    speech_wavs: list[Path],
) -> tuple[Path, list[dict]]:
    """
    Concatenate sentence WAVs + exact PCM silences.
    Returns (full_interview.wav, timings segments with start/end from the merge).
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    silence_short = work_dir / "_silence_short.wav"
    silence_long = work_dir / "_silence_long.wav"
    write_silence_wav(silence_short, PAUSE_BETWEEN_SENTENCES_MS)
    write_silence_wav(silence_long, PAUSE_BETWEEN_SPEAKERS_MS)

    concat_list: list[Path] = []
    segments: list[dict] = []
    cursor_sec = 0.0

    for i, line in enumerate(lines):
        wav = speech_wavs[i]
        dur = wav_duration_seconds(wav)
        start = cursor_sec
        end = start + dur
        segments.append(
            {
                "id": i + 1,
                "speaker": line["speaker"],
                "text": line["text"],
                "file": line.get("file", wav.name),
                "start": round(start, 6),
                "end": round(end, 6),
                "duration": round(dur, 6),
                "cue": line.get("cue"),
            }
        )
        concat_list.append(wav)
        cursor_sec = end
        if i + 1 < len(lines):
            pause = pause_ms_between(line["speaker"], lines[i + 1]["speaker"])
            gap = silence_short if pause == PAUSE_BETWEEN_SENTENCES_MS else silence_long
            concat_list.append(gap)
            cursor_sec += pause / 1000.0

    full_wav = work_dir / "full_interview.wav"
    concat_wavs(concat_list, full_wav)
    return full_wav, segments


def write_timings(path: Path, segments: list[dict]) -> None:
    path.write_text(json.dumps(segments, indent=2), encoding="utf-8")


def expected_full_duration(segments: list[dict], lines: list[dict]) -> float:
    """Merged length: last speech end (starts already include inter-line pauses)."""
    if not segments:
        return 0.0
    return float(segments[-1]["end"])


def check_caption_drift(
    segments: list[dict], lines: list[dict], audio_path: Path
) -> float:
    """Return |expected merge length − decoded audio length| in seconds."""
    expected = expected_full_duration(segments, lines)
    audio_dur = media_duration(audio_path)
    return abs(audio_dur - expected)
