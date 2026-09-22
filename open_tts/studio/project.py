"""Resolve YAML + output directory for studio --edit."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from open_tts.project import INTERVIEW_YAML, default_output_dir, is_project_directory
from open_tts.script import layout_options, load_interview, normalized_lines


@dataclass(frozen=True)
class StudioProject:
    yaml_path: Path
    output_dir: Path

    @property
    def timings_path(self) -> Path:
        return self.output_dir / "timings.json"

    @property
    def video_path(self) -> Path:
        return self.output_dir / "interview.mp4"

    @property
    def audio_path(self) -> Path:
        wav = self.output_dir / "full_interview.wav"
        if wav.is_file():
            return wav
        return self.output_dir / "full_interview.mp3"

    def media_path(self) -> Path:
        """Prefer muxed MP4 (video + audio); else the mixdown."""
        if self.video_path.is_file():
            return self.video_path
        return self.audio_path

    def load_data(self) -> dict:
        return load_interview(self.yaml_path)

    def load_segments(self) -> list[dict]:
        return json.loads(self.timings_path.read_text(encoding="utf-8"))

    def layout(self, data: dict | None = None) -> dict:
        return layout_options(data or self.load_data())

    def lines(self, data: dict | None = None) -> list[dict]:
        return normalized_lines(data or self.load_data())


def resolve_edit_target(path: Path) -> StudioProject:
    path = path.resolve()
    if path.suffix.lower() in (".yaml", ".yml"):
        yaml_path = path
        output_dir = default_output_dir(yaml_path)
        return StudioProject(yaml_path=yaml_path, output_dir=output_dir)

    if not path.is_dir():
        raise ValueError(f"Not a YAML file or output directory: {path}")

    if is_project_directory(path):
        yaml_path = path / INTERVIEW_YAML
        return StudioProject(yaml_path=yaml_path, output_dir=path)

    timings = path / "timings.json"
    if not timings.is_file():
        raise ValueError(f"Output directory missing timings.json: {path}")

    stem = path.name
    if path.parent.name == "output":
        yaml_path = path.parent.parent / f"{stem}.yaml"
    else:
        yaml_path = path / f"{stem}.yaml"
        if not yaml_path.is_file():
            yaml_path = path.parent / f"{stem}.yaml"

    if not yaml_path.is_file():
        raise ValueError(
            f"Could not find interview YAML for output dir {path} (tried {yaml_path})"
        )

    return StudioProject(yaml_path=yaml_path, output_dir=path)
