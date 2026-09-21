"""CLI: python -m open_tts.studio (wizard) or --edit <path> (#13 player)."""

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
        help="Interview output directory or YAML script path (#13 player)",
    )
    args = parser.parse_args(argv)
    if args.edit:
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

    from PySide6.QtWidgets import QApplication

    from open_tts.studio.main_window import MainWindow

    app = QApplication(argv or sys.argv)
    app.setApplicationName("Open TTS Studio")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
