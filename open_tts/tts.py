"""Optional Grok TTS (credentials via environment only)."""

from __future__ import annotations

import base64
import os
from pathlib import Path

import requests


def generate_speech(text: str, voice_id: str, dest_mp3: Path) -> None:
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
        json={"text": text, "voice_id": voice_id, "language": "en"},
        timeout=120,
    )
    response.raise_for_status()
    dest_mp3.write_bytes(response.content)


def ensure_sentence_audio(
    text: str,
    voice_id: str,
    mp3_path: Path,
    skip_tts: bool,
) -> None:
    if mp3_path.is_file():
        return
    if skip_tts:
        raise FileNotFoundError(
            f"Missing audio {mp3_path} and --skip-tts was set."
        )
    generate_speech(text, voice_id, mp3_path)
