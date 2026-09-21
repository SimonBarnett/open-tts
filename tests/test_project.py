import json
import math
import shutil
import tempfile
import unittest
import wave
from pathlib import Path

from open_tts.project import (
    create_project,
    default_output_dir,
    import_interview_yaml,
    list_projects,
    projects_root,
    script_texts,
)
from open_tts.render import render_interview


def _tone_wav(path: Path, duration_sec: float = 0.25) -> None:
    rate = 24000
    n = int(rate * duration_sec)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            val = int(8000 * math.sin(2 * math.pi * 440 * i / rate))
            frames += int(val).to_bytes(2, "little", signed=True)
        wf.writeframes(frames)


class TestProjectFolders(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.root = Path(self._tmpdir.name)
        self.projects = self.root / "projects"
        self.projects.mkdir()

    def _env_projects(self) -> None:
        import os

        os.environ["OPEN_TTS_PROJECTS_DIR"] = str(self.projects)

    def test_default_output_dir_legacy(self) -> None:
        yaml = self.root / "interviews" / "show.yaml"
        yaml.parent.mkdir(parents=True)
        yaml.write_text("title: x\ncharacters: {}\nscript: []\n", encoding="utf-8")
        self.assertEqual(
            default_output_dir(yaml),
            self.root / "interviews" / "output" / "show",
        )

    def test_default_output_dir_project(self) -> None:
        self._env_projects()
        slug = "vault-technical"
        proj = self.projects / slug
        proj.mkdir()
        yaml = proj / "interview.yaml"
        yaml.write_text("title: x\ncharacters: {}\nscript: []\n", encoding="utf-8")
        self.assertEqual(default_output_dir(yaml), proj.resolve())

    def test_new_project_layout(self) -> None:
        self._env_projects()
        path = create_project("vault-technical", host="leo", guest="eve")
        self.assertTrue((path / "interview.yaml").is_file())
        self.assertTrue((path / "project.json").is_file())
        self.assertTrue((path / "sentences").is_dir())
        meta = json.loads((path / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["slug"], "vault-technical")
        self.assertIsNone(meta["last_render"])

    def test_list_projects(self) -> None:
        self._env_projects()
        create_project("alpha-show", host="leo", guest="eve")
        rows = list_projects()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["slug"], "alpha-show")

    def test_import_partner_yaml_preserves_script(self) -> None:
        repo = Path(__file__).resolve().parent.parent
        source = repo / "interviews" / "partner-smart-catalogue.yaml"
        if not source.is_file():
            self.skipTest("partner-smart-catalogue.yaml not in tree")
        self._env_projects()
        before = script_texts(source)
        dest_root = import_interview_yaml(source, slug="partner-smart-catalogue")
        after = script_texts(dest_root / "interview.yaml")
        self.assertEqual(before, after)
        self.assertTrue((dest_root / "project.json").is_file())

    def test_projects_root_override(self) -> None:
        self._env_projects()
        self.assertEqual(projects_root(), self.projects.resolve())

    def test_skip_tts_reuses_project_sentence_mp3(self) -> None:
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg not on PATH")
        self._env_projects()
        root = create_project("reuse-audio", host="leo", guest="eve")
        yaml_path = root / "interview.yaml"
        speech = root / "sentences"
        for name in ("leo_001.mp3", "eve_002.mp3"):
            mp3 = speech / name
            mp3.write_bytes(b"\x00")
            wav = speech / name.replace(".mp3", ".wav")
            _tone_wav(wav)
            mp3.touch()
        out = render_interview(yaml_path, skip_tts=True, video=False)
        self.assertEqual(out.resolve(), root.resolve())
        self.assertTrue((root / "timings.json").is_file())
        self.assertTrue((root / "full_interview.wav").is_file())


if __name__ == "__main__":
    unittest.main()
