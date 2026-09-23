import tempfile
import unittest
from pathlib import Path

from PIL import Image

from open_tts.cartoon import draw_cartoon_still
from open_tts.loops import (
    build_viseme_loops,
    clip_slots,
    extract_loop_frames,
    find_eyes,
    find_native_mouth,
    frame_at,
    install_generated_video,
    list_character_clips,
    loop_frame_cache,
    looped_frames,
    loops_available,
    mouth_anchor,
    repo_root,
    resolve_clip,
    resolve_loop,
)
from open_tts.mouth import mouth_from_cell, mouth_shape, stamp_mouth


class TestVideoVisemes(unittest.TestCase):
    def test_resolve_original_loops(self) -> None:
        if not loops_available():
            self.skipTest("full/dual talking loops not present")
        self.assertTrue(resolve_loop("leo", "full").is_file())
        self.assertTrue(resolve_loop("eve", "split").name.startswith("dual_eve"))
        self.assertEqual(mouth_anchor("full", "leo")[0], 368)
        self.assertLess(mouth_anchor("split", "leo")[0], mouth_anchor("split", "eve")[0])

    def test_mouth_patch_stamps_onto_loop_frame(self) -> None:
        cell = Image.new("RGBA", (64, 64), (10, 10, 10, 255))
        for y in range(40, 56):
            for x in range(16, 48):
                cell.putpixel((x, y), (220, 40, 40, 255))
        mouth = mouth_from_cell(cell, (20, 14))
        self.assertEqual(mouth.size, (20, 14))
        self.assertEqual(mouth.getpixel((0, 0))[3], 0)
        self.assertGreater(mouth.getpixel((10, 7))[3], 0)
        frame = Image.new("RGBA", (80, 40), (0, 0, 80, 255))
        out = stamp_mouth(frame, mouth, (40, 20))
        self.assertGreater(out.getpixel((40, 20))[0], 150)

    def test_cartoon_open_mouth_is_white_not_skin(self) -> None:
        open_m = mouth_shape("a", (48, 32))
        rest = mouth_shape("pause", (48, 32))
        mid = open_m.getpixel((24, 16))
        self.assertGreater(mid[0], 200)
        self.assertGreater(mid[3], 0)
        self.assertNotEqual(open_m.tobytes(), rest.tobytes())

    def test_compose_loop_frame_when_present(self) -> None:
        from open_tts.sprite import CharacterSheet, ensure_placeholder_sheet
        from open_tts.video import _compose_loop_frame

        if not loops_available():
            self.skipTest("full/dual talking loops not present")
        tmp = Path(tempfile.mkdtemp())
        try:
            sheet_path = tmp / "leo.png"
            ensure_placeholder_sheet(sheet_path, "leo")
            dest = tmp / "out.png"
            ok = _compose_loop_frame(
                speaker="leo",
                mode="full",
                sheet=CharacterSheet(sheet_path),
                line={"id": 1, "text": "hello", "cue": ""},
                t_in_line=0.1,
                frame_index=3,
                dest=dest,
                size=(736, 400),
                background=None,
                left_id="leo",
                right_id="eve",
            )
            self.assertTrue(ok)
            self.assertTrue(dest.is_file())
            with Image.open(dest) as img:
                self.assertEqual(img.size, (736, 400))
                self.assertEqual(img.mode, "RGBA")
                self.assertEqual(img.getpixel((2, 2))[3], 0)
                sample = img.getpixel((368, 200))
                r, g, b = sample[:3]
                face = r < 80 and abs(r - g) < 25
                white = r > 200 and g > 200
                red = r > 180 and g < 80
                self.assertTrue(face or white or red, sample)
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

    def test_find_eyes_on_full_leo(self) -> None:
        if not loops_available():
            self.skipTest("full/dual talking loops not present")
        from open_tts.loops import frame_at

        loop = resolve_loop("leo", "full")
        with Image.open(frame_at(loop, 0)) as frame:
            eyes = find_eyes(frame)
        self.assertIsNotNone(eyes)
        left, right, ipd = eyes
        self.assertLess(left[0], right[0])
        self.assertGreater(ipd, 40)
        self.assertLess(abs(((left[0] + right[0]) // 2) - 368), 30)
        with Image.open(frame_at(loop, 59)) as open_frame:
            open_eyes = find_eyes(open_frame)
            self.assertIsNotNone(open_eyes)
            native = find_native_mouth(open_frame, open_eyes)
        self.assertIsNotNone(native)
        mx = (native[0] + native[2]) // 2
        my = (native[1] + native[3]) // 2
        self.assertLess(abs(mx - 368), 30)
        self.assertGreater(my, open_eyes[0][1] + 8)

    def test_body_loop_first_equals_last(self) -> None:
        if not loops_available():
            self.skipTest("full/dual talking loops not present")
        loop = resolve_loop("leo", "full")
        frames = extract_loop_frames(loop, loop_frame_cache(loop, repo_root()))
        playable = looped_frames(frames)
        self.assertEqual(playable[0], playable[-1])
        last = len(playable) - 1
        self.assertEqual(frame_at(loop, 0), frame_at(loop, last))

    def test_custom_person_gets_video_visemes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hero = root / "hero.png"
            draw_cartoon_still("navy jacket, red hair").save(hero)
            built = build_viseme_loops(hero, "sam", root, frames=6)
            self.assertIn("full", built)
            loop = resolve_loop("sam", "full", root)
            self.assertIsNotNone(loop)
            frames = extract_loop_frames(loop, loop_frame_cache(loop, root))
            self.assertGreaterEqual(len(frames), 2)
            with Image.open(frames[0]) as first, Image.open(frames[-1]) as last:
                self.assertEqual(first.size, (736, 400))
                self.assertEqual(first.tobytes(), last.tobytes())
                self.assertEqual(first.getpixel((2, 2))[3], 0)
                self.assertGreater(first.getpixel((368, 280))[3], 0)
            with Image.open(frames[0]) as frame:
                self.assertIsNotNone(find_eyes(frame))

    def test_install_one_clip_leaves_the_others(self) -> None:
        from open_tts.imagine import LocalImageProvider

        self.assertGreaterEqual(len(clip_slots()), 8)
        try:
            raw = LocalImageProvider().generate_video("teal jacket", slot="full")
        except RuntimeError as exc:
            self.skipTest(str(exc))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installed = install_generated_video(raw, "rio", root, slots=["full"])
            self.assertEqual(list(installed), ["full"])
            self.assertIsNotNone(resolve_clip("rio", "full", root))
            self.assertIsNone(resolve_clip("rio", "split", root))
            self.assertIsNone(resolve_clip("rio", "smile", root))
            clips = list_character_clips("rio", root)
            ready = {c["slot"]: c["ready"] for c in clips}
            self.assertTrue(ready["full"])
            self.assertFalse(ready["split"])
            smile = install_generated_video(raw, "rio", root, slots=["smile"])
            self.assertEqual(list(smile), ["smile"])
            self.assertIsNotNone(resolve_clip("rio", "smile", root))
            self.assertIsNone(resolve_clip("rio", "laugh", root))


if __name__ == "__main__":
    unittest.main()
