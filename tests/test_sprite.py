import tempfile
import unittest
from pathlib import Path

from PIL import Image

from open_tts.sprite import (
    CONSONANT_ROW,
    CONSONANT_VISEME_COL,
    EXPRESSION_COL,
    EXPRESSION_ROW,
    VISEME_COL,
    CharacterSheet,
    ensure_placeholder_sheet,
    fit_cover,
)


class TestSpriteLayout(unittest.TestCase):
    def test_shared_indices_across_characters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leo = root / "leo.png"
            eve = root / "eve.png"
            ensure_placeholder_sheet(leo, "leo")
            ensure_placeholder_sheet(eve, "eve")
            a = CharacterSheet(leo)
            b = CharacterSheet(eve)
            self.assertEqual(
                CharacterSheet.viseme_col("o"), CharacterSheet.viseme_col("o")
            )
            self.assertEqual(a.viseme("o").size, b.viseme("o").size)
            self.assertEqual(EXPRESSION_COL["laugh"], 1)
            self.assertEqual(EXPRESSION_COL["smile"], 2)
            self.assertEqual(EXPRESSION_COL["listen"], 5)
            self.assertEqual(EXPRESSION_ROW, 2)
            self.assertEqual(CONSONANT_ROW, 1)
            self.assertEqual(VISEME_COL["pause"], 5)
            laugh_a = a.laugh().getpixel((0, 0))
            laugh_b = b.laugh().getpixel((0, 0))
            self.assertEqual(laugh_a, laugh_b)
            smile_a = a.smile().getpixel((0, 0))
            smile_b = b.smile().getpixel((0, 0))
            self.assertEqual(smile_a, smile_b)
            self.assertNotEqual(smile_a, laugh_a)

    def test_consonant_viseme_row_shared_across_characters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leo = root / "leo.png"
            eve = root / "eve.png"
            ensure_placeholder_sheet(leo, "leo")
            ensure_placeholder_sheet(eve, "eve")
            a = CharacterSheet(leo)
            b = CharacterSheet(eve)
            for name in CONSONANT_VISEME_COL:
                self.assertEqual(
                    CharacterSheet.viseme_col(name), CONSONANT_VISEME_COL[name]
                )
                self.assertEqual(
                    a.viseme(name).getpixel((0, 0)), b.viseme(name).getpixel((0, 0))
                )
                self.assertNotEqual(
                    a.viseme(name).getpixel((0, 0)), a.pause().getpixel((0, 0))
                )

    def test_laugh_strip_is_six_frames_across(self):
        with tempfile.TemporaryDirectory() as tmp:
            sheet_path = Path(tmp) / "char.png"
            ensure_placeholder_sheet(sheet_path, "demo")
            sheet = CharacterSheet(sheet_path)
            frames = sheet.expression_frames("laugh")
            self.assertEqual(len(frames), 6)
            corner_colors = [frame.getpixel((0, 0)) for frame in frames]
            self.assertEqual(
                len(set(corner_colors)),
                6,
                "laugh strip must span six columns, not a single column",
            )


class TestFitCover(unittest.TestCase):
    def test_landscape_fills_square_no_letterbox(self) -> None:
        src = Image.new("RGBA", (256, 128), (200, 10, 10, 255))
        out = fit_cover(src, (128, 128))
        self.assertEqual(out.size, (128, 128))
        self.assertEqual(out.getpixel((0, 0))[:3], (200, 10, 10))
        self.assertEqual(out.getpixel((127, 127))[:3], (200, 10, 10))


if __name__ == "__main__":
    unittest.main()
