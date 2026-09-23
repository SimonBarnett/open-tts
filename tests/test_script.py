import unittest

from open_tts.script import (
    SCREEN_FULL,
    SCREEN_SPLIT,
    apply_cast_overrides,
    normalized_lines,
    screen_from_entry,
    split_yaml_value,
)


class TestScriptCues(unittest.TestCase):
    def test_unknown_cue_fails_at_load(self):
        data = {
            "title": "t",
            "characters": {"host": "leo", "guest": "eve"},
            "script": [{"speaker": "leo", "text": "Hi", "cue": "wink"}],
        }
        with self.assertRaises(ValueError):
            normalized_lines(data)

    def test_split_flag_round_trips_on_lines(self):
        data = {
            "title": "t",
            "characters": {"host": "leo", "guest": "eve"},
            "script": [
                {"speaker": "leo", "text": "Hi", "split": True},
                {"speaker": "eve", "text": "Hello", "split": False},
                {"speaker": "leo", "text": "Auto"},
            ],
        }
        lines = normalized_lines(data)
        self.assertTrue(lines[0]["split"])
        self.assertFalse(lines[1]["split"])
        self.assertNotIn("split", lines[2])

    def test_screen_helpers(self):
        self.assertEqual(screen_from_entry({"split": True}), SCREEN_SPLIT)
        self.assertEqual(screen_from_entry({"split": False}), SCREEN_FULL)
        self.assertEqual(screen_from_entry({}), "auto")
        self.assertTrue(split_yaml_value("split"))
        self.assertFalse(split_yaml_value("full"))
        self.assertIsNone(split_yaml_value("auto"))

    def test_cast_override_replaces_and_inherits(self):
        lines = [
            {"speaker": "leo", "text": "a"},
            {"speaker": "eve", "text": "b"},
            {"speaker": "maria", "text": "c", "right": "maria"},
            {"speaker": "leo", "text": "d"},
        ]
        staged = apply_cast_overrides(lines, "leo", "eve")
        self.assertEqual(staged[0]["_left"], "leo")
        self.assertEqual(staged[0]["_right"], "eve")
        self.assertEqual(staged[2]["_right"], "maria")
        self.assertEqual(staged[3]["_right"], "maria")
        self.assertEqual(staged[3]["_left"], "leo")

    def test_swap_flips_sides_from_that_line(self):
        lines = [
            {"speaker": "leo", "text": "a"},
            {"speaker": "eve", "text": "b", "swap": True},
            {"speaker": "leo", "text": "c"},
        ]
        staged = apply_cast_overrides(lines, "leo", "eve")
        self.assertEqual((staged[0]["_left"], staged[0]["_right"]), ("leo", "eve"))
        self.assertEqual((staged[1]["_left"], staged[1]["_right"]), ("eve", "leo"))
        self.assertEqual((staged[2]["_left"], staged[2]["_right"]), ("eve", "leo"))


if __name__ == "__main__":
    unittest.main()
