"""CLI: python -m open_tts render <script.yaml>"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from open_tts.audio import MAX_SRT_AUDIO_DRIFT_SEC, check_caption_drift
from open_tts.project import create_project, import_interview_yaml, list_projects
from open_tts.render import render_interview
from open_tts.project_explorer import run_studio


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


def cmd_project_new(args: argparse.Namespace) -> int:
    try:
        root = create_project(
            args.slug,
            host=args.host,
            guest=args.guest,
            title=args.title,
        )
    except (ValueError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(root.resolve())
    return 0


def cmd_project_list(_args: argparse.Namespace) -> int:
    rows = list_projects()
    if not rows:
        print("(no projects)")
        return 0
    for row in rows:
        video = "yes" if row.get("has_video") else "no"
        print(
            f"{row['slug']}\t{row.get('title', '')}\t"
            f"{row.get('host', '?')}/{row.get('guest', '?')}\tvideo={video}"
        )
    return 0


def cmd_project_import(args: argparse.Namespace) -> int:
    try:
        root = import_interview_yaml(Path(args.yaml), slug=args.slug)
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(root.resolve())
    return 0


def cmd_studio(args: argparse.Namespace) -> int:
    edit = Path(args.edit) if args.edit else None
    return run_studio(edit=edit)


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

    p_project = sub.add_parser("project", help="Interview project folders")
    project_sub = p_project.add_subparsers(dest="project_command", required=True)

    p_new = project_sub.add_parser("new", help="Create projects/<slug>/")
    p_new.add_argument("slug", help="Project slug (e.g. vault-technical)")
    p_new.add_argument("--host", default="leo", help="Host character id")
    p_new.add_argument("--guest", default="eve", help="Guest character id")
    p_new.add_argument("--title", help="Interview title")
    p_new.set_defaults(func=cmd_project_new)

    p_list = project_sub.add_parser("list", help="List projects (headless)")
    p_list.set_defaults(func=cmd_project_list)

    p_import = project_sub.add_parser(
        "import",
        help="Copy interviews/*.yaml into projects/<slug>/",
    )
    p_import.add_argument("yaml", help="Source interview YAML path")
    p_import.add_argument(
        "--slug",
        help="Destination slug (default: source file stem)",
    )
    p_import.set_defaults(func=cmd_project_import)

    p_studio = sub.add_parser("studio", help="Project explorer / edit entry")
    p_studio.add_argument(
        "--edit",
        metavar="PATH",
        help="Project folder or interview.yaml (#13 player when available)",
    )
    p_studio.set_defaults(func=cmd_studio)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
