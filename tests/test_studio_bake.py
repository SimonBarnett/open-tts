import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from open_tts.imagine import LocalImageProvider
from open_tts.studio.character_wizard import CharacterWizard


class TestCharacterWizardBake(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_bake_requires_keep_locked_hero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            still = LocalImageProvider().generate_still("test hero", None)
            sheet_path = root / "characters" / "demo.png"

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


if __name__ == "__main__":
    unittest.main()
