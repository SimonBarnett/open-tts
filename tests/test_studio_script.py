import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import yaml
from PySide6.QtWidgets import QApplication

from open_tts.cues import AUTO, suggest_cue
from open_tts.studio.script_editor import ScriptEditor


class TestScriptEditorCues(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_partner_enthusiasm_suggests_laugh_and_pause_override_saves(self) -> None:
        line = "There's always a bit of sales enthusiasm!"
        self.assertEqual(suggest_cue(line), "laugh")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yaml_path = root / "draft.yaml"
            editor = ScriptEditor()
            editor._path = yaml_path
            editor._suppress_suggest = True
            editor.title_edit.setText("Test")
            editor.table.setRowCount(0)
            editor._append_row("eve", line, suggest_cue(line), "")
            editor._renumber()
            editor._suppress_suggest = False

            anim_w = editor.table.cellWidget(0, editor.COL_ANIM)
            self.assertIsNotNone(anim_w)
            self.assertEqual(anim_w.currentText(), "laugh")

            anim_w.setCurrentText("pause")
            editor._write_yaml(yaml_path)
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            self.assertEqual(data["script"][0]["cue"], "pause")

            editor._suppress_suggest = True
            editor.table.setRowCount(0)
            editor._append_row("eve", line, AUTO, "")
            editor._renumber()
            editor._suppress_suggest = False
            editor._on_cell_changed(0, editor.COL_TEXT)
            anim_w = editor.table.cellWidget(0, editor.COL_ANIM)
            self.assertEqual(anim_w.currentText(), "laugh")


if __name__ == "__main__":
    unittest.main()
