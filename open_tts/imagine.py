"""Image / video LLM provider (testable without Qt)."""

from __future__ import annotations

import base64
import os
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path

import requests
from PIL import Image, ImageEnhance

from open_tts.cartoon import (
    draw_cartoon_still,
    knockout_generated,
    wrap_cartoon_prompt,
    wrap_cartoon_video_prompt,
)
from open_tts.dotenv import load_repo_env
from open_tts.sprite import COLS, DEFAULT_CELL_PX, SHEET_ROWS, fit_cover


def _api_key() -> str | None:
    load_repo_env()
    key = os.environ.get("XAI_IMAGE_API_KEY") or os.environ.get("XAI_API_KEY")
    return key or None


def _temp_png() -> Path:
    fd, name = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    return Path(name)


def _temp_mp4() -> Path:
    fd, name = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    return Path(name)


def _data_url(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, "image/png")
    raw = path.read_bytes()
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def _http_error(response: requests.Response) -> RuntimeError:
    detail = (response.text or "").strip().replace("\n", " ")
    if len(detail) > 800:
        detail = detail[:800] + "…"
    return RuntimeError(f"xAI image HTTP {response.status_code}: {detail or response.reason}")


def build_sheet_from_hero(hero: Path, dest: Path, cell_px: int = DEFAULT_CELL_PX) -> Path:
    """Bake a shared-grid sheet by compositing variants of the locked hero still."""
    hero_img = Image.open(hero).convert("RGBA")
    sheet = Image.new("RGBA", (COLS * cell_px, SHEET_ROWS * cell_px), (32, 36, 44, 255))

    for row in range(SHEET_ROWS):
        for col in range(COLS):
            cell = _hero_cell_variant(hero_img, col, row, cell_px)
            sheet.paste(cell, (col * cell_px, row * cell_px))

    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest)
    return dest


def _hero_cell_variant(
    hero: Image.Image, col: int, row: int, cell_px: int
) -> Image.Image:
    """Cover-fit hero into a cell with mild variation by grid position."""
    cell = fit_cover(hero, (cell_px, cell_px))
    factor = 0.92 + ((col + row * COLS) % 5) * 0.03
    return ImageEnhance.Brightness(cell).enhance(factor)


class ImageProvider(ABC):
    @abstractmethod
    def generate_still(self, prompt: str, ref: Path | None = None) -> Path:
        """Return path to a generated hero still PNG."""

    @abstractmethod
    def generate_video(
        self, prompt: str, ref: Path | None = None, slot: str = "full"
    ) -> Path:
        """Return path to one generated viseme MP4 (not a still)."""

    @abstractmethod
    def generate_sheet(self, hero: Path, dest: Path) -> Path:
        """Return path to a full character sheet on the shared grid."""


class LocalImageProvider(ImageProvider):
    """Offline still + sheet generation (CI and no API key)."""

    def generate_still(self, prompt: str, ref: Path | None = None) -> Path:
        src = draw_cartoon_still(prompt)
        tmp = _temp_png()
        src.save(tmp)
        return tmp

    def generate_video(
        self, prompt: str, ref: Path | None = None, slot: str = "full"
    ) -> Path:
        from open_tts.loops import build_viseme_loops

        still = Path(ref) if ref and ref.is_file() and ref.suffix.lower() == ".png" else None
        if still is None:
            still = self.generate_still(prompt, ref)
        work = Path(tempfile.mkdtemp(prefix="local-viseme-"))
        loops = build_viseme_loops(still, "draft", work, frames=16)
        dest = loops["full"]
        if not dest.is_file():
            raise RuntimeError("Local viseme video encode failed (ffmpeg missing?)")
        return dest

    def generate_sheet(self, hero: Path, dest: Path) -> Path:
        return build_sheet_from_hero(hero, dest)


