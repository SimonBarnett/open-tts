"""Load gitignored repo-root .env into os.environ (do not overwrite)."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_repo_env(path: Path | None = None) -> Path | None:
    """Set missing KEY=value pairs from `.env`. Returns the path if it exists."""
    env_path = path if path is not None else repo_root() / ".env"
    if not env_path.is_file():
        return None
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value
    return env_path
