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
