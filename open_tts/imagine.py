"""Image LLM provider interface (testable without Qt)."""

from __future__ import annotations

import base64
import hashlib
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import requests
from PIL import Image, ImageEnhance

from open_tts.sprite import COLS, DEFAULT_CELL_PX, SHEET_ROWS


def _api_key() -> str | None:
    return os.environ.get("XAI_IMAGE_API_KEY") or os.environ.get("XAI_API_KEY")


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
    """Resize hero into a cell with mild variation by grid position."""
    base = hero.copy()
    base.thumbnail((cell_px, cell_px), Image.Resampling.LANCZOS)
    cell = Image.new("RGBA", (cell_px, cell_px), (0, 0, 0, 0))
    ox = (cell_px - base.width) // 2
    oy = (cell_px - base.height) // 2
    cell.paste(base, (ox, oy), base)
    factor = 0.92 + ((col + row * COLS) % 5) * 0.03
    cell = ImageEnhance.Brightness(cell).enhance(factor)
    return cell


class ImageProvider(ABC):
    @abstractmethod
    def generate_still(self, prompt: str, ref: Path | None = None) -> Path:
        """Return path to a generated hero still PNG."""

    @abstractmethod
    def generate_sheet(self, hero: Path, dest: Path) -> Path:
        """Return path to a full character sheet on the shared grid."""


class LocalImageProvider(ImageProvider):
    """Offline still + sheet generation (CI and no API key)."""

    def generate_still(self, prompt: str, ref: Path | None = None) -> Path:
        if ref and ref.is_file():
            src = Image.open(ref).convert("RGBA")
        else:
            digest = hashlib.sha256(prompt.encode("utf-8")).digest()
            rgb = tuple(80 + digest[i] for i in range(3))
            src = Image.new("RGBA", (512, 512), (*rgb, 255))
        tmp = Path(tempfile.mkstemp(suffix=".png")[1])
        src.save(tmp)
        return tmp

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
            "prompt": prompt,
            "n": 1,
            "response_format": "b64_json",
        }
        response = requests.post(
            "https://api.x.ai/v1/images/generations",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=180,
        )
        response.raise_for_status()
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
        tmp = Path(tempfile.mkstemp(suffix=".png")[1])
        tmp.write_bytes(raw)
        if ref and ref.is_file():
            ref_img = Image.open(ref).convert("RGBA").resize(
                Image.open(tmp).size, Image.Resampling.LANCZOS
            )
            hero = Image.open(tmp).convert("RGBA")
            blended = Image.blend(ref_img, hero, alpha=0.65)
            blended.save(tmp)
        return tmp

    def generate_sheet(self, hero: Path, dest: Path) -> Path:
        return build_sheet_from_hero(hero, dest)


def get_image_provider() -> ImageProvider:
    if _api_key():
        return XAIImageProvider()
    return LocalImageProvider()
