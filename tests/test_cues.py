import tempfile
import unittest
from pathlib import Path

from open_tts.cues import AUTO, LAUGH, PAUSE, SURPRISE, cue_to_yaml_value, suggest_cue
from open_tts.imagine import build_sheet_from_hero
from open_tts.sprite import (
    EXPRESSION_COL,
    VISEME_COL,
    CharacterSheet,
    ensure_placeholder_sheet,
)


class TestCueSuggestion(unittest.TestCase):
    def test_partner_enthusiasm_line(self):
        line = "There's always a bit of sales enthusiasm!"
        self.assertEqual(suggest_cue(line), LAUGH)

    def test_surprise_punctuation(self):
        self.assertEqual(suggest_cue("Really?"), SURPRISE)

    def test_pause_empty(self):
        self.assertEqual(suggest_cue(""), PAUSE)
        self.assertEqual(suggest_cue("…"), PAUSE)

    def test_auto_default(self):
        self.assertEqual(suggest_cue("Welcome everyone."), AUTO)

    def test_cue_to_yaml_omits_auto(self):
        self.assertIsNone(cue_to_yaml_value(AUTO))
        self.assertEqual(cue_to_yaml_value(LAUGH), "laugh")
        self.assertEqual(cue_to_yaml_value(PAUSE), "pause")


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


if __name__ == "__main__":
    unittest.main()
