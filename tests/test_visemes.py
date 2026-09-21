import unittest

from open_tts.visemes import (
    attach_phones_to_segments,
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

    def test_consonant_visemes_map_to_consonant_cells_not_pause(self):
        self.assertEqual(sheet_viseme("mbp"), "mbp")
        self.assertEqual(sheet_viseme("fv"), "fv")
        self.assertNotEqual(sheet_viseme("mbp"), sheet_viseme("pause"))
        self.assertEqual(sheet_viseme("i"), "i")

    def test_vault_fv_then_o_in_time(self):
        intervals = build_phone_intervals("vault", 1.0)
        ordered = [p["viseme"] for p in intervals]
        fv_idx = ordered.index("fv")
        o_idx = next(i for i, v in enumerate(ordered) if v == "o")
        self.assertLess(fv_idx, o_idx)
        self.assertEqual(viseme_at_time(intervals, 0.05), "fv")

    def test_attach_phones_persists_track_for_skip_tts_reuse(self):
        seg = {"text": "map", "duration": 0.5}
        attach_phones_to_segments([seg])
        self.assertIn("phones", seg)
        mbp = [p for p in seg["phones"] if p["viseme"] == "mbp"]
        self.assertTrue(mbp)
        self.assertEqual(sheet_viseme(mbp[0]["viseme"]), "mbp")


if __name__ == "__main__":
    unittest.main()
