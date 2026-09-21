#!/usr/bin/env python3
"""
Build the final interview video using timings.json + interview.srt
from the clean sentence-level audio in interview_audio2/

CRITICAL FIX: visual segments now include the pauses that belong
to each speaker block so the video length matches the audio exactly.
"""

import json
import subprocess
import shutil
from pathlib import Path
from itertools import groupby

# ============================================================
# CONFIG
# ============================================================
AUDIO_DIR      = Path("interview_audio2")
TIMINGS_JSON   = AUDIO_DIR / "timings.json"
FULL_AUDIO     = AUDIO_DIR / "full_interview.mp3"
SRT            = AUDIO_DIR / "interview.srt"

OUTPUT_DIR     = Path("interview2")
OUTPUT         = OUTPUT_DIR / "interview_ai_vs_ai_final.mp4"

FULL_LEO       = Path("full_leo_talking.mp4")
FULL_EVE       = Path("full_eve_talking.mp4")
DUAL_LEO_TALK  = Path("dual_leo_talking_eve_idle.mp4")
DUAL_EVE_TALK  = Path("dual_eve_talking_leo_idle.mp4")

# Dual screen for the first N and last N sentences
DUAL_START = 4
DUAL_END   = 5


def run(cmd):
    print("→", " ".join(str(c) for c in cmd)[:150])
    subprocess.run(cmd, check=True)


def get_audio_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1",
         str(path.resolve())],
        capture_output=True, text=True, check=True
    )
    return float(r.stdout.strip())


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    for f in [TIMINGS_JSON, FULL_AUDIO, FULL_LEO, FULL_EVE, DUAL_LEO_TALK, DUAL_EVE_TALK]:
        if not f.exists():
            raise FileNotFoundError(f"Missing required file: {f}")

    # --------------------------------------------------------
    # 1. Load timings
    # --------------------------------------------------------
    with open(TIMINGS_JSON, encoding="utf-8") as f:
        segments = json.load(f)

    total_audio_duration = get_audio_duration(FULL_AUDIO)
    print(f"Loaded {len(segments)} sentences")
    print(f"Full audio duration: {total_audio_duration:.3f}s\n")

    # --------------------------------------------------------
    # 2. Build merged speaker blocks
    #    Duration now correctly includes the trailing pause
    # --------------------------------------------------------
    merged = []
    groups = []
    for speaker, group in groupby(segments, key=lambda x: x["speaker"]):
        groups.append((speaker, list(group)))

    for i, (speaker, group) in enumerate(groups):
        start = group[0]["start"]

        # End of this block = start of the next block
        # (this automatically includes the pause after the last sentence)
        if i + 1 < len(groups):
            end = groups[i + 1][1][0]["start"]
        else:
            # Last block → go all the way to the end of the audio
            end = total_audio_duration

        duration = end - start

        first_id = group[0]["id"]
        is_dual = (first_id <= DUAL_START) or (first_id > len(segments) - DUAL_END)
        mode = "split" if is_dual else "full"

        merged.append({
            "speaker": speaker,
            "start": start,
            "end": end,
            "duration": duration,
            "mode": mode,
            "ids": [g["id"] for g in group],
        })

    print("Merged visual segments (pauses now included):")
    print("-" * 75)
    for i, seg in enumerate(merged, 1):
        print(f"{i:02d}. {seg['speaker'].upper():3}  "
              f"{seg['start']:7.2f} → {seg['end']:7.2f}  "
              f"({seg['duration']:6.2f}s)  [{seg['mode']}]  "
              f"ids {seg['ids']}")
    print("-" * 75)

    calculated_total = merged[-1]["end"] if merged else 0
    print(f"Calculated visual length: {calculated_total:.3f}s")
    print(f"Audio length            : {total_audio_duration:.3f}s\n")

    # --------------------------------------------------------
    # 3. Create visual clips
    # --------------------------------------------------------
    temp = Path("temp_segments2")
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir()

    print("Creating visual segments...")
    clips = []
    for i, seg in enumerate(merged):
        if seg["mode"] == "split":
            src = DUAL_LEO_TALK if seg["speaker"] == "leo" else DUAL_EVE_TALK
        else:
            src = FULL_LEO if seg["speaker"] == "leo" else FULL_EVE

        out = temp / f"seg_{i:02d}_{seg['mode']}_{seg['speaker']}.mp4"

        run([
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(src.resolve()),
            "-t", f"{seg['duration']:.3f}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-an",
            str(out)
        ])
        clips.append(out)

    # --------------------------------------------------------
    # 4. Concatenate
    # --------------------------------------------------------
    list_file = temp / "list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    visual = temp / "visual.mp4"
    run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(visual)
    ])

    # --------------------------------------------------------
    # 5. Final mux (exact length, no -shortest)
    # --------------------------------------------------------
    print("\nMuxing final video...")
    local_srt = Path("temp_sub.srt")
    shutil.copy2(SRT, local_srt)

    # Important: we do NOT use -shortest any more
    # We force the video to the exact audio length
    vf = (
        "subtitles=temp_sub.srt:"
        "force_style='FontSize=16,PrimaryColour=&HFFFFFF&,"
        "OutlineColour=&H000000&,BorderStyle=3'"
    )

    run([
        "ffmpeg", "-y",
        "-i", str(visual),
        "-i", str(FULL_AUDIO.resolve()),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", f"{total_audio_duration:.3f}",   # force exact duration
        str(OUTPUT)
    ])

    local_srt.unlink(missing_ok=True)

    print(f"\n{'='*60}")
    print(f"✅ DONE → {OUTPUT.resolve()}")
    print(f"   Video length forced to {total_audio_duration:.3f}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()