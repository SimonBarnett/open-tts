"""Assert legacy interview dialogue tuples match interviews/*.yaml wording."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from open_tts.script import normalized_lines, load_interview

REPO_ROOT = Path(__file__).resolve().parents[1]

CASES = (
    (
        REPO_ROOT / "interviews" / "technical-vault.yaml",
        REPO_ROOT / "interview2" / "interview1.py",
        50,
    ),
    (
        REPO_ROOT / "interviews" / "white-label-partner.yaml",
        REPO_ROOT / "interview_audio3" / "interview.py",
        47,
    ),
    (
        REPO_ROOT / "interviews" / "marketing-door.yaml",
        REPO_ROOT / "interview_audio4" / "interview.py",
        75,
    ),
)


def _dialogue_from_py(py_path: Path) -> list[tuple[str, str]]:
    tree = ast.parse(py_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "dialogue":
                    value = ast.literal_eval(node.value)
                    if not isinstance(value, list):
                        raise ValueError(f"dialogue is not a list in {py_path}")
                    return value
    raise ValueError(f"no dialogue assignment in {py_path}")


def _pairs_from_yaml(yaml_path: Path) -> list[tuple[str, str]]:
    data = load_interview(yaml_path)
    return [(line["speaker"], line["text"]) for line in normalized_lines(data)]


class InterviewYamlWordingTests(unittest.TestCase):
    def test_legacy_dialogue_matches_yaml(self) -> None:
        for yaml_path, py_path, expected_len in CASES:
            with self.subTest(yaml=yaml_path.name):
                legacy = _dialogue_from_py(py_path)
                yaml_pairs = _pairs_from_yaml(yaml_path)
                self.assertEqual(len(legacy), expected_len)
                self.assertEqual(len(yaml_pairs), expected_len)
                self.assertEqual(yaml_pairs, legacy)


if __name__ == "__main__":
    unittest.main()
