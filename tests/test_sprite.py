import tempfile
import unittest
from pathlib import Path

from open_tts.sprite import (
    EXPRESSION_COL,
    VISEME_COL,
    CharacterSheet,
    ensure_placeholder_sheet,
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
            self.assertEqual(VISEME_COL["pause"], 5)
            laugh_a = a.laugh().getpixel((0, 0))
            laugh_b = b.laugh().getpixel((0, 0))
            self.assertEqual(laugh_a, laugh_b)
            smile_a = a.smile().getpixel((0, 0))
            smile_b = b.smile().getpixel((0, 0))
            self.assertEqual(smile_a, smile_b)
            self.assertNotEqual(smile_a, laugh_a)

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


if __name__ == "__main__":
    unittest.main()
