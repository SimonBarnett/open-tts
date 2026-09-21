# Build and test plan: remaining Leo/Eve YAML scripts

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/3
FR: `docs/feature-request-remaining-leo-eve-yaml-scripts-2026-09-21.md`

## Goals

Express vault, white-label, and marketing-door interviews as `interviews/*.yaml` without changing wording. Render via `python -m open_tts render`. No new per-show Python mux.

## Non-goals

Do not change spoken lines. Do not touch `tts_play.py`. Do not delete `interview*` folders.

## Phases

1. Extract `dialogue` tuples 1:1 from `interview2/interview1.py`, `interview_audio3/interview.py`, `interview_audio4/interview.py`.
2. Write YAML in the same schema as `interviews/partner-smart-catalogue.yaml` (title, host, guest, layout, script lines).
3. Unit-test wording equality (tuple text vs YAML `text` fields, order preserved).
4. `python -m unittest discover -s tests -v`. Do not require ffmpeg or live TTS for the wording tests.

## Locked

- Character ids stay `leo` / `eve` from `characters/registry.yaml`.
- Keys stay in the environment (`XAI_API_KEY`). Never in git.

## Definition of done

Issue #3 acceptance checkboxes are green. PR opened from `work/<job>`. Never push `main`. Never merge.
