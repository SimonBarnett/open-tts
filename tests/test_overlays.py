import tempfile
import unittest
from pathlib import Path

from PIL import Image

from open_tts.overlays import (
    composite_on_background,
    ffmpeg_escape_text,
    import_drop,
    overlay_spec,
    overlays_to_yaml,
)
from open_tts.script import interview_document


class TestOverlays(unittest.TestCase):
    def test_overlay_spec_reads_yaml_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bg = root / "bg.png"
            Image.new("RGB", (8, 8), (10, 20, 30)).save(bg)
            data = {
                "overlays": {
                    "background": str(bg),
                    "title": {"text": "Hello", "duration": 2.5},
                    "scroll": {"text": "Line A\nLine B"},
                }
            }
            spec = overlay_spec(data)
            self.assertEqual(spec.background, bg.resolve())
            self.assertTrue(spec.has_title)
            self.assertTrue(spec.has_scroll)
            self.assertEqual(spec.title_duration, 2.5)

    def test_document_round_trip_overlays(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = Path(tmp) / "show.yaml"
            bg = Path(tmp) / "plate.png"
            Image.new("RGB", (4, 4), (1, 2, 3)).save(bg)
            spec = overlay_spec(
                {
                    "overlays": {
                        "background": str(bg),
                        "title": "Show title",
                        "scroll": "Thanks for watching",
                    }
                }
            )
            doc = interview_document(
                title="T",
                characters={"host": "leo", "guest": "eve"},
                layout={"dual_start_turns": 0, "dual_end_turns": 0},
                script_rows=[{"speaker": "leo", "text": "Hi"}],
                overlays=overlays_to_yaml(spec, yaml_path),
            )
            self.assertIn("overlays", doc)
            self.assertEqual(doc["overlays"]["title"]["text"], "Show title")
            again = overlay_spec(doc, yaml_path)
            self.assertTrue(again.has_title)
            self.assertTrue(again.has_scroll)

    def test_composite_uses_background(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bg = Path(tmp) / "bg.png"
            Image.new("RGB", (64, 36), (255, 0, 0)).save(bg)
            fg = Image.new("RGBA", (16, 16), (0, 255, 0, 255))
            dest = Path(tmp) / "out.png"
            composite_on_background(fg, dest, (64, 36), bg)
            out = Image.open(dest)
            self.assertEqual(out.size, (64, 36))
            self.assertEqual(out.getpixel((0, 0))[:3], (255, 0, 0))

    def test_composite_default_is_transparent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fg = Image.new("RGBA", (16, 16), (0, 255, 0, 255))
            dest = Path(tmp) / "out.png"
            composite_on_background(fg, dest, (64, 36), None)
            out = Image.open(dest)
            self.assertEqual(out.mode, "RGBA")
            self.assertEqual(out.getpixel((0, 0))[3], 0)
            self.assertNotEqual(out.getpixel((32, 18))[3], 0)

    def test_import_drop_copies_into_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src.png"
            src.write_bytes(b"x")
            dest_dir = Path(tmp) / "assets"
            dest = import_drop(src, dest_dir)
            self.assertTrue(dest.is_file())
            self.assertEqual(dest.parent.resolve(), dest_dir.resolve())

    def test_ffmpeg_escape_text(self) -> None:
        self.assertIn("\\:", ffmpeg_escape_text("a:b"))


if __name__ == "__main__":
    unittest.main()
