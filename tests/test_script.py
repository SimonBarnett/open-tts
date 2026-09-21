import unittest

from open_tts.script import normalized_lines


class TestScriptCues(unittest.TestCase):
    def test_unknown_cue_fails_at_load(self):
        data = {
            "title": "t",
            "characters": {"host": "leo", "guest": "eve"},
            "script": [{"speaker": "leo", "text": "Hi", "cue": "wink"}],
        }
        with self.assertRaises(ValueError):
            normalized_lines(data)


if __name__ == "__main__":
    unittest.main()
