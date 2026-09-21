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


if __name__ == "__main__":
    unittest.main()
