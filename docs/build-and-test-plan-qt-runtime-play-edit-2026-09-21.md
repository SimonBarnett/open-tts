# Build and test plan: Qt runtime play and edit

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/13
FR: `docs/feature-request-qt-runtime-play-edit-2026-09-21.md`

## Goals / non-goals

Player + inspector as a client of `render_interview`. Unit-test dirty-block selection without Qt. Do not require a display in CI. Do not implement #9 character generation.

## Phases

1. `which blocks are dirty given a line id` helper + tests.
2. YAML load/save in #1 schema from inspector fields.
3. Qt player bound to `timings.json`.
4. Re-render actions call existing engine; skip TTS when sentence MP3 exists and text is unchanged.

## Definition of done

Issue #13 acceptance green. PR from `work/<job>`. Never push `main`. Never merge.
