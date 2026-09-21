"""PySide6 studio: issue #9 wizard and issue #13 runtime player."""

from __future__ import annotations

import sys
from pathlib import Path

from open_tts.project import list_projects, projects_root
from open_tts.studio.dirty import (
    block_index_for_line,
    dirty_block_indices_for_line,
)
from open_tts.studio.project import StudioProject, resolve_edit_target


def run_studio(*, edit: Path | None = None) -> int:
    """Explorer entry: list projects or launch the #13 player for --edit."""
    if edit is not None:
        try:
            project = resolve_edit_target(edit)
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if not project.timings_path.is_file():
            print(
                f"No timings.json in {project.output_dir}. Run render first.",
                file=sys.stderr,
            )
            return 1
        from open_tts.studio.app import run_edit_app

        return run_edit_app(project)

    projects = list_projects()
    if not projects:
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


__all__ = [
    "StudioProject",
    "block_index_for_line",
    "dirty_block_indices_for_line",
    "resolve_edit_target",
    "run_studio",
]
