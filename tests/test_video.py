import tempfile
import unittest
from pathlib import Path

from PIL import Image

from open_tts.sprite import VISEME_COL, ensure_placeholder_sheet, CharacterSheet
from open_tts.video import (
    _ATTENTIVE_LINE,
    _compose_full_frame,
    _compose_split_frame,
    _frame_for_line,
    line_is_split,
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
            self.assertNotEqual(img.getpixel((32, 29))[:3], img.getpixel((0, 0))[:3])
            self.assertNotEqual(img.getpixel((96, 29))[:3], img.getpixel((0, 0))[:3])

    def test_full_compose_keeps_square_not_panoramic_crop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cell = Path(tmp) / "cell.png"
            Image.new("RGB", (32, 32), (0, 220, 0)).save(cell)
            dest = Path(tmp) / "full.png"
            _compose_full_frame(cell, (64, 36), dest)
            img = Image.open(dest)
            self.assertEqual(img.size, (64, 36))
            self.assertEqual(img.getpixel((32, 16))[:3], (0, 220, 0))
            self.assertEqual(img.getpixel((2, 2))[3], 0)


class TestPerUtteranceSplit(unittest.TestCase):
    def test_line_split_override_beats_dual_defaults(self):
        mid = {"id": 6, "speaker": "leo", "split": True}
        self.assertTrue(line_is_split(mid, 10, dual_start=1, dual_end=1))
        forced_full = {"id": 1, "speaker": "leo", "split": False}
        self.assertFalse(line_is_split(forced_full, 10, dual_start=4, dual_end=5))
        self.assertFalse(line_is_split({"id": 3, "speaker": "leo"}, 10, 4, 5, can_split=False))

    def test_merged_blocks_break_when_screen_changes(self):
        segments = [
            {"id": 1, "speaker": "leo", "start": 0.0, "duration": 1.0, "split": True},
            {"id": 2, "speaker": "leo", "start": 1.0, "duration": 1.0, "split": False},
            {"id": 3, "speaker": "eve", "start": 2.0, "duration": 1.0, "split": True},
        ]
        blocks = merged_speaker_blocks(segments, audio_duration=4.0, dual_start=0, dual_end=0)
        self.assertEqual([b["mode"] for b in blocks], ["split", "full", "split"])
        self.assertEqual(blocks[0]["speaker"], "leo")
        self.assertEqual(blocks[1]["speaker"], "leo")

    def test_cast_change_starts_new_block(self):
        segments = [
            {"id": 1, "speaker": "leo", "start": 0.0, "duration": 1.0, "split": True},
            {"id": 2, "speaker": "leo", "start": 1.0, "duration": 1.0, "split": True, "right": "maria"},
        ]
        blocks = merged_speaker_blocks(
            segments, audio_duration=3.0, dual_start=0, dual_end=0, left="leo", right="eve"
        )
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["right"], "eve")
        self.assertEqual(blocks[1]["right"], "maria")
        self.assertEqual(blocks[1]["left"], "leo")

    def test_attentive_cue_uses_listen_animation(self):
        with tempfile.TemporaryDirectory() as tmp:
            sheet_path = Path(tmp) / "eve.png"
            ensure_placeholder_sheet(sheet_path, "eve")
            sheet = CharacterSheet(sheet_path)
            frame_path = _frame_for_line(sheet, _ATTENTIVE_LINE, 0.0)
            listen_px = sheet.expression_frames("listen")[0].getpixel((0, 0))
            pause_px = sheet.pause().getpixel((0, 0))
            actual = Image.open(frame_path).getpixel((0, 0))
            self.assertEqual(actual, listen_px)
            self.assertNotEqual(actual, pause_px)


if __name__ == "__main__":
    unittest.main()
