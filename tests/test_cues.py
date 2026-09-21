import tempfile
import unittest
from pathlib import Path

from open_tts.cues import (
    AUTO,
    LAUGH,
    LISTEN,
    PAUSE,
    SMILE,
    SURPRISE,
    cue_to_yaml_value,
    suggest_cue,
    validate_cue,
)
from open_tts.imagine import build_sheet_from_hero
from open_tts.script import normalized_lines
from open_tts.sprite import (
    EXPRESSION_COL,
    VISEME_COL,
    CharacterSheet,
    ensure_placeholder_sheet,
)

_REQUIRED_EXPRESSION_IDS = ("surprise", "laugh", "smile", "concern", "think", "listen")


class TestExpressionColContract(unittest.TestCase):
    def test_expression_col_has_all_locked_ids(self):
        for expr_id in _REQUIRED_EXPRESSION_IDS:
            self.assertIn(expr_id, EXPRESSION_COL)


class TestCueSuggestion(unittest.TestCase):
    def test_partner_enthusiasm_line(self):
        line = "There's always a bit of sales enthusiasm!"
        self.assertEqual(suggest_cue(line), LAUGH)

    def test_partner_thank_you_line(self):
        line = "Thank you Leo, it is great to be here."
        self.assertEqual(suggest_cue(line), SMILE)

    def test_smile_welcome(self):
        self.assertEqual(suggest_cue("Welcome everyone."), SMILE)

    def test_surprise_punctuation(self):
        self.assertEqual(suggest_cue("Really?"), SURPRISE)

    def test_listen_empty_and_ellipsis(self):
        self.assertEqual(suggest_cue(""), LISTEN)
        self.assertEqual(suggest_cue("…"), LISTEN)
        self.assertEqual(suggest_cue("..."), LISTEN)

    def test_pause_parenthetical(self):
        self.assertEqual(suggest_cue("(nods)"), PAUSE)

    def test_auto_default(self):
        self.assertEqual(suggest_cue("Leo explains the product."), AUTO)

    def test_cue_to_yaml_omits_auto(self):
        self.assertIsNone(cue_to_yaml_value(AUTO))
        self.assertEqual(cue_to_yaml_value(LAUGH), "laugh")
        self.assertEqual(cue_to_yaml_value(PAUSE), "pause")
        self.assertEqual(cue_to_yaml_value(SMILE), "smile")

    def test_validate_cue_rejects_unknown(self):
        with self.assertRaises(ValueError):
            validate_cue("not-a-real-cue")

    def test_normalized_lines_rejects_unknown_cue(self):
        data = {
            "characters": {"host": "leo", "guest": "eve"},
            "script": [{"speaker": "host", "text": "Hi", "cue": "bogus"}],
        }
        with self.assertRaises(ValueError):
            normalized_lines(data)


class TestSheetFromHero(unittest.TestCase):
    def test_baked_sheet_matches_shared_indices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hero = root / "hero.png"
            ref = root / "ref.png"
            ensure_placeholder_sheet(ref, "ref")
            build_sheet_from_hero(ref, hero)
            baked = CharacterSheet(hero)
            leo = root / "leo.png"
            ensure_placeholder_sheet(leo, "leo")
            placeholder = CharacterSheet(leo)
            self.assertEqual(
                baked.viseme("o").size,
                placeholder.viseme("o").size,
            )
            self.assertEqual(VISEME_COL["o"], 3)
            self.assertEqual(EXPRESSION_COL["laugh"], 1)
            self.assertEqual(baked.laugh().size, placeholder.laugh().size)
            self.assertEqual(baked.smile().size, placeholder.smile().size)
            self.assertEqual(EXPRESSION_COL["smile"], 2)

    def test_laugh_strip_is_six_frames_across(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sheet_path = root / "char.png"
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

    def test_smile_frames_use_smile_cell_not_pause(self):
        with tempfile.TemporaryDirectory() as tmp:
            sheet_path = Path(tmp) / "char.png"
            ensure_placeholder_sheet(sheet_path, "demo")
            sheet = CharacterSheet(sheet_path)
            pause_px = sheet.pause().getpixel((0, 0))
            smile_px = sheet.smile().getpixel((0, 0))
            frame_px = sheet.expression_frames("smile")[0].getpixel((0, 0))
            self.assertNotEqual(smile_px, pause_px)
            self.assertNotEqual(frame_px, pause_px)


if __name__ == "__main__":
    unittest.main()
