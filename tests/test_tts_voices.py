import os
import unittest
from unittest.mock import patch

from open_tts.tts import BUILTIN_TTS_VOICES, documented_tts_voices, list_tts_voices


class TestTtsVoices(unittest.TestCase):
    def test_documented_catalog_matches_live_lookup(self) -> None:
        ids = [voice_id for voice_id, _name in BUILTIN_TTS_VOICES]
        names = {voice_id: name for voice_id, name in BUILTIN_TTS_VOICES}
        self.assertEqual(len(ids), 28)
        self.assertEqual(len(set(ids)), 28)
        for voice_id in ("eve", "leo", "ara", "rex", "sal", "aurora", "liora"):
            self.assertIn(voice_id, ids)
        self.assertEqual(names["eve"], "Eve")
        self.assertEqual(names["leo"], "Leo")
        documented = documented_tts_voices()
        self.assertEqual([v["voice_id"] for v in documented], ids)

    def test_list_without_key_uses_documented_catalog(self) -> None:
        import open_tts.tts as tts

        tts._VOICES_CACHE = None
        with patch.dict(os.environ, {"XAI_API_KEY": ""}, clear=False):
            os.environ.pop("XAI_API_KEY", None)
            with patch("open_tts.tts.load_repo_env"):
                voices = list_tts_voices(refresh=True)
        ids = {v["voice_id"] for v in voices}
        self.assertEqual(ids, {voice_id for voice_id, _ in BUILTIN_TTS_VOICES})
        tts._VOICES_CACHE = None
