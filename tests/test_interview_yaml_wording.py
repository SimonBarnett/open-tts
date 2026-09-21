"""Assert interview YAML script lines match legacy dialogue tuples 1:1."""

import ast
import unittest
from pathlib import Path

from open_tts.script import load_interview, normalized_lines

REPO_ROOT = Path(__file__).resolve().parents[1]


def _dialogue_from_py(py_path: Path) -> list[tuple[str, str]]:
    tree = ast.parse(py_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "dialogue":
                if not isinstance(node.value, ast.List):
                    continue
                rows: list[tuple[str, str]] = []
                for element in node.value.elts:
                    if not isinstance(element, ast.Tuple) or len(element.elts) != 2:
                        continue
                    speaker = ast.literal_eval(element.elts[0])
                    text = ast.literal_eval(element.elts[1])
                    rows.append((speaker, text))
                return rows
    raise ValueError(f"No dialogue list in {py_path}")


def _assert_yaml_matches_py(
    testcase: unittest.TestCase,
    py_rel: str,
    yaml_rel: str,
) -> None:
    expected = _dialogue_from_py(REPO_ROOT / py_rel)
    lines = normalized_lines(load_interview(REPO_ROOT / yaml_rel))
    testcase.assertEqual(
        len(lines),
        len(expected),
        msg=f"{yaml_rel}: script length",
    )
    for index, ((speaker, text), line) in enumerate(zip(expected, lines), start=1):
        testcase.assertEqual(
            line["speaker"],
            speaker,
            msg=f"{yaml_rel} line {index} speaker",
        )
        testcase.assertEqual(line["text"], text, msg=f"{yaml_rel} line {index} text")


class TestInterviewYamlWording(unittest.TestCase):
    def test_technical_vault_matches_interview2(self):
        _assert_yaml_matches_py(
            self,
            "interview2/interview1.py",
            "interviews/technical-vault.yaml",
        )

    def test_white_label_partner_matches_interview_audio3(self):
        _assert_yaml_matches_py(
            self,
            "interview_audio3/interview.py",
            "interviews/white-label-partner.yaml",
        )

    def test_marketing_door_matches_interview_audio4(self):
        _assert_yaml_matches_py(
            self,
            "interview_audio4/interview.py",
            "interviews/marketing-door.yaml",
        )


if __name__ == "__main__":
    unittest.main()
