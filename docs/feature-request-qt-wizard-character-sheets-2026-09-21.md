# Feature request: Qt wizard for character sheets and script editor

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/9

## Summary

Desktop Qt (PySide6) wizard: describe a character, generate a still with an image LLM until Keep, bake a viseme/expression sheet on the shared grid, edit the script in a table with auto-suggested animation cues, write `characters/registry.yaml` + `interviews/*.yaml`, hand off to `python -m open_tts render`.

Depends on issue #1 engine (`CharacterSheet`, `VISEME_COL` / `EXPRESSION_COL`). Does not replace Grok TTS or `tts_play.py`.

## Gap vs current tree

Landed on `main` via PR #139 / MRB #140 (`2948d4c`). This FR tracks acceptance and docs; board delivery is an open `work/<job>` PR (MRB #146), not a merged `main` merge commit such as PR #143.

## Locked

- Launch: `python -m open_tts.studio`
- Shared grid: row 0 visemes A E I O U pause; row 1 expressions surprise, laugh, …; animation strips six frames across per expression.
- Secrets: `XAI_API_KEY` (and a distinct image-key env if needed). `.env` gitignored.
- Cue suggestion is deterministic and overridable.

## Out of scope

Replacing Grok TTS voices or audiotour JSON. Full lip-sync ML. Authoring the three remaining interview YAMLs (#3) inside this job. Hand-painted Leo/Eve art.

## Acceptance

- [x] `python -m open_tts.studio` opens a Qt wizard (PySide6).
- [x] Character flow: description → image LLM still → Keep / Again until lock → sheet on shared indices.
- [x] Saved character appears in `registry.yaml`; `CharacterSheet.laugh()` / `.viseme("o")` match Leo/Eve cells.
- [x] Script editor loads and saves #1-compatible YAML; animation column auto-fills and can be overridden.
- [x] Partner line "There's always a bit of sales enthusiasm!" suggests `laugh` and can be set to `pause`.
- [x] No API keys in the repo. No new per-show Python mux script.
