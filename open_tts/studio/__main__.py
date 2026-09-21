"""CLI: python -m open_tts.studio --edit <output-dir-or-yaml>"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from open_tts.studio.app import run_edit_app
from open_tts.studio.project import resolve_edit_target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="open_tts.studio")
    parser.add_argument(
        "--edit",
        metavar="PATH",
        required=True,
        help="Interview output directory or YAML script path",
    )
    args = parser.parse_args(argv)
    try:
        project = resolve_edit_target(Path(args.edit))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not project.timings_path.is_file():
        print(
            f"No timings.json in {project.output_dir}. Run render first.",
            file=sys.stderr,
        )
        return 1
    return run_edit_app(project)


if __name__ == "__main__":
    raise SystemExit(main())
