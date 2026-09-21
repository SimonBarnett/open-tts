import unittest

from open_tts.cues import AUTO, suggest_cue, cue_to_yaml_value, validate_cue


class TestSuggestCue(unittest.TestCase):
    def test_partner_thank_you_line_suggests_smile(self):
        text = "Thank you Leo, it's great to be here."
        self.assertEqual(suggest_cue(text), "smile")

    def test_partner_enthusiasm_line_suggests_laugh(self):
        text = "There's always a bit of sales enthusiasm!"
        self.assertEqual(suggest_cue(text), "laugh")

    def test_listener_and_empty_text_suggest_listen(self):
        self.assertEqual(suggest_cue("", is_listener=True), "listen")
        self.assertEqual(suggest_cue("…"), "listen")
        self.assertEqual(suggest_cue("   "), "listen")

    def test_unknown_wording_returns_auto(self):
        self.assertEqual(suggest_cue("Let's start with the basics."), "auto")


class TestValidateCue(unittest.TestCase):
    def test_accepts_expression_and_pause(self):
        validate_cue("smile")
        validate_cue("pause")

    def test_rejects_unknown_cue(self):
        with self.assertRaises(ValueError) as ctx:
            validate_cue("wink")
        self.assertIn("wink", str(ctx.exception))


class TestStudioYamlCue(unittest.TestCase):
    def test_auto_omits_cue_in_yaml(self):
        self.assertIsNone(cue_to_yaml_value(AUTO))
        self.assertEqual(cue_to_yaml_value("pause"), "pause")


if __name__ == "__main__":
    unittest.main()
