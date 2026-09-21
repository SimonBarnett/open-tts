#!/usr/bin/env python3
"""
Final correct stitcher – uses the exact ordered list of turns
that were used to generate full_interview_v2.mp3
"""

import subprocess
import shutil
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================
AUDIO_DIR      = Path("interview_audio")
FULL_AUDIO     = AUDIO_DIR / "full_interview_v2.mp3"
OUTPUT         = Path("interview_ai_vs_ai_final.mp4")

FULL_LEO       = Path("full_leo_talking.mp4")
FULL_EVE       = Path("full_eve_talking.mp4")
DUAL_LEO_TALK  = Path("dual_leo_talking_eve_idle.mp4")
DUAL_EVE_TALK  = Path("dual_eve_talking_leo_idle.mp4")

SRT            = Path("interview.srt")
PAUSE_MS       = 950

# ============================================================
# EXACT ORDER OF TURNS used to create the current full audio
# (this is the only reliable way)
# ============================================================
TURNS = [
    ("leo", "leo_01.mp3"),   # Welcome everyone...
    ("eve", "eve_01.mp3"),   # Thank you Leo...
    ("leo", "leo_02.mp3"),   # Let's start with the basics...
    ("eve", "eve_02.mp3"),   # The Smart Catalogue by Club Madeira is...
    ("eve", "eve_03.mp3"),   # These partners can embed...
    ("leo", "leo_03.mp3"),   # Who is this platform actually for?
    ("eve", "eve_04.mp3"),   # It's exclusively for approved...
    ("leo", "leo_04.mp3"),   # How does the AI actually choose...
    ("eve", "eve_05.mp3"),   # The AI uses a practical...
    ("eve", "eve_06.mp3"),   # The AI then pulls products...
    ("leo", "leo_05.mp3"),   # During some conversations... Vault
    ("eve", "eve_07.mp3"),   # The Vault is our internal name...
    ("eve", "eve_08.mp3"),   # It's essentially a large...
    ("leo", "leo_06.mp3"),   # Your salesman described this Vault...
    ("eve", "eve_09.mp3"),   # Databases themselves are very common...
    ("eve", "eve_10.mp3"),   # That level of smart automation...
    ("leo", "leo_07.mp3"),   # So would you say the salesman...
    ("eve", "eve_11.mp3"),   # There's always a bit of sales enthusiasm...
    ("eve", "eve_12.mp3"),   # We prefer to focus on the real benefits...
    ("leo", "leo_08.mp3"),   # Thank you Eve. This has been very insightful.
    ("eve", "eve_13.mp3"),   # Thank you Leo. It was a pleasure.
]

# Dual screen for first 2 and last 2 turns
DUAL_START = 2
DUAL_END   = 2


def run(cmd):
    print("→", " ".join(str(c) for c in cmd)[:150])
    subprocess.run(cmd, check=True)


def get_duration(path: Path) -> float:
    path = path.resolve()
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())


def main():
    for f in [FULL_AUDIO, FULL_LEO, FULL_EVE, DUAL_LEO_TALK, DUAL_EVE_TALK]:
        if not f.exists():
            raise FileNotFoundError(f"Missing: {f}")

    # --------------------------------------------------------
    # Build exact timeline from the known ordered list
    # --------------------------------------------------------
    segments = []
    current = 0.0

    print("Building exact timeline from known turn order...\n")
    for idx, (speaker, filename) in enumerate(TURNS):
        mp3 = AUDIO_DIR / speaker / filename
        if not mp3.exists():
            raise FileNotFoundError(f"Missing turn file: {mp3}")

        duration = get_duration(mp3)
        start = current
        end = start + duration

        is_dual = (idx < DUAL_START) or (idx >= len(TURNS) - DUAL_END)
        mode = "split" if is_dual else "full"

        segments.append({
            "start": start,
            "end": end,
            "mode": mode,
            "speaker": speaker,
            "file": filename
        })

        print(f"{idx+1:02d}. {speaker.upper():3}  {start:7.2f} → {end:7.2f}  "
              f"({duration:5.2f}s)  [{mode}]  {filename}")

        current = end + (PAUSE_MS / 1000.0)

    print(f"\nTotal calculated length: {current:.1f}s")

    # --------------------------------------------------------
    # Create visual segments
    # --------------------------------------------------------
    temp = Path("temp_segments")
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir()

    clip_paths = []
    print("\nCreating visual segments...")

    for i, seg in enumerate(segments):
        duration = seg["end"] - seg["start"]
        if seg["mode"] == "split":
            src = DUAL_LEO_TALK if seg["speaker"] == "leo" else DUAL_EVE_TALK
        else:
            src = FULL_LEO if seg["speaker"] == "leo" else FULL_EVE

        out = temp / f"seg_{i:02d}_{seg['mode']}_{seg['speaker']}.mp4"

        run([
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(src.resolve()),
            "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-an",
            str(out)
        ])
        clip_paths.append(out)

    # Concat
    list_file = temp / "list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{p.resolve().as_posix()}'\n")

    visual = temp / "visual.mp4"
    run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(visual)
    ])

    # Final mux (UNC-safe)
    print("\nMuxing final video...")
    local_srt = Path("temp_sub.srt")
    if SRT.exists():
        shutil.copy2(SRT, local_srt)

    if local_srt.exists():
        vf = "subtitles=temp_sub.srt:force_style='FontSize=16,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=3'"
        run([
            "ffmpeg", "-y",
            "-i", str(visual),
            "-i", str(FULL_AUDIO.resolve()),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(OUTPUT)
        ])
        local_srt.unlink(missing_ok=True)
    else:
        run([
            "ffmpeg", "-y",
            "-i", str(visual),
            "-i", str(FULL_AUDIO.resolve()),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(OUTPUT)
        ])

    print(f"\n{'='*60}")
    print(f"✅ DONE → {OUTPUT.resolve()}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()