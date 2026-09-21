import tempfile
import unittest
from pathlib import Path

from PIL import Image

from open_tts.sprite import VISEME_COL, ensure_placeholder_sheet, CharacterSheet
from open_tts.visemes import build_phone_intervals, viseme_at_time
from open_tts.video import (
    _compose_split_frame,
    _frame_for_line,
    merged_speaker_blocks,
)


class TestExpressionCues(unittest.TestCase):
    def test_smile_cue_uses_smile_cell_not_vowel(self):
        with tempfile.TemporaryDirectory() as tmp:
            sheet_path = Path(tmp) / "eve.png"
            ensure_placeholder_sheet(sheet_path, "eve")
            sheet = CharacterSheet(sheet_path)
            line = {
                "id": 3,
                "text": "Thank you Leo, it's great to be here.",
                "cue": "smile",
            }
            frame_path = _frame_for_line(sheet, line, 0.0)
            expr_px = sheet.expression_frames("smile")[0].getpixel((0, 0))
            vowel_px = sheet.viseme("e").getpixel((0, 0))
            actual = Image.open(frame_path).getpixel((0, 0))
            self.assertEqual(actual, expr_px)
            self.assertNotEqual(actual, vowel_px)


class TestPhonemeMouths(unittest.TestCase):
    def test_map_line_paints_mbp_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            sheet_path = Path(tmp) / "leo.png"
            ensure_placeholder_sheet(sheet_path, "leo")
            sheet = CharacterSheet(sheet_path)
            duration = 1.0
            phones = build_phone_intervals("map", duration)
            line = {
                "id": 9,
                "text": "map",
                "duration": duration,
                "phones": phones,
            }
            t0 = next(p["t0"] for p in phones if p["viseme"] == "mbp")
            t_mid = (t0 + next(p["t1"] for p in phones if p["viseme"] == "mbp")) / 2
            self.assertEqual(viseme_at_time(phones, t_mid), "mbp")
            frame_path = _frame_for_line(sheet, line, t_mid)
            expected = sheet.mbp().getpixel((0, 0))
            actual = Image.open(frame_path).getpixel((0, 0))
            self.assertEqual(actual, expected)
            self.assertNotEqual(actual, sheet.pause().getpixel((0, 0)))


class TestPauseCue(unittest.TestCase):
    def test_pause_cue_uses_pause_cell_not_vowel(self):
        with tempfile.TemporaryDirectory() as tmp:
            sheet_path = Path(tmp) / "leo.png"
            ensure_placeholder_sheet(sheet_path, "leo")
            sheet = CharacterSheet(sheet_path)
            line = {
                "id": 7,
                "text": "Hello everyone with lots of vowels",
                "cue": "pause",
            }
            frame_path = _frame_for_line(sheet, line, 0.25)
            pause_px = sheet.pause().getpixel((0, 0))
            vowel_px = sheet.viseme("e").getpixel((0, 0))
            actual = Image.open(frame_path).getpixel((0, 0))
            self.assertEqual(actual, pause_px)
            self.assertNotEqual(actual, vowel_px)
            self.assertEqual(VISEME_COL["pause"], 5)


class TestDualLayout(unittest.TestCase):
    def test_merged_blocks_mark_split_at_intro_and_outro(self):
        segments = [
            {"id": i, "speaker": "leo" if i <= 4 else "eve", "start": float(i), "duration": 1.0}
            for i in range(1, 11)
        ]
        blocks = merged_speaker_blocks(segments, audio_duration=20.0, dual_start=4, dual_end=5)
        modes = [b["mode"] for b in blocks]
        self.assertIn("split", modes)
        self.assertIn("full", modes)
        self.assertEqual(blocks[0]["mode"], "split")

    def test_split_compose_puts_host_left_guest_right(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            host = root / "leo.png"
            guest = root / "eve.png"
            ensure_placeholder_sheet(host, "leo")
            ensure_placeholder_sheet(guest, "eve")
            host_sheet = CharacterSheet(host)
            guest_sheet = CharacterSheet(guest)
            left = _frame_for_line(
                host_sheet, {"id": 1, "text": "talk", "cue": "pause"}, 0.0
            )
            right = _frame_for_line(
                guest_sheet, {"id": 2, "text": "", "cue": "pause"}, 0.0
            )
            out = root / "split.png"
            _compose_split_frame(left, right, (128, 64), out)
            img = Image.open(out)
            self.assertEqual(img.size, (128, 64))
            host_px = host_sheet.pause().resize((64, 64), Image.Resampling.LANCZOS)
            guest_px = guest_sheet.pause().resize((64, 64), Image.Resampling.LANCZOS)
            self.assertEqual(img.getpixel((5, 5)), host_px.convert("RGB").getpixel((5, 5)))
            self.assertEqual(img.getpixel((69, 5)), guest_px.convert("RGB").getpixel((5, 5)))


if __name__ == "__main__":
    unittest.main()
