"""Optional Grok TTS (credentials via environment only)."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import requests


def _parse_timestamp_envelope(payload: dict) -> dict | None:
    ts = payload.get("audio_timestamps")
    if not ts or not ts.get("graph_chars") or not ts.get("graph_times"):
        return None
    graph_chars = ts["graph_chars"]
    graph_times = ts["graph_times"]
    first = graph_times[0]
    if isinstance(first, (list, tuple)) and len(first) >= 2:
        try:
            ends = [float(pair[1]) for pair in graph_times]
        except (TypeError, ValueError, IndexError):
            return None
        graph_times = ends
    return {"graph_chars": graph_chars, "graph_times": graph_times}


def decode_tts_response(body: bytes) -> tuple[bytes, dict | None]:
    """Parse xAI TTS body: JSON envelope with optional timestamps, or raw audio."""
    if not body:
        return body, None
    if body[:1] == b"{":
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return body, None
        audio_b64 = payload.get("audio")
        if not audio_b64:
            return body, None
        audio = base64.b64decode(audio_b64)
        return audio, _parse_timestamp_envelope(payload)
    return body, None


def _timestamps_sidecar(mp3_path: Path) -> Path:
    return mp3_path.with_suffix(".timestamps.json")


def load_tts_timestamps(mp3_path: Path) -> dict | None:
    sidecar = _timestamps_sidecar(mp3_path)
    if not sidecar.is_file():
        return None
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not data.get("graph_chars") or not data.get("graph_times"):
        return None
    return data


def _write_timestamps_sidecar(mp3_path: Path, timestamps: dict) -> None:
    sidecar = _timestamps_sidecar(mp3_path)
    sidecar.write_text(json.dumps(timestamps), encoding="utf-8")


def generate_speech(text: str, voice_id: str, dest_mp3: Path) -> dict | None:
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "TTS requested but XAI_API_KEY is not set in the environment."
        )
    dest_mp3.parent.mkdir(parents=True, exist_ok=True)
    response = requests.post(
        "https://api.x.ai/v1/tts",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "voice_id": voice_id,
            "language": "en",
            "with_timestamps": True,
        },
        timeout=120,
    )
    response.raise_for_status()
    audio, meta = decode_tts_response(response.content)
    dest_mp3.write_bytes(audio)
    if meta:
        _write_timestamps_sidecar(dest_mp3, meta)
    return meta


def ensure_sentence_audio(
    text: str,
    voice_id: str,
    mp3_path: Path,
    skip_tts: bool,
) -> dict | None:
    if mp3_path.is_file():
        return load_tts_timestamps(mp3_path)
    if skip_tts:
        raise FileNotFoundError(
            f"Missing audio {mp3_path} and --skip-tts was set."
        )
    return generate_speech(text, voice_id, mp3_path)
