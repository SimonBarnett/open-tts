#!/usr/bin/env python3
"""
List all individual speech files in interview_audio2 with exact durations
"""

import subprocess
from pathlib import Path

AUDIO_DIR = Path("interview_audio2")

def get_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path.resolve())
        ],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())


def main():
    leo_files = sorted((AUDIO_DIR / "leo").glob("leo_*.mp3"))
    eve_files = sorted((AUDIO_DIR / "eve").glob("eve_*.mp3"))

    all_files = []

    # Collect by turn number (global numbering)
    for i in range(1, 50):
        leo = AUDIO_DIR / "leo" / f"leo_{i:02d}.mp3"
        eve = AUDIO_DIR / "eve" / f"eve_{i:02d}.mp3"
        if leo.exists():
            all_files.append(("leo", leo))
        if eve.exists():
            all_files.append(("eve", eve))

    if not all_files:
        print("No audio files found in interview_audio2/")
        return

    print(f"{'#':<4} {'Speaker':<8} {'Filename':<18} {'Duration':>10}")
    print("-" * 50)

    total = 0.0
    for idx, (speaker, path) in enumerate(all_files, 1):
        dur = get_duration(path)
        total += dur
        print(f"{idx:<4} {speaker.upper():<8} {path.name:<18} {dur:8.2f}s")

    print("-" * 50)
    print(f"Total speech time (without pauses): {total:.1f}s")
    print(f"Number of turns: {len(all_files)}")


if __name__ == "__main__":
    main()