import json
import tempfile
import unittest
from pathlib import Path

from open_tts.project import (
    create_project,
    default_output_dir,
    ensure_project_in_folder,
    import_interview_yaml,
    list_projects,
    projects_root,
    script_texts,
    slug_from_title,
)


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
        self.assertTrue((path / "characters").is_dir())
        self.assertTrue((path / "assets").is_dir())
        self.assertTrue((path / "_work").is_dir())
        texts = script_texts(path / "interview.yaml")
        self.assertEqual(len(texts), 2)
        self.assertEqual(texts[0], "Welcome.")
        self.assertEqual(texts[1], "Thanks for having me.")
        raw = (path / "interview.yaml").read_text(encoding="utf-8")
        self.assertIn("left: leo", raw)
        self.assertIn("right: eve", raw)
        meta = json.loads((path / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["slug"], "vault-technical")
        self.assertIsNone(meta["last_render"])

    def test_slug_from_title(self) -> None:
        self.assertEqual(slug_from_title("Hello Studio"), "hello-studio")
        self.assertEqual(slug_from_title("  "), "interview")

    def test_create_uses_last_cast(self) -> None:
        import os

        from open_tts.prefs import remember_cast

        self._env_projects()
        prefs = self.root / "prefs.json"
        os.environ["OPEN_TTS_PREFS_PATH"] = str(prefs)
        self.addCleanup(lambda: os.environ.pop("OPEN_TTS_PREFS_PATH", None))
        remember_cast("eve", "leo")
        path = create_project("from-last-cast")
        raw = (path / "interview.yaml").read_text(encoding="utf-8")
        self.assertIn("host: eve", raw)
        self.assertIn("guest: leo", raw)
        self.assertIn("left: eve", raw)
        self.assertIn("right: leo", raw)

    def test_open_folder_creates_or_reopens(self) -> None:
        import os

        from open_tts.prefs import remember_cast

        self._env_projects()
        os.environ["OPEN_TTS_PREFS_PATH"] = str(self.root / "prefs.json")
        self.addCleanup(lambda: os.environ.pop("OPEN_TTS_PREFS_PATH", None))
        remember_cast("leo", "eve")
        folder = self.root / "scratch-show"
        folder.mkdir()
        first = ensure_project_in_folder(folder)
        self.assertTrue((first / "interview.yaml").is_file())
        self.assertTrue((first / "project.json").is_file())
        for name in ("sentences", "characters", "assets", "_work"):
            self.assertTrue((first / name).is_dir())
        texts = script_texts(first / "interview.yaml")
        self.assertEqual(texts[0], "Welcome.")
        raw = (first / "interview.yaml").read_text(encoding="utf-8")
        edited = raw.replace("Welcome.", "Stay put.")
        (first / "interview.yaml").write_text(edited, encoding="utf-8")
        again = ensure_project_in_folder(folder)
        self.assertEqual(again, first)
        self.assertIn("Stay put.", (again / "interview.yaml").read_text(encoding="utf-8"))

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


if __name__ == "__main__":
    unittest.main()
