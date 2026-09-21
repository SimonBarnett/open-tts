import unittest

from open_tts.srt import format_srt_time


class TestSrtTime(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(format_srt_time(0), "00:00:00,000")

    def test_ms_never_1000(self):
        self.assertEqual(format_srt_time(1.9995), "00:00:02,000")
        self.assertEqual(format_srt_time(59.9996), "00:01:00,000")

    def test_fractional(self):
        self.assertEqual(format_srt_time(1.5), "00:00:01,500")


if __name__ == "__main__":
    unittest.main()
