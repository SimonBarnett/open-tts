import json
import tempfile
import unittest
from pathlib import Path

from open_tts.studio.dirty import (
    block_index_for_line,
    dirty_block_indices_for_line,
)
from open_tts.video import merged_speaker_blocks


def _sample_segments() -> list[dict]:
    return [
        {
            "id": i,
            "speaker": "leo" if i <= 4 else "eve",
            "start": float(i - 1),
            "end": float(i),
            "duration": 1.0,
        }
        for i in range(1, 11)
    ]


class TestDirtyBlocks(unittest.TestCase):
    def test_block_index_for_line(self):
        segments = _sample_segments()
        idx = block_index_for_line(
            3, segments, audio_duration=20.0, dual_start=4, dual_end=5
        )
        self.assertEqual(idx, 0)
        idx_eve = block_index_for_line(
            7, segments, audio_duration=20.0, dual_start=4, dual_end=5
        )
        self.assertEqual(idx_eve, 2)

    def test_cue_change_marks_single_block(self):
        segments = _sample_segments()
        dirty = dirty_block_indices_for_line(
            7,
            segments,
            audio_duration=20.0,
            dual_start=4,
            dual_end=5,
            cue_changed=True,
        )
        blocks = merged_speaker_blocks(segments, 20.0, 4, 5)
        self.assertEqual(dirty, {2})
        self.assertEqual(len(blocks), 3)

    def test_speaker_change_marks_all_blocks(self):
        segments = _sample_segments()
        dirty = dirty_block_indices_for_line(
            5,
            segments,
            audio_duration=20.0,
            dual_start=4,
            dual_end=5,
            speaker_changed=True,
        )
        self.assertEqual(dirty, {0, 1, 2})

    def test_text_change_marks_containing_block(self):
        segments = _sample_segments()
        dirty = dirty_block_indices_for_line(
            2,
            segments,
            audio_duration=20.0,
            dual_start=4,
            dual_end=5,
            text_changed=True,
        )
        self.assertEqual(dirty, {0})


class TestResolveProject(unittest.TestCase):
    def test_yaml_path_resolves_default_output_dir(self):
        from open_tts.studio.project import resolve_edit_target

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yaml_path = root / "interviews" / "demo.yaml"
            yaml_path.parent.mkdir(parents=True)
            yaml_path.write_text(
                "title: Demo\ncharacters: {host: leo, guest: eve}\nscript: []\n",
                encoding="utf-8",
            )
            proj = resolve_edit_target(yaml_path)
            self.assertEqual(proj.yaml_path.resolve(), yaml_path.resolve())
            self.assertEqual(
                proj.output_dir.resolve(),
                (root / "interviews" / "output" / "demo").resolve(),
            )

    def test_yaml_path_resolves_partner_style_output_dir(self):
        from open_tts.studio.project import resolve_edit_target

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yaml_path = root / "interviews" / "partner-smart-catalogue.yaml"
            yaml_path.parent.mkdir(parents=True)
            yaml_path.write_text(
                "title: T\ncharacters: {host: leo, guest: eve}\nscript: []\n",
                encoding="utf-8",
            )
            proj = resolve_edit_target(yaml_path)
            self.assertEqual(
                proj.output_dir.resolve(),
                (root / "interviews" / "output" / "partner-smart-catalogue").resolve(),
            )

    def test_project_folder_resolves_interview_yaml(self):
        from open_tts.project import INTERVIEW_YAML
        from open_tts.studio.project import resolve_edit_target

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "vault-technical"
            proj.mkdir(parents=True)
            yaml_path = proj / INTERVIEW_YAML
            yaml_path.write_text(
                "title: T\ncharacters: {host: leo, guest: eve}\nscript: []\n",
                encoding="utf-8",
            )
            (proj / "timings.json").write_text("[]", encoding="utf-8")
            resolved = resolve_edit_target(proj)
            self.assertEqual(resolved.yaml_path.resolve(), yaml_path.resolve())
            self.assertEqual(resolved.output_dir.resolve(), proj.resolve())

    def test_output_dir_under_interviews_output_finds_yaml(self):
        from open_tts.studio.project import resolve_edit_target

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            interviews = root / "interviews"
            out = interviews / "output" / "partner-smart-catalogue"
            out.mkdir(parents=True)
            (out / "timings.json").write_text(json.dumps([]), encoding="utf-8")
            yaml_path = interviews / "partner-smart-catalogue.yaml"
            yaml_path.write_text(
                "title: T\ncharacters: {host: leo, guest: eve}\nscript: []\n",
                encoding="utf-8",
            )
            proj = resolve_edit_target(out)
            self.assertEqual(proj.yaml_path.resolve(), yaml_path.resolve())
            self.assertEqual(proj.output_dir.resolve(), out.resolve())

    def test_output_dir_to_yaml(self):
        from pathlib import Path

        from open_tts.studio.project import resolve_edit_target

        root = Path(__file__).resolve().parent.parent
        out = root / "interviews" / "output" / "partner-smart-catalogue"
        if not (out / "timings.json").is_file():
            self.skipTest("partner-smart-catalogue output not present")
        proj = resolve_edit_target(out)
        self.assertEqual(proj.yaml_path.name, "partner-smart-catalogue.yaml")
        self.assertEqual(proj.output_dir, out.resolve())

    def test_media_path_prefers_mp4(self) -> None:
        from open_tts.studio.project import StudioProject

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yaml_path = root / "show.yaml"
            out = root / "output"
            out.mkdir()
            yaml_path.write_text("title: T\n", encoding="utf-8")
            (out / "full_interview.wav").write_bytes(b"RIFF")
            proj = StudioProject(yaml_path=yaml_path, output_dir=out)
            self.assertEqual(proj.media_path(), proj.audio_path)
            (out / "interview.mp4").write_bytes(b"ftyp")
            self.assertEqual(proj.media_path(), proj.video_path)


if __name__ == "__main__":
    unittest.main()
