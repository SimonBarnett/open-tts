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

    def test_local_still_rgb_stays_in_range(self) -> None:
        still = LocalImageProvider().generate_still(
            "mid-40s presenter, navy jacket, studio lighting, facing camera",
            None,
        )
        self.assertTrue(still.is_file())
        self.assertGreater(still.stat().st_size, 0)

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
