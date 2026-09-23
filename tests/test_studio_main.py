import tempfile
import unittest
from pathlib import Path
from unittest import mock

from open_tts.studio.__main__ import main


class TestStudioMain(unittest.TestCase):
    def test_missing_timings_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = Path(tmp) / "show.yaml"
            yaml_path.write_text(
                "title: T\ncharacters: {host: leo, guest: eve}\nscript: []\n",
                encoding="utf-8",
            )
            code = main(["--edit", str(yaml_path)])
        self.assertEqual(code, 1)

    def test_invalid_path_returns_error(self):
        code = main(["--edit", "/nonexistent/path/xyz"])
        self.assertEqual(code, 1)

    def test_edit_launches_app_when_timings_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yaml_path = root / "show.yaml"
            out = root / "output" / "show"
            out.mkdir(parents=True)
            yaml_path.write_text(
                "title: T\ncharacters: {host: leo, guest: eve}\nscript: []\n",
                encoding="utf-8",
            )
            (out / "timings.json").write_text("[]", encoding="utf-8")
            with mock.patch(
                "open_tts.studio.__main__.run_edit_app", return_value=0
            ) as run:
                code = main(["--edit", str(yaml_path)])
            self.assertEqual(code, 0)
            run.assert_called_once()

    def test_editor_opens_interview_tab_for_yaml(self):
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from open_tts.studio.main_window import MainWindow

        QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["OPEN_TTS_PREFS_PATH"] = str(Path(tmp) / "prefs.json")
            yaml_path = Path(tmp) / "show.yaml"
            yaml_path.write_text(
                "title: FromReview\ncharacters: {host: leo, guest: eve}\n"
                "script: [{speaker: leo, text: Hi}]\n",
                encoding="utf-8",
            )
            win = MainWindow(yaml_path=yaml_path)
            self.assertEqual(win._script._path, yaml_path)
            self.assertEqual(win._script.title_edit.text(), "FromReview")
            self.assertEqual(win._tabs.currentWidget(), win._script)
            self.assertGreaterEqual(win._tabs.count(), 3)
            self.assertEqual(win._tabs.tabText(2), "Tutorials")

    def test_toolbar_has_separate_create_open_save(self):
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QToolBar

        from open_tts.studio.main_window import MainWindow

        QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["OPEN_TTS_PREFS_PATH"] = str(Path(tmp) / "prefs.json")
            os.environ["OPEN_TTS_PROJECTS_DIR"] = str(Path(tmp) / "projects")
            created = Path(tmp) / "created-show"
            created.mkdir()
            opened = Path(tmp) / "opened-show"
            opened.mkdir()
            (opened / "interview.yaml").write_text(
                "title: Existing\ncharacters: {host: leo, guest: eve}\nscript: []\n",
                encoding="utf-8",
            )
            win = MainWindow()
            labels = [a.text() for bar in win.findChildren(QToolBar) for a in bar.actions()]
            self.assertEqual(labels[:3], ["Create", "Open", "Save"])
            with mock.patch(
                "open_tts.studio.script_editor.QFileDialog.getExistingDirectory",
                return_value=str(created),
            ):
                win._create_folder()
            self.assertTrue((created / "interview.yaml").is_file())
            self.assertTrue((created / "sentences").is_dir())
            self.assertEqual(win._script._path.resolve(), (created / "interview.yaml").resolve())
            with mock.patch(
                "open_tts.studio.script_editor.QFileDialog.getExistingDirectory",
                return_value=str(opened),
            ):
                win._open_folder()
            self.assertEqual(win._script._path.resolve(), (opened / "interview.yaml").resolve())
            self.assertEqual(win._script.title_edit.text(), "Existing")
            win._script.title_edit.setText("Renamed")
            win._save()
            self.assertIn("Renamed", (opened / "interview.yaml").read_text(encoding="utf-8"))
            self.assertEqual(win._tabs.currentWidget(), win._script)

    def test_review_without_mixdown_does_not_crash(self):
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from open_tts.audio import media_duration
        from open_tts.studio.app import run_edit_app
        from open_tts.studio.project import StudioProject

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "full_interview.mp3"
            self.assertEqual(media_duration(missing), 0.0)
            yaml_path = root / "interview.yaml"
            yaml_path.write_text(
                "title: T\ncharacters: {host: leo, guest: eve}\n"
                "script:\n  - {speaker: leo, text: Hi}\n",
                encoding="utf-8",
            )
            (root / "timings.json").write_text(
                '[{"id":1,"speaker":"leo","text":"Hi","start":0,"end":1.5}]\n',
                encoding="utf-8",
            )
            project = StudioProject(yaml_path=yaml_path, output_dir=root)
            code = run_edit_app(project)
            self.assertEqual(code, 0)
            win = getattr(app, "_review_window", None)
            self.assertIsNotNone(win)
            win.close()


if __name__ == "__main__":
    unittest.main()
