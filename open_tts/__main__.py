"""CLI: python -m open_tts render <script.yaml>"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from open_tts.audio import MAX_SRT_AUDIO_DRIFT_SEC, check_caption_drift
from open_tts.render import render_interview
import json


def cmd_render(args: argparse.Namespace) -> int:
    yaml_path = Path(args.script)
    if not yaml_path.is_file():
        print(f"Script not found: {yaml_path}", file=sys.stderr)
        return 1
    out = render_interview(
        yaml_path,
        output_dir=Path(args.output) if args.output else None,
        skip_tts=args.skip_tts,
        video=not args.no_video,
        check_only=False,
    )
    print(f"Rendered interview → {out.resolve()}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    timings = Path(args.timings)
    audio = Path(args.audio)
    if not timings.is_file() or not audio.is_file():
        print("Missing timings or audio path", file=sys.stderr)
        return 1
    segments = json.loads(timings.read_text(encoding="utf-8"))
    lines = [{"speaker": s["speaker"]} for s in segments]
    drift = check_caption_drift(segments, lines, audio)
    ok = drift <= MAX_SRT_AUDIO_DRIFT_SEC
    print(f"Drift: {drift * 1000:.2f} ms (budget {MAX_SRT_AUDIO_DRIFT_SEC * 1000:.0f} ms)")
    return 0 if ok else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="open_tts")
    sub = parser.add_subparsers(dest="command", required=True)

    p_render = sub.add_parser("render", help="Render interview from YAML script")
    p_render.add_argument("script", help="Path to interview YAML")
    p_render.add_argument("-o", "--output", help="Output directory")
    p_render.add_argument(
        "--skip-tts",
        action="store_true",
        help="Do not call TTS; require existing sentence MP3s",
    )
    p_render.add_argument(
        "--no-video",
        action="store_true",
        help="Audio + captions only",
    )
    p_render.set_defaults(func=cmd_render)

    p_check = sub.add_parser("check", help="Verify caption drift vs audio")
    p_check.add_argument("timings", help="timings.json path")
    p_check.add_argument("audio", help="full_interview.wav or .mp3 path")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
