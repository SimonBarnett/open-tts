"""Optional Grok TTS (credentials via environment only)."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import requests

from open_tts.dotenv import load_repo_env

# Built-in voices from GET https://api.x.ai/v1/tts/voices (retrieved 2026-09-22).
# Live studio refreshes this list when XAI_API_KEY is set.
BUILTIN_TTS_VOICES: tuple[tuple[str, str], ...] = (
    ("altair", "Altair"),
    ("ara", "Ara"),
    ("atlas", "Atlas"),
    ("aurora", "Aurora"),
    ("carina", "Carina"),
    ("castor", "Castor"),
    ("celeste", "Celeste"),
    ("cosmo", "Cosmo"),
    ("eve", "Eve"),
    ("helios", "Helios"),
    ("helix", "Helix"),
    ("iris", "Iris"),
    ("kepler", "Kepler"),
    ("leo", "Leo"),
    ("liora", "Liora"),
    ("lumen", "Lumen"),
    ("luna", "Luna"),
    ("lux", "Lux"),
    ("naksh", "Naksh"),
    ("orion", "Orion"),
    ("perseus", "Perseus"),
    ("rex", "Rex"),
    ("rigel", "Rigel"),
    ("sal", "Sal"),
    ("sirius", "Sirius"),
    ("ursa", "Ursa"),
    ("zagan", "Zagan"),
    ("zenith", "Zenith"),
)

_VOICES_CACHE: list[dict[str, str]] | None = None


def documented_tts_voices() -> list[dict[str, str]]:
    """Offline copy of the official built-in catalog."""
    return [
        {"voice_id": voice_id, "name": name, "language": "multilingual"}
        for voice_id, name in BUILTIN_TTS_VOICES
    ]


def _normalize_voice(raw: dict) -> dict[str, str] | None:
    voice_id = str(raw.get("voice_id") or "").strip()
    if not voice_id:
        return None
    name = str(raw.get("name") or voice_id).strip()
    language = str(raw.get("language") or "").strip()
    return {"voice_id": voice_id, "name": name, "language": language}


def list_tts_voices(*, refresh: bool = False) -> list[dict[str, str]]:
    """Official voices from GET /v1/tts/voices, else the documented catalog."""
    global _VOICES_CACHE
    if _VOICES_CACHE is not None and not refresh:
        return list(_VOICES_CACHE)
    load_repo_env()
    voices = _fetch_remote_voices()
    if not voices:
        voices = documented_tts_voices()
    voices.sort(key=lambda v: (v.get("name") or v["voice_id"]).lower())
    _VOICES_CACHE = voices
    return list(voices)


def _fetch_remote_voices() -> list[dict[str, str]]:
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        return []
    headers = {"Authorization": f"Bearer {api_key}"}
    found: dict[str, dict[str, str]] = {}
    try:
        response = requests.get(
            "https://api.x.ai/v1/tts/voices",
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        for raw in response.json().get("voices") or []:
            if isinstance(raw, dict):
                item = _normalize_voice(raw)
                if item:
                    found[item["voice_id"]] = item
    except (OSError, ValueError, requests.RequestException):
        return []
    try:
        response = requests.get(
            "https://api.x.ai/v1/custom-voices",
            headers=headers,
            timeout=20,
        )
        if response.ok:
            for raw in response.json().get("voices") or []:
                if isinstance(raw, dict):
                    item = _normalize_voice(raw)
                    if item:
                        found[item["voice_id"]] = item
    except (OSError, ValueError, requests.RequestException):
        pass
    return list(found.values())


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
