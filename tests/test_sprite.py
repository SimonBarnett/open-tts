import tempfile
import unittest
from pathlib import Path

from open_tts.sprite import (
    ANIMATION_START_ROW,
    EXPRESSION_COL,
    VISEME_COL,
    CharacterSheet,
    ensure_placeholder_sheet,
)

LOCKED_EXPRESSION_COL = {
    "surprise": 0,
    "laugh": 1,
    "smile": 2,
    "concern": 3,
    "think": 4,
    "listen": 5,
}


class TestSpriteLayout(unittest.TestCase):
    def test_expression_col_locked_six_wide_row(self):
        self.assertEqual(EXPRESSION_COL, LOCKED_EXPRESSION_COL)

    def test_expression_frames_smile_not_pause_stand_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            sheet_path = Path(tmp) / "leo.png"
            ensure_placeholder_sheet(sheet_path, "leo")
            sheet = CharacterSheet(sheet_path)
            strip_px = sheet.cell(
                EXPRESSION_COL["smile"], ANIMATION_START_ROW
            ).getpixel((0, 0))
            pause_px = sheet.pause().getpixel((0, 0))
            frame_px = sheet.expression_frames("smile")[0].getpixel((0, 0))
            self.assertEqual(frame_px, strip_px)
            self.assertNotEqual(frame_px, pause_px)

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


if __name__ == "__main__":
    unittest.main()
