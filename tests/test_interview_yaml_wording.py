"""Assert interview YAML scripts match legacy dialogue tuples 1:1."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from open_tts.script import load_interview, normalized_lines

ROOT = Path(__file__).resolve().parents[1]


def _dialogue_from_py(rel_path: str) -> list[tuple[str, str]]:
    tree = ast.parse((ROOT / rel_path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "dialogue":
                    return ast.literal_eval(node.value)
    raise AssertionError(f"dialogue not found in {rel_path}")


def _yaml_pairs(rel_path: str) -> list[tuple[str, str]]:
    data = load_interview(ROOT / rel_path)
    return [(line["speaker"], line["text"]) for line in normalized_lines(data)]


class InterviewYamlWordingTests(unittest.TestCase):
    def test_technical_vault_matches_interview2(self):
        py = _dialogue_from_py("interview2/interview1.py")
        yaml_lines = _yaml_pairs("interviews/technical-vault.yaml")
        self.assertEqual(len(py), 50)
        self.assertEqual(py, yaml_lines)

    def test_white_label_partner_matches_interview_audio3(self):
        py = _dialogue_from_py("interview_audio3/interview.py")
        yaml_lines = _yaml_pairs("interviews/white-label-partner.yaml")
        self.assertEqual(len(py), 47)
        self.assertEqual(py, yaml_lines)

    def test_marketing_door_matches_interview_audio4(self):
        py = _dialogue_from_py("interview_audio4/interview.py")
        yaml_lines = _yaml_pairs("interviews/marketing-door.yaml")
        self.assertEqual(len(py), 75)
        self.assertEqual(py, yaml_lines)


if __name__ == "__main__":
    unittest.main()
