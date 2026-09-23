import tempfile
import unittest
from pathlib import Path
from unittest import mock

from open_tts.audio import SAMPLE_RATE
from open_tts.record import save_line_recording, write_pcm_wav
from open_tts.render import sentence_audio_paths


class TestLineRecording(unittest.TestCase):
    def test_save_line_recording_writes_sentence_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "take.wav"
            write_pcm_wav(src, b"\x00\x00" * (SAMPLE_RATE // 10))
            out = Path(tmp) / "show"
            _mp3, wav = save_line_recording(src, out, "leo", 1)
            self.assertTrue(wav.is_file())
            self.assertEqual(wav, sentence_audio_paths(out, "leo", 1)[1])
            self.assertGreater(wav.stat().st_size, 44)

    def test_render_uses_recorded_wav_without_tts(self) -> None:
        from open_tts.render import render_interview
        from open_tts.script import save_interview

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yaml_path = root / "interview.yaml"
            save_interview(
                {
                    "title": "Rec",
                    "characters": {"host": "leo", "guest": "eve"},
                    "layout": {"dual_start_turns": 0, "dual_end_turns": 0},
                    "script": [{"speaker": "leo", "text": "Hello from a take"}],
                },
                yaml_path,
            )
            out = root
            write_pcm_wav(
                sentence_audio_paths(out, "leo", 1)[1],
                b"\x00\x00" * (SAMPLE_RATE // 5),
            )
            with mock.patch("open_tts.tts.generate_speech") as gen, mock.patch(
                "open_tts.render.export_mp3_from_wav"
            ):
                result = render_interview(
                    yaml_path, output_dir=out, skip_tts=True, video=False
                )
            gen.assert_not_called()
            self.assertTrue((result / "full_interview.wav").is_file())


if __name__ == "__main__":
    unittest.main()
