import tempfile
import unittest
from pathlib import Path
from unittest import mock

from open_tts.script import apply_line_to_script, load_interview, save_interview


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
