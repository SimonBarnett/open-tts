import base64
import json
import unittest

from open_tts.tts import decode_tts_response
from open_tts.visemes import build_phone_intervals


class TestTtsDecode(unittest.TestCase):
    def test_decode_json_envelope_with_timestamps(self):
        audio = b"\xff\xfb\x90"
        payload = {
            "audio": base64.b64encode(audio).decode("ascii"),
            "audio_timestamps": {
                "graph_chars": ["b", "e", "a", "t"],
                "graph_times": [[0.0, 0.1], [0.1, 0.2], [0.2, 0.5], [0.5, 0.8]],
            },
        }
        body = json.dumps(payload).encode("utf-8")
        decoded, meta = decode_tts_response(body)
        self.assertEqual(decoded, audio)
        self.assertIsNotNone(meta)
        self.assertEqual(meta["graph_chars"], ["b", "e", "a", "t"])

    def test_decode_raw_mp3_bytes(self):
        raw = b"\xff\xfb\x90\x00"
        decoded, meta = decode_tts_response(raw)
        self.assertEqual(decoded, raw)
        self.assertIsNone(meta)


class TestTimestampAlignment(unittest.TestCase):
    def test_prefers_tts_timestamps_over_weighted_slice(self):
        weighted = build_phone_intervals("beat", 1.0)
        aligned = build_phone_intervals(
            "beat",
            1.0,
            graph_chars=["b", "e", "a", "t"],
            graph_times=[[0.0, 0.1], [0.1, 0.2], [0.2, 0.6], [0.6, 1.0]],
        )
        self.assertNotEqual(weighted, aligned)
        self.assertTrue(aligned)
        self.assertAlmostEqual(aligned[-1]["t1"], 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
