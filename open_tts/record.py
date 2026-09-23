"""Save a microphone take onto a sentence slot for digital-tool audio."""

from __future__ import annotations

import wave
from pathlib import Path

from open_tts.audio import (
    CHANNELS,
    SAMPLE_RATE,
    SAMPLE_WIDTH,
    decode_to_wav,
    export_mp3_from_wav,
)
from open_tts.project import default_output_dir
from open_tts.render import sentence_audio_paths


def write_pcm_wav(
    path: Path,
    frames: bytes,
    *,
    sample_rate: int = SAMPLE_RATE,
    channels: int = CHANNELS,
    sample_width: int = SAMPLE_WIDTH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)
    return path


def save_line_recording(
    src: Path,
    output_dir: Path,
    speaker: str,
    line_index: int,
) -> tuple[Path, Path]:
    """Copy a take into sentences/<speaker>_NNN.wav and .mp3."""
    if not src.is_file() or src.stat().st_size < 44:
        raise ValueError(f"Recording is empty: {src}")
    mp3, wav = sentence_audio_paths(output_dir, speaker, line_index)
    wav.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".wav":
        try:
            with wave.open(str(src), "rb") as wf:
                match = (
                    wf.getnchannels() == CHANNELS
                    and wf.getsampwidth() == SAMPLE_WIDTH
                    and wf.getframerate() == SAMPLE_RATE
                )
        except wave.Error:
            match = False
        if match:
            wav.write_bytes(src.read_bytes())
        else:
            decode_to_wav(src, wav)
    else:
        decode_to_wav(src, wav)
    try:
        export_mp3_from_wav(wav, mp3)
    except Exception:
        pass
    return mp3, wav


def output_dir_for_script(yaml_path: Path) -> Path:
    out = default_output_dir(yaml_path)
    (out / "sentences").mkdir(parents=True, exist_ok=True)
    return out
