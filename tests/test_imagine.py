import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from open_tts.dotenv import load_repo_env
from PIL import Image

from open_tts.imagine import (
    LocalImageProvider,
    XAIImageProvider,
    _http_error,
    _temp_png,
    build_sheet_from_hero,
    get_image_provider,
)
from open_tts.sprite import DEFAULT_CELL_PX


class TestDotenv(unittest.TestCase):
    def test_load_sets_missing_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("XAI_API_KEY=from-file\nOTHER=kept\n", encoding="utf-8")
            os.environ.pop("OTHER", None)
            os.environ["XAI_API_KEY"] = "already-set"
            try:
                loaded = load_repo_env(path)
                self.assertEqual(loaded, path)
                self.assertEqual(os.environ["XAI_API_KEY"], "already-set")
                self.assertEqual(os.environ["OTHER"], "kept")
            finally:
                os.environ.pop("OTHER", None)
                os.environ.pop("XAI_API_KEY", None)


class TestImagineHelpers(unittest.TestCase):
    def test_temp_png_is_writable(self) -> None:
        path = _temp_png()
        path.write_bytes(b"ok")
        self.assertTrue(path.is_file())
        path.unlink(missing_ok=True)

    def test_local_still_is_cartoon_with_transparent_plate(self) -> None:
        still = LocalImageProvider().generate_still(
            "mid-40s presenter, navy jacket, red hair, facing camera",
            None,
        )
        self.assertTrue(still.is_file())
        img = Image.open(still).convert("RGBA")
        self.assertEqual(img.getpixel((2, 2))[3], 0)
        mid = img.getpixel((img.width // 2, img.height // 2))
        self.assertGreater(mid[3], 200)
        other = LocalImageProvider().generate_still("green jacket, blonde hair", None)
        other_img = Image.open(other).convert("RGBA")
        self.assertNotEqual(img.tobytes(), other_img.tobytes())
        img.close()
        other_img.close()
        still.unlink(missing_ok=True)
        other.unlink(missing_ok=True)

    def test_cartoon_prompt_demands_flat_cartoon(self) -> None:
        from open_tts.cartoon import wrap_cartoon_prompt

        text = wrap_cartoon_prompt("navy jacket")
        self.assertIn("navy jacket", text)
        self.assertIn("cartoon", text.lower())
        self.assertIn("FF00FF", text)
        from open_tts.cartoon import wrap_cartoon_video_prompt

        video = wrap_cartoon_video_prompt("navy jacket")
        self.assertIn("VIDEO", video)
        smile = wrap_cartoon_video_prompt("navy jacket", "smile")
        self.assertIn("Smiling", smile)

    def test_http_error_includes_status_and_body(self) -> None:
        response = requests.Response()
        response.status_code = 400
        response._content = b'{"error":"nope"}'
        response.reason = "Bad Request"
        err = _http_error(response)
        self.assertIn("400", str(err))
        self.assertIn("nope", str(err))

    def test_get_image_provider_local_without_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("XAI_API_KEY", None)
            os.environ.pop("XAI_IMAGE_API_KEY", None)
            with patch("open_tts.imagine.load_repo_env", return_value=None):
                provider = get_image_provider()
        self.assertIsInstance(provider, LocalImageProvider)

    def test_xai_generate_video_posts_to_videos_not_images(self) -> None:
        from unittest.mock import MagicMock

        provider = XAIImageProvider(api_key="test-key")
        posted: list[str] = []

        def fake_post(url, **kwargs):
            posted.append(url)
            response = MagicMock()
            response.ok = True
            response.json.return_value = {"request_id": "rid-1"}
            return response

        def fake_get(url, **kwargs):
            response = MagicMock()
            response.ok = True
            response.status_code = 200
            if url.rstrip("/").endswith("/videos/rid-1"):
                response.json.return_value = {
                    "status": "done",
                    "video": {
                        "url": "https://example.test/clip.mp4",
                        "duration": 4,
                        "respect_moderation": True,
                    },
                }
                response.content = b""
            else:
                response.json.return_value = {}
                response.content = b"\x00\x00fake-mp4-bytes-" + (b"X" * 1200)
            return response

        with patch("open_tts.imagine.requests.post", side_effect=fake_post), patch(
            "open_tts.imagine.requests.get", side_effect=fake_get
        ), patch("open_tts.imagine.time.sleep"):
            path = provider.generate_video("navy jacket, red hair")
        self.assertTrue(any("/videos/generations" in url for url in posted))
        self.assertFalse(any("/images/" in url for url in posted))
        self.assertEqual(path.suffix.lower(), ".mp4")
        self.assertGreater(path.stat().st_size, 10)
        path.unlink(missing_ok=True)

    def test_local_generate_video_writes_mp4(self) -> None:
        try:
            path = LocalImageProvider().generate_video("navy jacket")
        except RuntimeError as exc:
            self.skipTest(str(exc))
        self.assertEqual(path.suffix.lower(), ".mp4")
        self.assertTrue(path.is_file())
        self.assertGreater(path.stat().st_size, 1000)

    def test_sheet_cells_fill_not_letterboxed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hero = Path(tmp) / "hero.png"
            dest = Path(tmp) / "sheet.png"
            Image.new("RGBA", (256, 128), (200, 10, 10, 255)).save(hero)
            build_sheet_from_hero(hero, dest)
            sheet = Image.open(dest).convert("RGBA")
            canvas = (32, 36, 44)
            for xy in ((0, 0), (DEFAULT_CELL_PX - 1, DEFAULT_CELL_PX - 1)):
                px = sheet.getpixel(xy)
                self.assertEqual(px[3], 255)
                self.assertNotEqual(px[:3], canvas)
                self.assertGreater(px[0], 140)


if __name__ == "__main__":
    unittest.main()
