"""Interview project folders under projects/<slug>/."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from open_tts.script import load_interview, normalized_lines

INTERVIEW_YAML = "interview.yaml"
PROJECT_JSON = "project.json"
WORK_DIR = "_work"

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def projects_root() -> Path:
    override = __import__("os").environ.get("OPEN_TTS_PROJECTS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return repo_root() / "projects"


def validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise ValueError(
            f"Invalid project slug {slug!r}; use lowercase letters, digits, and hyphens."
        )


def project_dir(slug: str) -> Path:
    validate_slug(slug)
    return projects_root() / slug


def is_project_directory(path: Path) -> bool:
    path = path.resolve()
    return (path / INTERVIEW_YAML).is_file()


def interview_yaml_in_project(yaml_path: Path) -> bool:
    yaml_path = yaml_path.resolve()
    if yaml_path.name != INTERVIEW_YAML:
        return False
    parent = yaml_path.parent
    if (parent / PROJECT_JSON).is_file():
        return True
    try:
        parent.relative_to(projects_root().resolve())
        return True
    except ValueError:
        return False


def default_output_dir(yaml_path: Path) -> Path:
    """Project root for projects/*/interview.yaml; legacy interviews/output/<stem> otherwise."""
    if interview_yaml_in_project(yaml_path):
        return yaml_path.resolve().parent
    return yaml_path.parent / "output" / yaml_path.stem


def resolve_project_path(path: Path) -> Path:
    """Directory containing interview.yaml for a project folder or YAML path."""
    path = path.expanduser()
    if path.is_file():
        if path.name != INTERVIEW_YAML:
            raise ValueError(f"Expected {INTERVIEW_YAML}, got: {path}")
        return path.parent.resolve()
    if path.is_dir() and is_project_directory(path):
        return path.resolve()
    raise FileNotFoundError(f"Not a project folder or interview YAML: {path}")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_project_metadata(slug: str) -> dict[str, Any]:
    return {
        "slug": slug,
        "created": _utc_now_iso(),
        "last_render": None,
        "interview_yaml": INTERVIEW_YAML,
        "paths": {
            "sentences": "sentences",
            "timings": "timings.json",
            "srt": "interview.srt",
            "full_wav": "full_interview.wav",
            "full_mp3": "full_interview.mp3",
            "video": "interview.mp4",
            "work": WORK_DIR,
        },
    }


def write_project_json(project_path: Path, meta: dict[str, Any]) -> None:
    dest = project_path / PROJECT_JSON
    dest.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def load_project_json(project_path: Path) -> dict[str, Any]:
    raw = json.loads((project_path / PROJECT_JSON).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid {PROJECT_JSON}: {project_path}")
    return raw


def touch_last_render(project_path: Path) -> None:
    meta_path = project_path / PROJECT_JSON
    if not meta_path.is_file():
        return
    meta = load_project_json(project_path)
    meta["last_render"] = _utc_now_iso()
    write_project_json(project_path, meta)


def default_interview_yaml(title: str, host: str, guest: str) -> str:
    return (
        f"title: {title}\n"
        "characters:\n"
        f"  host: {host}\n"
        f"  guest: {guest}\n"
        "layout:\n"
        "  dual_start_turns: 4\n"
        "  dual_end_turns: 5\n"
        "script:\n"
        f'  - {{ speaker: {host}, text: "Welcome." }}\n'
        f'  - {{ speaker: {guest}, text: "Thanks for having me." }}\n'
    )


def create_project(
    slug: str,
    *,
    host: str = "leo",
    guest: str = "eve",
    title: str | None = None,
) -> Path:
    validate_slug(slug)
    root = project_dir(slug)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Project already exists: {root}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "sentences").mkdir(exist_ok=True)
    (root / WORK_DIR).mkdir(exist_ok=True)
    show_title = title or slug.replace("-", " ").title()
    yaml_path = root / INTERVIEW_YAML
    yaml_path.write_text(
        default_interview_yaml(show_title, host, guest),
        encoding="utf-8",
    )
    write_project_json(root, new_project_metadata(slug))
    return root


def list_projects() -> list[dict[str, Any]]:
    root = projects_root()
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        yaml_path = child / INTERVIEW_YAML
        if not yaml_path.is_file():
            continue
        row: dict[str, Any] = {
            "slug": child.name,
            "path": str(child),
            "has_video": (child / "interview.mp4").is_file(),
            "modified": yaml_path.stat().st_mtime,
        }
        try:
            data = load_interview(yaml_path)
            row["title"] = data.get("title", child.name)
            chars = data.get("characters") or {}
            row["host"] = chars.get("host", "?")
            row["guest"] = chars.get("guest", "?")
        except (OSError, ValueError):
            row["title"] = child.name
            row["host"] = "?"
            row["guest"] = "?"
        if (child / PROJECT_JSON).is_file():
            try:
                meta = load_project_json(child)
                row["last_render"] = meta.get("last_render")
            except (OSError, json.JSONDecodeError):
                pass
        rows.append(row)
    return rows


def import_interview_yaml(source_yaml: Path, slug: str | None = None) -> Path:
    source_yaml = source_yaml.resolve()
    if not source_yaml.is_file():
        raise FileNotFoundError(f"YAML not found: {source_yaml}")
    dest_slug = slug or source_yaml.stem.replace("_", "-")
    validate_slug(dest_slug)
    root = project_dir(dest_slug)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Project already exists: {root}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "sentences").mkdir(exist_ok=True)
    (root / WORK_DIR).mkdir(exist_ok=True)
    dest_yaml = root / INTERVIEW_YAML
    shutil.copy2(source_yaml, dest_yaml)
    write_project_json(root, new_project_metadata(dest_slug))
    return root


def script_texts(path: Path) -> list[str]:
    return [line["text"] for line in normalized_lines(load_interview(path))]
