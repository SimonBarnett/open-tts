#!/usr/bin/env python3
"""
Generate sentence-level interview audio + SRT + timings
into interview4/
One sentence = one MP3 file.
Topic: Marketing the Smart Catalogue & the three markets
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
    # MARKETING DOOR / THREE MARKETS dialogue
    # ============================================================
    dialogue = [
        # Intro
        ("leo", "Today I'm delighted to be joined again by Eve from Club Madeira."),
        ("leo", "Welcome back Eve!"),
        ("eve", "Happy to be here."),

        # Marketing door concept
        ("leo", "So today I wanted to ask about how you market the Smart Catalogue."),
        ("leo", "What's your marketing door?"),
        ("eve", "Marketing door?"),
        ("eve", "I'm not sure I follow."),
        ("leo", "Yes, when I worked in marketing we had a marketing door."),
        ("leo", "We knew who our customers were because they walked through the marketing door."),
        ("eve", "That's not how marketing usually works."),
        ("eve", "Did your marketing door say 'fish and chips' over it?"),
        ("leo", "No."),
        ("eve", "Car dealership?"),
        ("leo", "Okay."),
        ("leo", "So how do you do marketing at Club Madeira?"),

        # Real definition of marketing
        ("eve", "Marketing is about identifying people who will buy your product."),
        ("eve", "What do you do if the person who walks through your marketing door has no use-case for your product?"),
        ("leo", "Well, I have to sell them something because they came through my marketing door."),
        ("leo", "I can just make up a new product that they might buy."),
        ("eve", "Marketing is about identifying people who will buy your product."),
        ("eve", "If you have to make up a new product to sell to the person who walked through your marketing door, they are -by definition- not in your market."),

        # Who is the market
        ("leo", "So who is the market for the Smart Catalogue, and how do you identify them without a marketing door?"),
        ("eve", "Club Madeira operates in three distinct markets."),
        ("eve", "Clubs, partners and merchants."),

        # Clubs market
        ("eve", "Firstly, clubs."),
        ("leo", "Sorry, why clubs specifically?"),
        ("leo", "Can I not just put a Smart Catalogue on any website?"),
        ("eve", "We are an affiliate marketing company that earns on commission."),
        ("eve", "Affiliate commissions require high traffic as conversion rates are typically around one percent."),
        ("eve", "Each Smart Catalogue costs around twenty dollars per month to maintain."),
        ("eve", "So to have any hope of commercial viability a Smart Catalogue must be on a site with the potential for around twenty sales per month."),
        ("eve", "At one percent conversion that's two thousand clicks."),
        ("eve", "Handing out Smart Catalogues to sites without any audience is a loss-making exercise."),
        ("eve", "Our market is specifically clubs and community groups that have an unmonetised audience and members that will buy because they know their club gets the commission."),
        ("eve", "A member has a reason to purchase through the Smart Catalogue rather than Amazon."),
        ("eve", "A customer does not."),

        # The no-traffic customer
        ("leo", "But my customer is never going to have two thousand clicks per month."),
        ("leo", "They don't even have a website yet."),
        ("eve", "Are they a club?"),
        ("eve", "How many members?"),
        ("leo", "No."),
        ("leo", "But they walked through the marketing door."),
        ("eve", "Okay, but without an audience to monetise or any chance of generating that audience, they aren't a Smart Catalogue customer."),

        # Partners market
        ("leo", "You mentioned you had a market for partners."),
        ("leo", "Can I be a partner so I can give away Smart Catalogues to people who don't have any traffic?"),
        ("eve", "No, because every time you deliberately created an unsuccessful catalogue it would damage Club Madeira's reputation."),
        ("eve", "We'd need to charge you twenty dollars per website per month to break even."),
        ("eve", "You'd need to charge twenty times the going rate of one pound just to cover costs."),
        ("eve", "And the moment you set off building websites in competition with our actual partners, they would refuse to deal with us."),

        ("leo", "But I can make websites."),
        ("leo", "Why can't I be a partner?"),
        ("eve", "We are an affiliate marketing company that earns on commission."),
        ("eve", "Affiliate commissions require high traffic as conversion rates are typically one percent."),
        ("eve", "Partners are people that manage websites with an audience."),
        ("eve", "They engage that audience with marketing, SEO and promotion and deliver ongoing technical support."),
        ("eve", "Do you manage any websites with an unmonetised audience?"),
        ("leo", "No, but..."),
        ("eve", "Can you provide marketing, SEO and promotion and deliver ongoing technical support?"),
        ("leo", "No, but I can make websites."),
        ("eve", "Anyone with one pound per month and an Ionos account can do that."),
        ("eve", "The web agencies who will survive are those that drive engagement."),
        ("eve", "And right now they are looking for ways to differentiate their offering, " ),
        ("eve", "for client retention, for billables and for recurring revenue."),
        ("eve", "For a company in the actual partner market, the Smart Catalogue offers all of that."),

        # Closing the loop
        ("leo", "Okay, so I'm not in the target market to be a partner."),
        ("leo", "But what about the guy who walked through my marketing door?"),
        ("leo", "He's giving me buying signals!"),
        ("eve", "Take him to someone who can offer proper partner services."),
        ("eve", "Tell him to ask for a Smart Catalogue and ask them to contact us."),        
        ("eve", "You have just gained a partner who will now look to see where else they can place the Smart Catalogue."),
        ("eve", "And with the partner's marketing, SEO and promotion that catalogue might eventually break even."),

        # The final challenge
        ("leo", "What if I ignore all that and set up as a partner behind your back anyway?"),
        ("eve", "We'd have to wish you all the best in your future endeavours."),
        ("eve", "Do you want to hear about the market for merchants?"),
        ("leo", "No, ten thousand products is unrealistic."),
    ]

    base = Path("interview4")
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