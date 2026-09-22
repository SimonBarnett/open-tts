import os
import tempfile
import unittest
from pathlib import Path

from open_tts.prefs import (
    last_cast,
    last_hero,
    last_heroes,
    last_model,
    last_project,
    remember_cast,
    remember_hero,
    remember_hero_for,
    remember_model,
    remember_project,
)


class TestPrefs(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.prefs = Path(self._tmpdir.name) / "prefs.json"
        self._old = os.environ.get("OPEN_TTS_PREFS_PATH")
        os.environ["OPEN_TTS_PREFS_PATH"] = str(self.prefs)

    def tearDown(self) -> None:
        if self._old is None:
            os.environ.pop("OPEN_TTS_PREFS_PATH", None)
        else:
            os.environ["OPEN_TTS_PREFS_PATH"] = self._old

    def test_last_cast_defaults_leo_eve(self) -> None:
        self.assertEqual(last_cast(), ("leo", "eve"))

    def test_remember_cast(self) -> None:
        remember_cast("eve", "leo")
        self.assertEqual(last_cast(), ("eve", "leo"))

    def test_remember_project(self) -> None:
        path = Path(self._tmpdir.name) / "interview.yaml"
        remember_project(path)
        self.assertEqual(last_project(), str(path))

    def test_remember_model(self) -> None:
        self.assertIsNone(last_model())
        remember_model("eve")
        self.assertEqual(last_model(), "eve")

    def test_remember_hero(self) -> None:
        path = Path(self._tmpdir.name) / "eve.png"
        remember_hero(path)
        self.assertEqual(last_hero(), str(path))

    def test_remember_hero_per_model(self) -> None:
        leo = Path(self._tmpdir.name) / "leo.png"
        eve = Path(self._tmpdir.name) / "eve.png"
        leo.write_bytes(b"l")
        eve.write_bytes(b"e")
        remember_hero_for("leo", leo)
        remember_hero_for("eve", eve)
        self.assertEqual(last_heroes()["leo"], str(leo))
        self.assertEqual(last_heroes()["eve"], str(eve))


if __name__ == "__main__":
    unittest.main()
