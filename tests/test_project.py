import json
import tempfile
import unittest
from pathlib import Path

from open_tts.project import (
    create_project,
    default_output_dir,
    import_interview_yaml,
    list_projects,
    projects_root,
    script_texts,
)
from open_tts.tts import ensure_sentence_audio


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

    def test_skip_tts_reuses_existing_project_sentence_mp3(self) -> None:
        self._env_projects()
        path = create_project("reuse-show", host="leo", guest="eve")
        mp3 = path / "sentences" / "leo_001.mp3"
        mp3.write_bytes(b"existing-mp3")
        before = mp3.read_bytes()
        ensure_sentence_audio("Welcome.", "leo", mp3, skip_tts=True)
        self.assertEqual(mp3.read_bytes(), before)

    def test_skip_tts_requires_existing_mp3_in_project(self) -> None:
        self._env_projects()
        path = create_project("missing-audio", host="leo", guest="eve")
        mp3 = path / "sentences" / "leo_001.mp3"
        with self.assertRaises(FileNotFoundError):
            ensure_sentence_audio("Welcome.", "leo", mp3, skip_tts=True)


if __name__ == "__main__":
    unittest.main()
