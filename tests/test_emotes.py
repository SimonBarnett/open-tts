import tempfile
import unittest
from pathlib import Path

from PIL import Image

from open_tts.emotes import (
    _LOOP,
    _pose,
    apply_emote,
    emote_for_line,
    emote_phase,
)
from open_tts.loops import looped_frames
from open_tts.loops import find_eyes, loops_available, resolve_loop, frame_at
from open_tts.sprite import EXPRESSION_COL
from open_tts.video import _viseme_key


class TestEmotes(unittest.TestCase):
    def test_each_sheet_emote_is_recognized(self) -> None:
        for name in EXPRESSION_COL:
            self.assertEqual(emote_for_line({"cue": name}), name)
        self.assertEqual(emote_for_line({"cue": "attentive"}), "listen")
        self.assertIsNone(emote_for_line({"cue": ""}))
        self.assertIsNone(emote_for_line({"cue": "pause"}))

    def test_emote_phase_cycles_six_frames(self) -> None:
        self.assertEqual(emote_phase(0.0), 0)
        self.assertEqual(emote_phase(0.125), 1)
        self.assertEqual(emote_phase(0.75), 0)

    def test_each_emote_loop_starts_and_ends_the_same(self) -> None:
        for name, frames in _LOOP.items():
            self.assertEqual(len(frames), 6, name)
            self.assertEqual(frames[0], frames[-1], name)
            self.assertEqual(_pose(name, 0), _pose(name, 5), name)
        self.assertEqual(looped_frames(["a", "b", "c"])[-1], "a")
        self.assertEqual(looped_frames(["a", "b", "c"])[0], "a")

    def test_smile_cue_does_not_replace_speech_viseme(self) -> None:
        line = {"id": 1, "text": "father", "cue": "smile", "duration": 1.2}
        self.assertEqual(emote_for_line(line), "smile")
        self.assertNotEqual(_viseme_key(line, 0.35), "pause")

    def test_emotes_redraw_eyes_differently(self) -> None:
        if not loops_available():
            self.skipTest("talking loops not present")
        loop = resolve_loop("leo", "full")
        with Image.open(frame_at(loop, 0)) as src:
            base = src.convert("RGBA")
        eyes = find_eyes(base)
        self.assertIsNotNone(eyes)
        box = (0, 0, *base.size)
        painted = {
            name: apply_emote(base.copy(), name, 0.1, box, "leo", eyes)
            for name in EXPRESSION_COL
        }
        keys = list(painted)
        self.assertNotEqual(painted[keys[0]].tobytes(), painted[keys[1]].tobytes())
        self.assertNotEqual(painted["surprise"].tobytes(), painted["think"].tobytes())
        self.assertNotEqual(painted["laugh"].tobytes(), painted["listen"].tobytes())
        self.assertNotEqual(painted["concern"].tobytes(), painted["smile"].tobytes())

    def test_compose_emote_plus_lips(self) -> None:
        from open_tts.sprite import CharacterSheet, ensure_placeholder_sheet
        from open_tts.video import _compose_loop_frame

        if not loops_available():
            self.skipTest("talking loops not present")
        tmp = Path(tempfile.mkdtemp())
        try:
            sheet_path = tmp / "leo.png"
            ensure_placeholder_sheet(sheet_path, "leo")
            dest = tmp / "out.png"
            ok = _compose_loop_frame(
                speaker="leo",
                mode="full",
                sheet=CharacterSheet(sheet_path),
                line={"id": 1, "text": "father", "cue": "surprise", "duration": 1.2},
                t_in_line=0.35,
                frame_index=8,
                dest=dest,
                size=(736, 400),
                background=None,
                left_id="leo",
                right_id="eve",
            )
            self.assertTrue(ok)
            with Image.open(dest) as img:
                self.assertEqual(img.size, (736, 400))
        finally:
            for leftover in tmp.glob("*"):
                try:
                    leftover.unlink()
                except OSError:
                    pass
            try:
                tmp.rmdir()
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
