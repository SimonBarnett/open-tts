#!/usr/bin/env python3
"""
Generate sentence-level interview audio + SRT + timings
into interview3/
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
        ("leo", "Welcome back everyone."),
        ("leo", "Today I'm joined once again by Eve from Club Madeira."),
        ("leo", "Eve, thank you for being here."),
        ("eve", "Always a pleasure, Leo."),

        # Hypothetical partner question
        ("leo", "So, if I wanted to become a partner — say I'm a website designer or digital agency working with clubs — walk me through what that would look like, especially the white-label side."),

        # White-label core
        ("eve", "That's the part partners love most."),
        ("eve", "The Smart Catalogue is built from the ground up as a fully white-label product."),
        ("eve", "Clubs never see Club Madeira branding."),
        ("eve", "When you embed it, the entire experience appears under your client's brand, on their domain, with their colours, logo and voice."),
        ("eve", "From the member's point of view it simply feels like the club's own professional online shop."),
        ("eve", "That's a huge selling point for agencies."),

        ("leo", "So I control the look and feel completely?"),
        ("eve", "Completely."),
        ("eve", "You control the branding, the pricing you charge the club, the level of support you offer, and the ongoing client relationship."),
        ("eve", "We stay in the background."),
        ("eve", "You deliver a white-labelled Progressive Web App experience that members can even install on their phones — still fully branded as the club."),

        # MIT open source
        ("leo", "Can I modify the code myself if I need to?"),
        ("eve", "Yes."),
        ("eve", "The complete partner integration code is available under the MIT open-source licence."),
        ("eve", "You're free to use it, modify it, and extend it however you need."),
        ("eve", "That means you can adapt the widgets, adjust the PWA behaviour, or build additional features on top without asking permission or paying extra."),
        ("eve", "It's designed so agencies can properly own the technical delivery for their clients."),

        ("leo", "That makes it feel like a premium service I'm providing, not a locked-down third-party tool."),
        ("eve", "Exactly."),
        ("eve", "You're not reselling someone else's platform."),
        ("eve", "You're embedding a powerful fundraising engine that becomes part of the club's own digital presence."),
        ("eve", "And because it's white-label and open source under MIT, you can position and customise it however you like."),

        # Commercial side
        ("leo", "How does the commercial side work in that model?"),
        ("eve", "When members shop, the club earns commission, you earn recurring revenue, and merchants get targeted exposure."),
        ("eve", "There are no monthly platform fees."),
        ("eve", "Your technical work is the clean integration, branding, and any modifications you choose to make."),
        ("eve", "The ongoing commercial opportunity is driving engagement."),
        ("eve", "We expect each active catalogue to generate around two thousand clicks a month."),
        ("eve", "That comes from the marketing, SEO and promotion that you bill the club for as a paid service."),

        ("leo", "So the white-label nature plus the MIT licence lets me own the whole relationship and charge properly for the value."),
        ("eve", "That's the model."),
        ("eve", "You bring the clubs, the websites and the promotional expertise."),
        ("eve", "We provide the AI, the product vault and the infrastructure — all invisible to the end user."),
        ("eve", "It turns a simple website add-on into a high-value, recurring service under your brand."),

        # Next steps + outro
        ("leo", "That's very clear."),
        ("leo", "What's the practical first step if I wanted to start?"),
        ("eve", "You become an approved partner, receive your affiliate code and the full partner package — including the MIT-licensed integration code — then begin embedding the white-label catalogue for your existing club clients."),
        ("eve", "From day one it looks and feels like something you built for them."),

        ("leo", "Thank you, Eve."),
        ("leo", "That's extremely helpful."),
        ("eve", "Thank you, Leo."),
        ("eve", "Happy to go deeper any time."),
    ]

    base = Path("interview3")          # ← changed to interview3
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

        # Add pause after this sentence (this is what creates the gaps in the SRT)
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
    # Write SRT  (includes the gaps because current_time already has them)
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