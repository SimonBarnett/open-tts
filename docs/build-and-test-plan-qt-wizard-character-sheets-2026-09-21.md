# Build and test plan: Qt wizard character sheets + script editor

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/9
FR: `docs/feature-request-qt-wizard-character-sheets-2026-09-21.md`

## Goals / non-goals

Ship `python -m open_tts.studio` as a PySide6 client of existing render models. Do not require a display or ffmpeg in CI. Do not implement #3 wording dumps. Do not put keys in git.

## Phases

1. Cue helper (`open_tts/cues.py`) unit-tested without Qt: partner enthusiasm line → `laugh`.
2. Image provider interface (`generate_still`, `generate_sheet`) behind env-configured xAI family; key from environment.
3. Qt flows A (character) and B (script table). Save `characters/<id>.png` + registry + YAML schema from #1.
4. Headless tests for cue suggestion and sheet index contract. Skip live image LLM in CI.

## Definition of done

Issue #9 acceptance green. PR from `work/<job>`. Never push `main`. Never merge.

## Board (MRB #146)

- Delivery object: tip of open PR `work/a96edc39-b16d-4f00-ba97-f7f0e15cd96e` vs `origin/main` (`MERGEABLE` / `CLEAN`). Not merge commit `37be23c` / PR #143 (issue #141). Do not merge stale PRs #133, #125, or #83.
- Regress gates from PR #139 / MRB #140: wizard `MainWindow`, `--edit` → `run_edit_app`, Keep-before-bake, six-across laugh strip, headless tests in `tests/test_studio_*.py`, `tests/test_cues.py`, `tests/test_sprite.py`.
