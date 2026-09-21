import unittest

from open_tts.visemes import build_phone_track, g2p_text, phone_to_viseme, viseme_at_time


class TestG2PAndP2V(unittest.TestCase):
    def test_map_contains_mbp(self):
        phones = g2p_text("map")
        self.assertIn("M", phones)
        self.assertIn("P", phones)
        track = build_phone_track("map", 0.6)
        visemes = {seg["viseme"] for seg in track}
        self.assertIn("mbp", visemes)

    def test_vault_fv_then_o(self):
        phones = g2p_text("vault")
        self.assertEqual(phones[0], "V")
        self.assertIn("AO", phones)
        track = build_phone_track("vault", 1.0)
        ordered = [seg["viseme"] for seg in track]
        fv_idx = ordered.index("fv")
        o_idx = next(i for i, v in enumerate(ordered) if v == "o")
        self.assertLess(fv_idx, o_idx)

    def test_beat_maps_to_i(self):
        phones = g2p_text("beat")
        self.assertIn("IY", phones)
        self.assertEqual(phone_to_viseme("IY"), "i")
        track = build_phone_track("beat", 0.5)
        self.assertIn("i", {seg["viseme"] for seg in track})

    def test_viseme_at_time_uses_intervals(self):
        track = build_phone_track("vault", 1.0)
        first = track[0]
        self.assertEqual(viseme_at_time(track, first["t0"]), first["viseme"])
        mid = (first["t0"] + first["t1"]) / 2
        self.assertEqual(viseme_at_time(track, mid), first["viseme"])


if __name__ == "__main__":
    unittest.main()
