"""Optional Grok TTS (credentials via environment only)."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import requests


def generate_speech(text: str, voice_id: str, dest_mp3: Path) -> dict[str, Any] | None:
    """Synthesize speech; return character timestamps when the API provides them."""
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
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = response.json()
        audio_b64 = payload.get("audio")
        if not audio_b64:
            raise ValueError("TTS JSON response missing audio field")
        dest_mp3.write_bytes(base64.b64decode(audio_b64))
        stamps = payload.get("audio_timestamps") or {}
        chars = stamps.get("graph_chars")
        times = stamps.get("graph_times")
        if chars and times and len(chars) == len(times):
            return {"graph_chars": list(chars), "graph_times": list(times)}
        return None
    dest_mp3.write_bytes(response.content)
    return None


def ensure_sentence_audio(
    text: str,
    voice_id: str,
    mp3_path: Path,
    skip_tts: bool,
    line: dict | None = None,
) -> None:
    if mp3_path.is_file():
        return
    if skip_tts:
        raise FileNotFoundError(
            f"Missing audio {mp3_path} and --skip-tts was set."
        )
    stamps = generate_speech(text, voice_id, mp3_path)
    if line is not None and stamps:
        line["graph_chars"] = stamps["graph_chars"]
        line["graph_times"] = stamps["graph_times"]
