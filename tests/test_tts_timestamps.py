import unittest

from open_tts.tts import _parse_timestamp_envelope
from open_tts.visemes import build_phone_intervals


class TestTtsTimestampEnvelope(unittest.TestCase):
    def test_parse_pairs_to_end_times(self):
        payload = {
            "audio": "AA==",
            "audio_timestamps": {
                "graph_chars": ["h", "i"],
                "graph_times": [[0.0, 0.1], [0.1, 0.2]],
            },
        }
        parsed = _parse_timestamp_envelope(payload)
        self.assertEqual(parsed["graph_chars"], ["h", "i"])
        self.assertEqual(parsed["graph_times"], [0.1, 0.2])

    def test_build_phone_intervals_uses_tts_timestamps_when_present(self):
        weighted = build_phone_intervals("beat", 1.0)
        aligned = build_phone_intervals(
            "beat",
            1.0,
            graph_chars=list("beat"),
            graph_times=[0.2, 0.4, 0.7, 1.0],
        )
        self.assertNotEqual(weighted, aligned)


if __name__ == "__main__":
    unittest.main()
