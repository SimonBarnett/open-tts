import tempfile
import unittest
from pathlib import Path

from open_tts.sprite import (
    CONSONANT_ROW,
    CONSONANT_VISEME_COL,
    EXPRESSION_COL,
    EXPRESSION_ROW,
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

    def test_consonant_row_shared_across_characters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leo = root / "leo.png"
            eve = root / "eve.png"
            ensure_placeholder_sheet(leo, "leo")
            ensure_placeholder_sheet(eve, "eve")
            a = CharacterSheet(leo)
            b = CharacterSheet(eve)
            self.assertEqual(CONSONANT_ROW, 1)
            self.assertEqual(EXPRESSION_ROW, 2)
            self.assertEqual(CONSONANT_VISEME_COL["mbp"], 0)
            mbp_a = a.mbp().getpixel((0, 0))
            mbp_b = b.mbp().getpixel((0, 0))
            self.assertEqual(mbp_a, mbp_b)
            self.assertNotEqual(mbp_a, a.pause().getpixel((0, 0)))
            self.assertEqual(a.fv().size, a.viseme("fv").size)
            self.assertEqual(VISEME_COL["pause"], 5)


if __name__ == "__main__":
    unittest.main()
