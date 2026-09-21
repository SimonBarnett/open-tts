"""CLI project lister (``python -m open_tts studio``); Qt wizard is ``python -m open_tts.studio``."""

from __future__ import annotations

import sys
from pathlib import Path

from open_tts.project import list_projects, resolve_project_path


def run_studio(*, edit: Path | None = None) -> int:
    if edit is not None:
        try:
            project_path = resolve_project_path(edit)
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(
            f"Studio edit (#13): project folder {project_path}\n"
            "Qt runtime player is not in this branch; use render CLI or merge #13."
        )
        return 0

    projects = list_projects()
    if not projects:
        from open_tts.project import projects_root

        print(f"No projects under {projects_root()}")
        return 0
    print("Projects:")
    for row in projects:
        video = "mp4" if row.get("has_video") else "no"
        print(
            f"  {row['slug']:30}  {row.get('title', '')[:40]:40}  "
            f"{row.get('host', '?')}/{row.get('guest', '?')}  video:{video}"
        )
    print("\nOpen a project: python -m open_tts studio --edit projects/<slug>")
    return 0
