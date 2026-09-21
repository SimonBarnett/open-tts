#!/usr/bin/env python3
"""
Generate sentence-level interview audio + SRT + timings
into interview_audio2/
One sentence = one MP3 file.
Skips any sentence that already exists.
"""

import os
import requests
import base64
import json
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

GROK_API_KEY = os.environ.get("XAI_API_KEY")
if not GROK_API_KEY:
    raise SystemExit("Set the XAI_API_KEY environment variable")

PAUSE_BETWEEN_SPEAKERS = 950   # ms
PAUSE_BETWEEN_SENTENCES = 350  # ms (same speaker)


def generate_grok_audio(text: str, voice_id: str) -> str | None:
    print(f"🔊 {voice_id.upper():3} : {text[:80]}{'...' if len(text) > 80 else ''}")
    url = "https://api.x.ai/v1/tts"
    payload = {"text": text, "voice_id": voice_id, "language": "en"}
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=90)
        r.raise_for_status()
        print("   ✓ done")
        return base64.b64encode(r.content).decode("utf-8")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return None


def save_audio(b64: str, path: Path):
    path.write_bytes(base64.b64decode(b64))


def get_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1",
         str(path.resolve())],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())


def create_silence(ms: int, path: Path):
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anullsrc=r=24000:cl=mono",
        "-t", str(ms / 1000),
        "-acodec", "libmp3lame", str(path)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def format_srt_time(seconds: float) -> str:
    td = timedelta(seconds=seconds)
    total = int(td.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    ms = int(round((seconds - total) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    # ============================================================
    # ALREADY SPLIT INTO SINGLE SENTENCES
    # ============================================================
    dialogue = [
        # Intro
        ("leo", "Welcome everyone."),
        ("leo", "Today I'm joined by Eve from Club Madeira to talk about their Smart Catalogue."),
        ("leo", "Eve, thank you for joining us."),
        ("eve", "Thank you Leo, it's great to be here."),

        # What is the Smart Catalogue
        ("leo", "Let's start with the basics."),
        ("leo", "What exactly is the Smart Catalogue?"),
        ("eve", "The Smart Catalogue by Club Madeira is a B2B, invite-only, white-label AI-powered fundraising engine."),
        ("eve", "It's designed specifically for professional partners — website designers, digital agencies, consultants, and service providers — who work with clubs and community groups."),
        ("eve", "These partners can embed a fully white-labelled Smart Catalogue into their clients’ websites."),
        ("eve", "The AI automatically creates and manages a smart online shop with products that members are likely to love."),
        ("eve", "When members shop, the club earns commission, the partner gets recurring revenue, and merchants get targeted exposure — all with almost no extra work."),

        ("leo", "Who is this platform actually for?"),
        ("eve", "It's exclusively for approved professional partners."),
        ("eve", "Clubs don't buy it directly."),
        ("eve", "Partners control the client relationship, branding, pricing, and support."),
        ("eve", "There are no monthly platform fees, no stock to manage, and everything can be handled from a dashboard or even a smartphone app."),

        # AI Curation
        ("leo", "How does the AI actually choose which products to show?"),
        ("eve", "The AI uses a practical, interest-based curation system."),
        ("eve", "Club admins pick their group's main interests and categories through the smartphone app — things like model flying, scouting, sports, crafts, parenting, etc."),
        ("eve", "The AI then pulls products from trusted merchant feeds and APIs, matches them to those interests, and scores them for relevance."),
        ("eve", "The catalogue is living — it updates daily, adding new products and removing ones that are no longer relevant."),

        # The Vault
        ("leo", "During some conversations, your team mentioned keeping products in a 'Vault'."),
        ("leo", "What is that exactly?"),
        ("eve", "The Vault is our internal name for the central product database."),
        ("eve", "We don't hold any physical stock — this is a pure affiliate model."),
        ("eve", "Merchants connect their stores via APIs, and we pull product data into our system."),
        ("eve", "It's essentially a large, well-organized database of normalised product information that our AI can search and curate from efficiently."),

        ("leo", "Your salesman described this Vault as very rare and special."),
        ("leo", "Is a database really that unusual?"),
        ("eve", "Databases themselves are very common — almost every modern website uses one."),
        ("eve", "What makes our system special is not the database, but how we combine it with powerful AI to automatically build and maintain highly relevant catalogues for thousands of different communities with almost no manual effort."),
        ("eve", "That level of smart automation, especially in the club and community fundraising space, is quite rare."),

        # Sales hype
        ("leo", "So would you say the salesman was overselling it a bit?"),
        ("eve", "There's always a bit of sales enthusiasm!"),
        ("eve", "The core technology — a database plus AI curation — isn't unique in the broader e-commerce world."),
        ("eve", "But the specific combination we’ve built: white-label for agencies, smartphone-first admin, fully automated curation, zero stock, and strong focus on community fundraising, is genuinely valuable and unusual in this niche."),
        ("eve", "We prefer to focus on the real benefits rather than hype."),

        # Outro
        ("leo", "Thank you Eve."),
        ("leo", "This has been very insightful."),
        ("leo", "I'm excited to see how the Smart Catalogue develops."),
        ("eve", "Thank you Leo."),
        ("eve", "It was a pleasure."),
    ]

    base = Path("interview_audio2")
    leo_dir = base / "leo"
    eve_dir = base / "eve"
    leo_dir.mkdir(parents=True, exist_ok=True)
    eve_dir.mkdir(parents=True, exist_ok=True)

    print(f"🎙️ Generating {len(dialogue)} individual sentences into {base}\n")

    all_segments = []
    current_time = 0.0

    for idx, (speaker, text) in enumerate(dialogue, 1):
        out_dir = leo_dir if speaker == "leo" else eve_dir
        mp3_path = out_dir / f"{speaker}_{idx:03d}.mp3"
        json_path = out_dir / f"{speaker}_{idx:03d}.json"

        if mp3_path.exists():
            print(f"   ⏭  Skipping {mp3_path.name}")
            duration = get_duration(mp3_path)
        else:
            b64 = generate_grok_audio(text, speaker)
            if not b64:
                print(f"   ❌ Skipping {idx} due to generation failure")
                continue
            save_audio(b64, mp3_path)
            duration = get_duration(mp3_path)
            json_path.write_text(json.dumps({
                "id": idx,
                "speaker": speaker,
                "text": text,
                "duration": round(duration, 3),
                "generated_at": datetime.now().isoformat()
            }, indent=2), encoding="utf-8")
            print(f"   Saved {mp3_path.name} ({duration:.2f}s)")

        start = current_time
        end = current_time + duration

        all_segments.append({
            "id": idx,
            "speaker": speaker,
            "text": text,
            "file": mp3_path.name,
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(duration, 3)
        })

        current_time = end

        # Add pause after this sentence
        if idx < len(dialogue):
            next_speaker = dialogue[idx][0]  # next item (0-based)
            if next_speaker == speaker:
                current_time += PAUSE_BETWEEN_SENTENCES / 1000.0
            else:
                current_time += PAUSE_BETWEEN_SPEAKERS / 1000.0

    # --------------------------------------------------------
    # Write timings.json
    # --------------------------------------------------------
    timings_path = base / "timings.json"
    timings_path.write_text(json.dumps(all_segments, indent=2), encoding="utf-8")
    print(f"\n📄 timings.json → {timings_path}")

    # --------------------------------------------------------
    # Write SRT
    # --------------------------------------------------------
    srt_path = base / "interview.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(all_segments, 1):
            f.write(f"{i}\n")
            f.write(f"{format_srt_time(seg['start'])} --> {format_srt_time(seg['end'])}\n")
            f.write(f"{seg['text']}\n\n")
    print(f"📄 interview.srt → {srt_path}")

    # --------------------------------------------------------
    # Build full_interview.mp3 with correct pauses
    # --------------------------------------------------------
    print("\nMerging full audio...")
    silence_short = base / "silence_short.mp3"
    silence_long = base / "silence_long.mp3"
    create_silence(PAUSE_BETWEEN_SENTENCES, silence_short)
    create_silence(PAUSE_BETWEEN_SPEAKERS, silence_long)

    list_file = base / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for i, seg in enumerate(all_segments):
            audio_path = (base / seg["speaker"] / seg["file"]).resolve()
            f.write(f"file '{audio_path}'\n")
            if i < len(all_segments) - 1:
                next_speaker = all_segments[i + 1]["speaker"]
                if next_speaker == seg["speaker"]:
                    f.write(f"file '{silence_short.resolve()}'\n")
                else:
                    f.write(f"file '{silence_long.resolve()}'\n")

    full_audio = base / "full_interview.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(full_audio)
    ], check=True, capture_output=True)

    # cleanup
    list_file.unlink(missing_ok=True)
    silence_short.unlink(missing_ok=True)
    silence_long.unlink(missing_ok=True)

    print(f"✅ full_interview.mp3 → {full_audio}")
    print(f"\nTotal sentences : {len(all_segments)}")
    print(f"Total duration  : {current_time:.1f}s")
    print(f"\nAll files are in → {base.resolve()}")


if __name__ == "__main__":
    main()