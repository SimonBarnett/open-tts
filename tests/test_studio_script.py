import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import yaml
from PySide6.QtWidgets import QApplication

from open_tts.cues import AUTO, suggest_cue
from open_tts.script import apply_line_to_script, load_interview, save_interview
from open_tts.studio.script_editor import ScriptEditor


class TestScriptSave(unittest.TestCase):
    def test_apply_and_save_preserves_schema(self):
        data = {
            "title": "T",
            "characters": {"host": "leo", "guest": "eve"},
            "layout": {"dual_start_turns": 4, "dual_end_turns": 5},
            "script": [
                {"speaker": "leo", "text": "Hello"},
                {"speaker": "eve", "text": "Hi", "cue": "laugh"},
            ],
        }
        apply_line_to_script(
            data, 1, speaker="eve", text="Hi there", cue="smile"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "interview.yaml"
            save_interview(data, path)
            loaded = load_interview(path)
        self.assertEqual(loaded["script"][1]["text"], "Hi there")
        self.assertEqual(loaded["script"][1]["cue"], "smile")


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


class TestInvalidateSentenceAudio(unittest.TestCase):
    def test_speaker_change_removes_both_caches(self):
        from open_tts.render import invalidate_sentence_audio, sentence_audio_paths

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "sentences").mkdir()
            for sp in ("leo", "eve"):
                mp3, wav = sentence_audio_paths(out, sp, 1)
                mp3.write_bytes(b"mp3")
                wav.write_bytes(b"wav")
            invalidate_sentence_audio(out, 1, "leo", "eve")
            self.assertFalse(sentence_audio_paths(out, "leo", 1)[0].is_file())
            self.assertFalse(sentence_audio_paths(out, "eve", 1)[0].is_file())


class TestTtsReuse(unittest.TestCase):
    def test_existing_mp3_skips_tts(self):
        from open_tts.tts import ensure_sentence_audio

        with tempfile.TemporaryDirectory() as tmp:
            mp3 = Path(tmp) / "leo_001.mp3"
            mp3.write_bytes(b"fake")
            with mock.patch("open_tts.tts.generate_speech") as gen:
                ensure_sentence_audio("text", "leo", mp3, skip_tts=False)
                gen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
