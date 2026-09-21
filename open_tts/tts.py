"""Optional Grok TTS (credentials via environment only)."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import requests


def timestamps_sidecar(mp3_path: Path) -> Path:
    return mp3_path.with_name(f"{mp3_path.stem}.timestamps.json")


def _parse_timestamp_envelope(payload: dict) -> dict | None:
    ts = payload.get("audio_timestamps")
    if not isinstance(ts, dict):
        return None
    graph_chars = ts.get("graph_chars")
    graph_times = ts.get("graph_times")
    if not graph_chars or not graph_times or len(graph_chars) != len(graph_times):
        return None
    ends: list[float] = []
    for entry in graph_times:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            ends.append(float(entry[1]))
        else:
            ends.append(float(entry))
    return {"graph_chars": list(graph_chars), "graph_times": ends}


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
    content_type = (response.headers.get("content-type") or "").lower()
    if "json" in content_type:
        payload = response.json()
        audio_b64 = payload.get("audio")
        if not audio_b64:
            raise ValueError("TTS JSON response missing audio field")
        dest_mp3.write_bytes(base64.b64decode(audio_b64))
        return _parse_timestamp_envelope(payload)
    dest_mp3.write_bytes(response.content)
    return None


def ensure_sentence_audio(
    text: str,
    voice_id: str,
    mp3_path: Path,
    skip_tts: bool,
) -> dict | None:
    sidecar = timestamps_sidecar(mp3_path)
    if mp3_path.is_file():
        if sidecar.is_file():
            return json.loads(sidecar.read_text(encoding="utf-8"))
        return None
    if skip_tts:
        raise FileNotFoundError(
            f"Missing audio {mp3_path} and --skip-tts was set."
        )
    alignment = generate_speech(text, voice_id, mp3_path)
    if alignment:
        sidecar.write_text(json.dumps(alignment), encoding="utf-8")
    return alignment
