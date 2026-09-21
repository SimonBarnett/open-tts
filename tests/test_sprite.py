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
    def test_expression_col_locked_columns(self):
        self.assertEqual(
            EXPRESSION_COL,
            {
                "surprise": 0,
                "laugh": 1,
                "smile": 2,
                "concern": 3,
                "think": 4,
                "listen": 5,
            },
        )

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

    def test_all_expression_methods_match_leo_and_eve(self):
        accessors = (
            ("surprise", "surprise"),
            ("laugh", "laugh"),
            ("smile", "smile"),
            ("concern", "concern"),
            ("think", "think"),
            ("listen", "listen"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leo = root / "leo.png"
            eve = root / "eve.png"
            ensure_placeholder_sheet(leo, "leo")
            ensure_placeholder_sheet(eve, "eve")
            a = CharacterSheet(leo)
            b = CharacterSheet(eve)
            for name, attr in accessors:
                px_a = getattr(a, attr)().getpixel((0, 0))
                px_b = getattr(b, attr)().getpixel((0, 0))
                self.assertEqual(px_a, px_b, msg=name)
                frames_a = a.expression_frames(name)
                frames_b = b.expression_frames(name)
                self.assertEqual(len(frames_a), 2)
                self.assertEqual(
                    frames_a[0].getpixel((0, 0)),
                    frames_b[0].getpixel((0, 0)),
                    msg=name,
                )


if __name__ == "__main__":
    unittest.main()
