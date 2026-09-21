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
            for name in ("surprise", "concern", "think", "listen"):
                px_a = getattr(a, name)().getpixel((0, 0))
                px_b = getattr(b, name)().getpixel((0, 0))
                self.assertEqual(px_a, px_b, name)
            for expr_id in EXPRESSION_COL:
                frames = a.expression_frames(expr_id)
                self.assertEqual(len(frames), 2)
                self.assertEqual(
                    frames[0].getpixel((0, 0)), b.expression_frames(expr_id)[0].getpixel((0, 0))
                )

    def test_placeholder_expression_cells_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "leo.png"
            ensure_placeholder_sheet(path, "leo")
            sheet = CharacterSheet(path)
            pixels = {
                name: getattr(sheet, name)().getpixel((0, 0))[:3]
                for name in EXPRESSION_COL
            }
            self.assertEqual(len(set(pixels.values())), len(EXPRESSION_COL))


if __name__ == "__main__":
    unittest.main()
