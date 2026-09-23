import unittest
from pathlib import Path

from PIL import Image

from open_tts.framing import (
    compose_split_pair,
    frame_half,
    frame_monologue,
    is_closeup,
    is_stage_aspect,
    knockout_stage,
    monologue_box,
)
from open_tts.sprite import CharacterSheet


def _sheet(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "characters" / "visemes" / f"{name}.png"


class TestOriginalFraming(unittest.TestCase):
    def test_leo_is_monologue_closeup_eve_is_half_screen(self) -> None:
        if not _sheet("leo").is_file() or not _sheet("eve").is_file():
            self.skipTest("original viseme sheets not present")
        leo = CharacterSheet(_sheet("leo")).pause()
        eve = CharacterSheet(_sheet("eve")).pause()
        self.assertTrue(is_closeup(leo))
        self.assertFalse(is_closeup(eve))

    def test_eve_monologue_tightens_on_her_not_the_desk(self) -> None:
        if not _sheet("eve").is_file():
            self.skipTest("original eve sheet not present")
        eve = CharacterSheet(_sheet("eve")).pause()
        box = monologue_box(eve)
        self.assertLess(box[2] - box[0], eve.width)
        self.assertGreater((box[0] + box[2]) / 2, eve.width * 0.45)
        full = frame_monologue(eve, (64, 36))
        self.assertEqual(full.size, (64, 36))

    def test_half_slots_keep_original_square(self) -> None:
        if not _sheet("leo").is_file() or not _sheet("eve").is_file():
            self.skipTest("original viseme sheets not present")
        leo = CharacterSheet(_sheet("leo")).pause()
        eve = CharacterSheet(_sheet("eve")).pause()
        left = frame_half(leo, (40, 72), "left")
        right = frame_half(eve, (40, 72), "right")
        self.assertEqual(left.size, (40, 72))
        self.assertEqual(right.size, (40, 72))
        pair = compose_split_pair(leo, eve, (80, 72))
        self.assertEqual(pair.size, (80, 72))
        self.assertNotEqual(pair.getpixel((20, 33))[3], 0)
        self.assertNotEqual(pair.getpixel((60, 33))[3], 0)

    def test_original_cells_keep_aspect_not_panoramic_crop(self) -> None:
        if not _sheet("leo").is_file() or not _sheet("eve").is_file():
            self.skipTest("original viseme sheets not present")
        leo = CharacterSheet(_sheet("leo")).pause()
        wide = frame_monologue(leo, (128, 72))
        self.assertEqual(wide.size, (128, 72))
        self.assertEqual(wide.getpixel((0, 36))[3], 0)
        self.assertNotEqual(wide.getpixel((64, 33))[3], 0)

    def test_solid_placeholder_keeps_square_on_wide_canvas(self) -> None:
        cell = Image.new("RGBA", (32, 32), (0, 220, 0, 255))
        full = frame_monologue(cell, (64, 36))
        self.assertEqual(full.size, (64, 36))
        self.assertEqual(full.getpixel((32, 16))[:3], (0, 220, 0))
        self.assertEqual(full.getpixel((0, 16))[3], 0)

    def test_stage_matches_original_736x400(self) -> None:
        from open_tts.framing import STAGE_SIZE

        cell = Image.new("RGBA", (64, 64), (0, 180, 0, 255))
        full = frame_monologue(cell, STAGE_SIZE)
        pair = compose_split_pair(cell, cell, STAGE_SIZE)
        self.assertEqual(full.size, (736, 400))
        self.assertEqual(pair.size, (736, 400))
        self.assertEqual(full.getpixel((2, 2))[3], 0)
        self.assertNotEqual(full.getpixel((368, 184))[3], 0)

    def test_knockout_clears_stage_keeps_character(self) -> None:
        img = Image.new("RGBA", (40, 20), (8, 8, 22, 255))
        for y in range(6, 14):
            for x in range(14, 26):
                img.putpixel((x, y), (46, 126, 208, 255))
        img.putpixel((2, 18), (0, 0, 0, 255))
        img.putpixel((20, 8), (35, 38, 49, 255))
        out = knockout_stage(img)
        self.assertEqual(out.getpixel((1, 1))[3], 0)
        self.assertEqual(out.getpixel((20, 10))[3], 255)
        self.assertEqual(out.getpixel((2, 18))[3], 255)
        self.assertEqual(out.getpixel((20, 8))[3], 255)

    def test_stage_aspect_matches_full_left_right(self) -> None:
        self.assertTrue(is_stage_aspect((736, 400)))
        self.assertTrue(is_stage_aspect((368, 200)))
        self.assertFalse(is_stage_aspect((128, 128)))
