"""YAML interview scripts must match legacy Python dialogue tuples 1:1."""

import ast
import unittest
from pathlib import Path

from open_tts.script import load_interview, normalized_lines

REPO = Path(__file__).resolve().parents[1]


def dialogue_from_python(path: Path) -> list[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "dialogue":
                    return ast.literal_eval(ast.unparse(node.value))
    raise AssertionError(f"no dialogue assignment in {path}")


def yaml_lines(path: Path) -> list[tuple[str, str]]:
    data = load_interview(path)
    return [(line["speaker"], line["text"]) for line in normalized_lines(data)]


class InterviewYamlWordingTests(unittest.TestCase):
    def test_technical_vault_matches_interview2(self) -> None:
        py = REPO / "interview2" / "interview1.py"
        yml = REPO / "interviews" / "technical-vault.yaml"
        self.assertEqual(dialogue_from_python(py), yaml_lines(yml))

    def test_white_label_partner_matches_interview_audio3(self) -> None:
        py = REPO / "interview_audio3" / "interview.py"
        yml = REPO / "interviews" / "white-label-partner.yaml"
        self.assertEqual(dialogue_from_python(py), yaml_lines(yml))

    def test_marketing_door_matches_interview_audio4(self) -> None:
        py = REPO / "interview_audio4" / "interview.py"
        yml = REPO / "interviews" / "marketing-door.yaml"
        self.assertEqual(dialogue_from_python(py), yaml_lines(yml))


if __name__ == "__main__":
    unittest.main()