class XAIImageProvider(ImageProvider):
    """xAI Grok Imagine still generation; sheet baked locally from hero."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or _api_key()
        if not self._api_key:
            raise RuntimeError(
                "Image generation requires XAI_API_KEY or XAI_IMAGE_API_KEY in the environment."
            )

    def generate_still(self, prompt: str, ref: Path | None = None) -> Path:
        body: dict = {
            "model": os.environ.get("XAI_IMAGE_MODEL", "grok-imagine-image"),
            "prompt": wrap_cartoon_prompt(prompt),
            "n": 1,
            "response_format": "b64_json",
        }
        if ref and ref.is_file():
            body["prompt"] += " Same cartoon character as the previous still."
        response = requests.post(
            "https://api.x.ai/v1/images/generations",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=180,
        )
        if not response.ok:
            raise _http_error(response)
        payload = response.json()
        data = payload.get("data") or []
        if not data:
            raise RuntimeError("xAI image response contained no data")
        item = data[0]
        if item.get("b64_json"):
            raw = base64.b64decode(item["b64_json"])
        elif item.get("url"):
            raw = requests.get(item["url"], timeout=120).content
        else:
            raise RuntimeError("xAI image response missing b64_json and url")
        tmp = _temp_png()
        tmp.write_bytes(raw)
        with Image.open(tmp) as hero:
            cut = knockout_generated(hero)
            cut.save(tmp)
        return tmp

    def generate_video(
        self, prompt: str, ref: Path | None = None, slot: str = "full"
    ) -> Path:
        body: dict = {
            "model": os.environ.get("XAI_VIDEO_MODEL", "grok-imagine-video-1.5"),
            "prompt": wrap_cartoon_video_prompt(prompt, slot),
            "duration": int(os.environ.get("XAI_VIDEO_DURATION", "4")),
            "aspect_ratio": "16:9",
            "resolution": os.environ.get("XAI_VIDEO_RESOLUTION", "480p"),
        }
        if ref is not None and ref.is_file():
            image = ref
            if ref.suffix.lower() in {".mp4", ".mov", ".webm"}:
                image = _first_frame(ref)
            if image is not None and image.is_file():
                body["image"] = {"url": _data_url(image)}
                body["prompt"] += " Same cartoon character as the reference."
        response = requests.post(
            "https://api.x.ai/v1/videos/generations",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=60,
        )
        if not response.ok:
            raise _http_error(response)
        request_id = str((response.json() or {}).get("request_id") or "").strip()
        if not request_id:
            raise RuntimeError("xAI video response contained no request_id")
        payload = self._poll_video(request_id)
        video = payload.get("video") or {}
        if video.get("respect_moderation") is False:
            raise RuntimeError("xAI blocked the viseme video (moderation).")
        url = video.get("url")
        if not url:
            raise RuntimeError("xAI video finished with no download url")
        raw = requests.get(url, timeout=180)
        if not raw.ok:
            raise _http_error(raw)
        tmp = _temp_mp4()
        tmp.write_bytes(raw.content)
        if tmp.stat().st_size < 1000:
            raise RuntimeError("xAI video download was empty")
        return tmp

    def _poll_video(self, request_id: str, timeout: float = 600.0, interval: float = 4.0) -> dict:
        deadline = time.time() + timeout
        headers = {"Authorization": f"Bearer {self._api_key}"}
        url = f"https://api.x.ai/v1/videos/{request_id}"
        while time.time() < deadline:
            response = requests.get(url, headers=headers, timeout=60)
            if response.status_code == 202:
                time.sleep(interval)
                continue
            if not response.ok:
                raise _http_error(response)
            payload = response.json() or {}
            status = str(payload.get("status") or "")
            if status == "done":
                return payload
            if status in {"failed", "expired", "cancelled"}:
                err = payload.get("error") or {}
                raise RuntimeError(str(err.get("message") or f"xAI video {status}"))
            time.sleep(interval)
        raise TimeoutError("xAI video generation timed out")

    def generate_sheet(self, hero: Path, dest: Path) -> Path:
        return build_sheet_from_hero(hero, dest)


def _first_frame(video: Path) -> Path | None:
    import subprocess

    dest = _temp_png()
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(video.resolve()), "-frames:v", "1", str(dest)],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        dest.unlink(missing_ok=True)
        return None
    return dest if dest.is_file() and dest.stat().st_size > 0 else None


def get_image_provider() -> ImageProvider:
    if _api_key():
        return XAIImageProvider()
    return LocalImageProvider()
