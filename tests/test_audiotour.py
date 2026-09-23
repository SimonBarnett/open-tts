import json
import tempfile
import unittest
from pathlib import Path

from open_tts.audiotour import (
    apply_take,
    encode_audio_b64,
    has_real_audio,
    list_tours,
    load_tour,
    message_text,
    preferred_tour_file,
    save_processed,
)
from open_tts.record import write_pcm_wav


class TestAudiotourTakes(unittest.TestCase):
    def test_apply_take_sets_real_base64_and_keeps_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "demo-audiotour.json"
            src.write_text(
                json.dumps(
                    {
                        "widget": "demo",
                        "messages": [
                            {
                                "id": 0,
                                "dialog-text": "Welcome to the tutorial.",
                                "base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEA",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            wav = root / "step.wav"
            write_pcm_wav(wav, b"\x00\x00" * 2400)
            data = load_tour(src)
            self.assertFalse(has_real_audio(data["messages"][0]))
            apply_take(data, 0, wav)
            self.assertTrue(has_real_audio(data["messages"][0]))
            self.assertEqual(data["messages"][0]["base64"], encode_audio_b64(wav))
            dest = save_processed(src, data, root)
            self.assertEqual(dest, root / "processed" / "demo-audiotour.json")
            self.assertTrue(dest.is_file())
            original = json.loads(src.read_text(encoding="utf-8"))
            self.assertFalse(has_real_audio(original["messages"][0]))
            self.assertEqual(message_text(data["messages"][0]), "Welcome to the tutorial.")
            self.assertEqual(preferred_tour_file(src, root), dest)

    def test_list_tours_finds_repo_files(self) -> None:
        tours = list_tours()
        names = {p.name for p in tours}
        self.assertIn("categories-widget-audiotour.json", names)


if __name__ == "__main__":
    unittest.main()
