import tempfile
import unittest
import wave
from pathlib import Path

from open_tts.audio import (
    MAX_SRT_AUDIO_DRIFT_SEC,
    build_full_interview,
    check_caption_drift,
    write_silence_wav,
)


def _tone_wav(path: Path, duration_sec: float) -> None:
    import math

    rate = 24000
    n = int(rate * duration_sec)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            val = int(8000 * math.sin(2 * math.pi * 440 * i / rate))
            frames += int(val).to_bytes(2, "little", signed=True)
        wf.writeframes(frames)


class TestAudioTimeline(unittest.TestCase):
    def test_long_interview_stays_within_drift_budget(self):
        """>60s of speech + pauses: merged WAV matches timeline within 30 ms."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            lines = []
            wavs = []
            for i in range(40):
                sp = "leo" if i % 2 == 0 else "eve"
                lines.append({"speaker": sp, "text": f"Line {i}"})
                w = work / f"{sp}_{i:03d}.wav"
                _tone_wav(w, 1.2)
                wavs.append(w)
            full, segments = build_full_interview(lines, work / "merge", wavs)
            drift = check_caption_drift(segments, lines, full)
            self.assertLessEqual(drift, MAX_SRT_AUDIO_DRIFT_SEC)
            self.assertGreater(check_caption_drift(segments, lines, full), -1)
            dur = full.stat().st_size
            self.assertGreater(dur, 0)


if __name__ == "__main__":
    unittest.main()
