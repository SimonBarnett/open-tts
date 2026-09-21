#!/usr/bin/env python3
"""
Generate sentence-level interview audio + SRT + timings
into interview_audio1/
One sentence = one MP3 file.
Second interview – more technical questions about the Product Vault.
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
    # SECOND INTERVIEW – technical deep-dive
    # ============================================================
    dialogue = [
        # Intro – second interview
        ("leo", "Welcome back everyone."),
        ("leo", "Today I'm delighted to be joined once again by Eve from Club Madeira."),
        ("leo", "In our previous conversation we covered the overall Smart Catalogue concept."),
        ("leo", "Today we're going to dig into some of the more technical questions."),
        ("leo", "Eve, thank you so much for joining us again."),
        ("eve", "Thank you Leo, it's a pleasure to be back."),

        # Why product vault
        ("leo", "Why did you choose to build a product vault instead of individual catalogs?"),
        ("eve", "A catalog is a collection of categories belonging to a club."),
        ("eve", "A product may exist in many categories and on many clubs."),
        ("eve", "First, you need to make a list of products and then decide which catalog or club they are relevant to."),

        # How products enter the vault
        ("leo", "How do products enter the product vault?"),
        ("eve", "Through merchant synchronization, we rotate through all the merchants' API keys in the system."),
        ("eve", "Each key gives us access to a merchant's online catalog."),
        ("eve", "The key can be from any of the common product stores like Awin, Wix, WooCommerce, Shopify, etcetera."),
        ("eve", "We download the product details, normalize them into a standard format, and save them to the RDS, our vault."),

        # Organisation
        ("leo", "How are products organized once they're there?"),
        ("eve", "At this point, it's just a big Excel-like sheet of product data."),
        ("eve", "They are organized to be optimal for text searches."),

        # Role of AI
        ("leo", "What role does AI play in managing the product vault?"),
        ("eve", "None at the ingestion stage."),
        ("eve", "We have a list of API keys and functions that know how to pull products from each system."),
        ("eve", "The AI only comes in when we are choosing which products are relevant to a given community, category, or subcategory."),

        # Creating a new catalog
        ("leo", "How does a new catalog get created from the product vault?"),
        ("eve", "Actually, a new catalog is created from the club website the partner identified during the invite."),
        ("eve", "The AI reviews the website, identifies the audience, and works up a marketing report listing all the affiliate opportunities."),
        ("eve", "Then we feed all of that back to the AI as context for choosing the best categories."),
        ("eve", "For each category, it returns positive and negative keywords and the meta descriptions we use for searches."),

        # Putting products into categories
        ("leo", "What happens when we want to put products into those categories?"),
        ("eve", "That's when the vault becomes really useful."),
        ("eve", "We do an initial text search across Amazon, eBay, and our vault to find candidate products, then we give the AI the full context for the category plus the candidate products including images, descriptions, and features."),
        ("eve", "For each product, the AI returns a simple yes or no with a reason."),

        # Smartphone admin
        ("leo", "How does smartphone administration work and why was it important?"),
        ("eve", "The smartphone interface is just the website on a small screen, but this form factor is very important for customers."),
        ("eve", "Club admins, many of whom use their mobile as their primary device, it lowers both the cost and technical barriers for participation."),

        # Merchant changes
        ("leo", "What happens when a participating supplier changes a product, price, or availability?"),
        ("eve", "Merchant synchronization automatically inserts new products, updates existing ones, and removes any that are no longer listed."),
        ("eve", "This runs every seventy-two hours or so."),

        # Scalability
        ("leo", "What makes the architecture scalable for different markets and countries?"),
        ("eve", "The region-agnostic AWS backend means we can spin up separate instances in each Amazon region."),
        ("eve", "The front-end AI assistant is also region-aware and supports multiple languages and accents."),

        # Proudest decision
        ("leo", "Looking back, which architectural decision are you most proud of?"),
        ("eve", "The SQS queues are a work of art."),
        ("eve", "They're capable of downloading eight hundred K products an hour and orchestrating all the searches required to maintain the catalogs with a massively scalable workload."),

        # Investor pitch
        ("leo", "If you had one minute to explain the product vault to an investor, what would you say?"),
        ("eve", "It's a shiny, carefully tuned database."),
        ("eve", "The clever bit is in how we populate the data into it from multiple third-party systems using merchant API keys and how we exploit that data to find relevant products that the club's members will love."),

        # Outro
        ("leo", "Thank you so much, Eve."),
        ("leo", "I'm really excited to see this smart catalog go forward with Club Madeira."),
        ("eve", "Thank you, Leo."),
        ("eve", "It was a pleasure speaking with you."),
    ]

    base = Path("interview_audio1")
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
            next_speaker = dialogue[idx][0]
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