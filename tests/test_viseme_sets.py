import tempfile
import unittest
from pathlib import Path

from open_tts.viseme_sets import (
    DEFAULT_VISEME_SET,
    NONE_MODEL,
    characters_to_sides,
    ensure_default_viseme_set,
    list_viseme_sets,
    sides_to_characters,
    viseme_set_path,
)


class TestVisemeSets(unittest.TestCase):
    def test_default_set_is_created_and_listed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = ensure_default_viseme_set(root)
            self.assertTrue(path.is_file())
            self.assertEqual(path, viseme_set_path(DEFAULT_VISEME_SET, root))
            self.assertIn(DEFAULT_VISEME_SET, list_viseme_sets(root))

    def test_sides_both_one_or_other(self) -> None:
        self.assertEqual(
            sides_to_characters("leo", "eve"),
            {"host": "leo", "guest": "eve"},
        )
        self.assertEqual(
            sides_to_characters("leo", NONE_MODEL),
            {"host": "leo", "guest": "leo"},
        )
        self.assertEqual(
            sides_to_characters(NONE_MODEL, "eve"),
            {"host": "eve", "guest": "eve"},
        )

    def test_characters_to_sides_solo_uses_none(self) -> None:
        left, right = characters_to_sides({"host": "leo", "guest": "leo"})
        self.assertEqual(left, "leo")
        self.assertEqual(right, NONE_MODEL)


if __name__ == "__main__":
    unittest.main()
