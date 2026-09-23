import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from open_tts.imagine import LocalImageProvider
from open_tts.studio.character_wizard import CharacterWizard


class TestCharacterWizardBake(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._prefs_dir = tempfile.TemporaryDirectory()
        os.environ["OPEN_TTS_PREFS_PATH"] = str(Path(cls._prefs_dir.name) / "prefs.json")
        cls._app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls) -> None:
        cls._prefs_dir.cleanup()

    def test_no_mouth_sheet_ui(self) -> None:
        wizard = CharacterWizard()
        self.assertFalse(hasattr(wizard, "bake_btn"))
        self.assertFalse(hasattr(wizard, "_sheet_cells"))
        self.assertFalse(hasattr(wizard, "still_label"))
        self.assertFalse(hasattr(wizard, "viseme_combo"))
        self.assertFalse(hasattr(wizard, "gen_btn"))
        self.assertEqual(
            wizard.clip_list.contextMenuPolicy(),
            Qt.ContextMenuPolicy.CustomContextMenu,
        )
        self.assertEqual(wizard.full_frame_label.size().width(), 276)
        self.assertEqual(wizard.full_frame_label.size().height(), 150)
        self.assertEqual(wizard.split_left_label.size().width(), 138)
        self.assertEqual(wizard.split_left_label.size().height(), 150)
        self.assertAlmostEqual(276 / 150, 736 / 400, places=2)
        wizard.hide()

    def test_keep_copies_face_out_of_temp(self) -> None:
        from open_tts.imagine import LocalImageProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            still = LocalImageProvider().generate_still("kept hero", None)
            wizard = CharacterWizard()
            wizard.id_edit.setText("eve")
            wizard._history.append(still)
            registry = {"eve": {"voice_id": "eve", "sheet": "characters/eve.png"}}
            with patch(
                "open_tts.studio.character_wizard.repo_root", return_value=root
            ), patch(
                "open_tts.studio.character_wizard.load_registry", return_value=registry
            ), patch(
                "open_tts.studio.character_wizard.save_registry"
            ) as save, patch(
                "open_tts.studio.character_wizard.QMessageBox.information"
            ):
                wizard._on_keep()
            dest = root / "characters" / "heroes" / "eve.png"
            self.assertTrue(dest.is_file())
            self.assertGreater(dest.stat().st_size, 0)
            self.assertEqual(wizard._locked_hero.resolve(), dest.resolve())
            self.assertEqual(registry["eve"]["hero"], "characters/heroes/eve.png")
            save.assert_called()

    def test_generate_saves_per_model_and_reload_finds_it(self) -> None:
        from open_tts.characters import persist_hero, resolve_hero
        from open_tts.imagine import LocalImageProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leo_still = LocalImageProvider().generate_still("leo face", None)
            eve_still = LocalImageProvider().generate_still("eve face", None)
            persist_hero(leo_still, "leo", root)
            persist_hero(eve_still, "eve", root)
            self.assertIsNotNone(resolve_hero("leo", {}, root=root))
            self.assertIsNotNone(resolve_hero("eve", {}, root=root))
            self.assertNotEqual(
                resolve_hero("leo", {}, root=root),
                resolve_hero("eve", {}, root=root),
            )
            wizard = CharacterWizard()
            with patch(
                "open_tts.studio.character_wizard.repo_root", return_value=root
            ), patch(
                "open_tts.studio.character_wizard.load_registry",
                return_value={
                    "leo": {"voice_id": "leo"},
                    "eve": {"voice_id": "eve"},
                },
            ):
                wizard._load_hero_for("leo", {})
                self.assertIsNotNone(wizard._locked_hero)
                self.assertEqual(wizard._locked_hero.name, "leo.png")
                wizard._load_hero_for("eve", {})
                self.assertEqual(wizard._locked_hero.name, "eve.png")

    def test_resolve_hero_falls_back_to_original_leo_eve(self) -> None:
        from open_tts.characters import persist_hero, resolve_hero
        from open_tts.imagine import LocalImageProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leo = resolve_hero("leo", {}, root=root)
            eve = resolve_hero("eve", {}, root=root)
            self.assertIsNotNone(leo)
            self.assertIsNotNone(eve)
            self.assertTrue(leo.is_file())
            self.assertTrue(eve.is_file())
            self.assertGreater(leo.stat().st_size, 200)
            self.assertEqual(leo.name, "leo.png")
            self.assertIn("defaults", leo.parts)
            self.assertNotEqual(leo, eve)
            custom = LocalImageProvider().generate_still("custom leo", None)
            kept = persist_hero(custom, "leo", root)
            self.assertEqual(resolve_hero("leo", {}, root=root), kept.resolve())

    def test_resolve_hero_uses_original_viseme_face(self) -> None:
        from PIL import Image

        from open_tts.characters import resolve_hero
        from open_tts.sprite import COLS, DEFAULT_CELL_PX, VISEME_COL

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            viseme = root / "characters" / "visemes" / "leo.png"
            viseme.parent.mkdir(parents=True)
            img = Image.new(
                "RGBA",
                (COLS * DEFAULT_CELL_PX, 9 * DEFAULT_CELL_PX),
                (8, 8, 8, 255),
            )
            col = VISEME_COL["pause"]
            for y in range(DEFAULT_CELL_PX):
                for x in range(col * DEFAULT_CELL_PX, (col + 1) * DEFAULT_CELL_PX):
                    img.putpixel((x, y), (210, 30, 30, 255))
            img.save(viseme)
            path = resolve_hero("leo", {}, root=root)
            self.assertIsNotNone(path)
            face = Image.open(path).convert("RGBA")
            px = face.getpixel((face.width // 2, face.height // 2))
            self.assertGreater(px[0], 150)
            self.assertLess(px[1], 80)

    def test_last_model_reloads_until_back(self) -> None:
        from open_tts.characters import load_registry
        from open_tts.prefs import remember_model

        ids = load_registry()
        if "eve" not in ids:
            self.skipTest("eve not in registry")
        remember_model("eve")
        wizard = CharacterWizard()
        self.assertEqual(wizard.id_edit.text(), "eve")
        self.assertFalse(wizard.customize_box.isVisible())
        wizard._show_picker()
        self.assertFalse(wizard.customize_box.isVisible())
        if "leo" in ids:
            wizard._enter_model("leo")
            self.assertEqual(wizard.id_edit.text(), "leo")
            again = CharacterWizard()
            self.assertEqual(again.id_edit.text(), "leo")

    def test_full_and_split_frame_previews(self) -> None:
        from open_tts.characters import resolve_hero

        wizard = CharacterWizard()
        path = resolve_hero("leo", {})
        if path is None:
            self.skipTest("no leo default")
        wizard.id_edit.setText("leo")
        wizard._show_still(path)
        self.assertFalse(wizard.full_frame_label.pixmap().isNull())
        self.assertFalse(wizard.split_left_label.pixmap().isNull())
        self.assertFalse(wizard.split_right_label.pixmap().isNull())
        full = wizard.full_frame_label.pixmap()
        self.assertAlmostEqual(full.width() / full.height(), 736 / 400, places=2)
        left = wizard.split_left_label.pixmap()
        self.assertEqual(left.width() * 2, full.width())
        self.assertEqual(left.height(), full.height())

    def test_new_face_and_clip_still_use_stage_previews(self) -> None:
        from PIL import Image

        wizard = CharacterWizard()
        still = LocalImageProvider().generate_still("navy jacket red hair", None)
        wizard._show_still(still)
        self.assertFalse(wizard.full_frame_label.pixmap().isNull())
        self.assertFalse(wizard.split_left_label.pixmap().isNull())
        self.assertFalse(wizard.split_right_label.pixmap().isNull())
        full = wizard.full_frame_label.pixmap()
        self.assertAlmostEqual(full.width() / full.height(), 736 / 400, places=2)

        with tempfile.TemporaryDirectory() as tmp:
            plate = Path(tmp) / "aa_sam.png"
            Image.new("RGBA", (736, 400), (40, 180, 90, 255)).save(plate)
            wizard._show_still(plate)
            stage = wizard.full_frame_label.pixmap()
            self.assertEqual(stage.width(), 368)
            self.assertEqual(stage.height(), 200)
            half = wizard.split_left_label.pixmap()
            self.assertEqual(half.width(), 184)
            self.assertEqual(half.height(), 200)

    def test_default_stage_stills_from_original(self) -> None:
        from open_tts.characters import (
            ensure_default_stage_stills,
            native_stage_kind,
            resolve_stage_still,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            viseme = Path(__file__).resolve().parent.parent / "characters" / "visemes"
            if not (viseme / "leo.png").is_file():
                self.skipTest("original viseme sheets not present")
            dest = root / "characters" / "visemes"
            dest.mkdir(parents=True)
            (dest / "leo.png").write_bytes((viseme / "leo.png").read_bytes())
            (dest / "eve.png").write_bytes((viseme / "eve.png").read_bytes())
            baked = ensure_default_stage_stills(root)
            self.assertIn("leo", baked)
            self.assertIn("eve", baked)
            self.assertTrue(baked["leo"]["full"].is_file())
            self.assertTrue(baked["eve"]["left"].is_file())
            self.assertTrue(baked["eve"]["right"].is_file())
            self.assertEqual(native_stage_kind("leo", root), "full")
            self.assertEqual(native_stage_kind("eve", root), "right")
            leo_full = resolve_stage_still("leo", "full", root=root)
            eve_right = resolve_stage_still("eve", "right", root=root)
            self.assertIsNotNone(leo_full)
            self.assertIsNotNone(eve_right)
            self.assertIn("leo_full", leo_full.name)
            self.assertIn("eve_right", eve_right.name)

    def test_voice_combo_lists_official_voices(self) -> None:
        wizard = CharacterWizard()
        self.assertGreaterEqual(wizard.voice_combo.count(), 20)
        self.assertNotEqual(wizard.voice_combo.findData("eve"), -1)
        self.assertNotEqual(wizard.voice_combo.findData("leo"), -1)
        self.assertNotEqual(wizard.voice_combo.findData("ara"), -1)
        wizard._fill_voice_combo("leo")
        self.assertEqual(wizard._selected_voice_id(), "leo")

    def test_new_person_button_opens_customize(self) -> None:
        wizard = CharacterWizard()
        wizard.show()
        self.assertTrue(hasattr(wizard, "new_btn"))
        self.assertEqual(wizard.new_btn.text(), "New person")
        self.assertEqual(wizard.face_btn.text(), "New face")
        self.assertEqual(wizard.keep_btn.text(), "Approve face")
        self.assertFalse(hasattr(wizard, "gen_btn"))
        self.assertGreaterEqual(wizard.clip_list.count(), 8)
        wizard.clip_list.setCurrentRow(3)
        self.assertTrue(wizard._selected_slot())
        wizard._on_new_model()
        self.assertTrue(wizard.customize_btn.isChecked())
        self.assertTrue(wizard.customize_box.isVisible())
        self.assertEqual(wizard.current_model_label.text(), "New person")
        self.assertFalse(wizard._face_approved)
        wizard.name_edit.setText("Sam Navy")
        wizard.prompt_edit.setPlainText("navy jacket, red hair")
        self.assertEqual(wizard._ensure_id(), "sam-navy")
        self.assertEqual(wizard.id_edit.text(), "sam-navy")
        wizard.hide()

    def test_entering_a_model_does_not_autoplay(self) -> None:
        from unittest.mock import MagicMock

        from open_tts.characters import load_registry

        wizard = CharacterWizard()
        wizard._player = MagicMock()
        wizard._player_out = MagicMock()
        ids = load_registry()
        who = "eve" if "eve" in ids else next(iter(ids), "leo")
        wizard._on_model_picked(who)
        wizard._player.play.assert_not_called()
        wizard._stop_video()
        wizard._player.stop.assert_called()
        wizard.hide()

    def test_video_waits_until_face_is_approved(self) -> None:
        wizard = CharacterWizard()
        wizard._face_approved = False
        wizard._locked_hero = None
        with patch("open_tts.studio.character_wizard.QMessageBox.information") as info:
            wizard._on_generate()
        info.assert_called()
        self.assertIsNone(wizard._gen_thread)
        still = LocalImageProvider().generate_still("navy jacket", None)
        wizard._history.append(still)
        wizard.id_edit.setText("sam")
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "open_tts.studio.character_wizard.repo_root", return_value=Path(tmp)
            ), patch(
                "open_tts.studio.character_wizard.load_registry", return_value={}
            ), patch(
                "open_tts.studio.character_wizard.save_registry"
            ), patch(
                "open_tts.studio.character_wizard.QMessageBox.information"
            ):
                wizard._on_keep()
        self.assertTrue(wizard._face_approved)
        wizard.hide()


if __name__ == "__main__":
    unittest.main()
