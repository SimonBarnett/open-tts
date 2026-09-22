import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from open_tts.imagine import LocalImageProvider
from open_tts.sprite import COLS, PREVIEW_ROWS
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

    def test_bake_requires_keep_locked_hero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            still = LocalImageProvider().generate_still("test hero", None)
            sheet_path = root / "characters" / "visemes" / "demo.png"

            wizard = CharacterWizard()
            wizard.id_edit.setText("demo")
            wizard._history.append(still)
            wizard._locked_hero = None
            wizard._provider = LocalImageProvider()

            with patch(
                "open_tts.studio.character_wizard.repo_root", return_value=root
            ), patch(
                "open_tts.studio.character_wizard.QMessageBox.information"
            ), patch(
                "open_tts.studio.character_wizard.QMessageBox.warning"
            ):
                wizard._on_bake()
                self.assertFalse(sheet_path.is_file())

                wizard._locked_hero = still
                wizard._on_bake()
                self.assertTrue(sheet_path.is_file())
                self.assertEqual(len(wizard._sheet_cells), COLS * PREVIEW_ROWS)
                for cell in wizard._sheet_cells:
                    self.assertFalse(cell.pixmap().isNull())

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

    def test_last_model_reloads_until_back(self) -> None:
        from open_tts.characters import load_registry
        from open_tts.prefs import remember_model

        ids = load_registry()
        if "eve" not in ids:
            self.skipTest("eve not in registry")
        remember_model("eve")
        wizard = CharacterWizard()
        self.assertEqual(wizard.stack.currentWidget(), wizard.editor_page)
        self.assertEqual(wizard.id_edit.text(), "eve")
        wizard._show_picker()
        self.assertEqual(wizard.stack.currentWidget(), wizard.picker_page)
        if "leo" in ids:
            wizard._enter_model("leo")
            self.assertEqual(wizard.id_edit.text(), "leo")
            again = CharacterWizard()
            self.assertEqual(again.id_edit.text(), "leo")
            self.assertEqual(again.stack.currentWidget(), again.editor_page)


if __name__ == "__main__":
    unittest.main()
