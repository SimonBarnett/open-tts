import unittest

from open_tts.visemes import (
    build_phone_intervals,
    sheet_viseme,
    text_to_phones,
    viseme_at_time,
)
from open_tts.sprite import viseme_sequence_for_text


class TestG2P(unittest.TestCase):
    def test_vault_phones_include_v_and_ao(self):
        phones = text_to_phones("vault")
        bases = {p.rstrip("012") for p in phones}
        self.assertIn("V", bases)
        self.assertIn("AO", bases)

    def test_beat_has_iy(self):
        phones = text_to_phones("beat")
        self.assertIn("IY", {p.rstrip("012") for p in phones})

    def test_map_has_m(self):
        phones = text_to_phones("map")
        self.assertIn("M", {p.rstrip("012") for p in phones})


class TestPhoneIntervals(unittest.TestCase):
    def test_beat_iy_interval_viseme_is_i(self):
        intervals = build_phone_intervals("beat", 1.0)
        iy = [p for p in intervals if p["phone"] == "IY"]
        self.assertTrue(iy)
        self.assertEqual(iy[0]["viseme"], "i")

    def test_map_has_mbp_interval(self):
        intervals = build_phone_intervals("map", 1.0)
        m = [p for p in intervals if p["phone"] == "M"]
        self.assertTrue(m)
        self.assertEqual(m[0]["viseme"], "mbp")

    def test_vault_track_not_spelling_vowel_cycle(self):
        intervals = build_phone_intervals("vault", 1.0)
        spelling = viseme_sequence_for_text("vault")
        self.assertEqual(spelling, ["a", "u"])
        # Spelling cycle at 6 Hz alternates a/u; phoneme track should not.
        samples = [viseme_at_time(intervals, t) for t in (0.05, 0.15, 0.25, 0.35)]
        spelling_samples = [
            spelling[int(t * 6) % len(spelling)] for t in (0.05, 0.15, 0.25, 0.35)
        ]
        self.assertNotEqual(samples, spelling_samples)

    def test_viseme_at_time_uses_half_open_interval(self):
        intervals = build_phone_intervals("beat", 1.0)
        t_mid = (intervals[0]["t0"] + intervals[0]["t1"]) / 2
        self.assertEqual(viseme_at_time(intervals, t_mid), intervals[0]["viseme"])
        self.assertEqual(viseme_at_time(intervals, intervals[-1]["t1"] + 1), intervals[-1]["viseme"])

    def test_vault_track_includes_fv_then_o(self):
        intervals = build_phone_intervals("vault", 1.0)
        visemes = [p["viseme"] for p in intervals]
        self.assertIn("fv", visemes)
        self.assertIn("o", visemes)
        fv_idx = visemes.index("fv")
        o_idx = visemes.index("o")
        self.assertLess(fv_idx, o_idx)

    def test_consonant_visemes_resolve_on_sheet(self):
        self.assertEqual(sheet_viseme("mbp"), "mbp")
        self.assertEqual(sheet_viseme("fv"), "fv")
        self.assertEqual(sheet_viseme("i"), "i")


if __name__ == "__main__":
    unittest.main()
