# Feature request: expand shared expression set

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/10

## Summary

Grow the character-agnostic expression vocabulary. Today `EXPRESSION_COL` is only `surprise` (col 0) and `laugh` (col 1). Four of six columns are unused; unknown cues (including issue #1 example `cue: smile`) fall through to vowel visemes.

Every new type lands at the same (col, row) on every sheet. `character.smile` / `.think` / … work like `.laugh`.

## Locked set (row 1)

| col | id |
|---|---|
| 0 | `surprise` (exists) |
| 1 | `laugh` (exists) |
| 2 | `smile` |
| 3 | `concern` |
| 4 | `think` |
| 5 | `listen` |

Unknown `cue` values must error at script load, not silently mouth vowels.

## Auto-suggest (deterministic)

- `laugh` — laugh, haha, enthusiasm, hilarious
- `surprise` — ?, wow, really, unusual
- `smile` — thank, pleasure, welcome, delighted, great to be
- `concern` — unfortunately, oversell, risk, but
- `think` — well, so, technically, database, vault
- `listen` — empty text, `…`, or non-speaking side of a split block
- else `auto` (visemes)

## Out of scope

Qt wizard chrome (#9). Remaining interview YAML (#3). Lip-sync ML. Hand-painted final art.

## Acceptance

- [ ] `EXPRESSION_COL` includes `smile`, `concern`, `think`, `listen` at fixed columns shared by all sheets.
- [ ] `CharacterSheet` has methods / frames for each; Leo and Eve resolve to the same indices.
- [ ] `cue: smile` (and the new ids) drive those cells in `open_tts/video.py`; unknown cues fail closed.
- [ ] Placeholder sheet generator paints the new cells.
- [ ] Cue helper suggests `smile` / `laugh` on the partner wording.
- [ ] Docs name the grid. No per-character layout files.
