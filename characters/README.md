# Character sprite sheets

Every character uses the same **6×N** grid defined in `open_tts/sprite.py`. There are no per-character layout files.

## Row 0 — visemes (`VISEME_ROW`)

| Column | id |
|--------|-----|
| 0 | `a` |
| 1 | `e` |
| 2 | `i` |
| 3 | `o` |
| 4 | `u` |
| 5 | `pause` |

## Row 1 — expressions (`EXPRESSION_ROW`)

| Column | id |
|--------|-----|
| 0 | `surprise` |
| 1 | `laugh` |
| 2 | `smile` |
| 3 | `concern` |
| 4 | `think` |
| 5 | `listen` |

## Rows 2+ — animation strips

Each expression id has one row of six frames (columns 0–5), starting at `ANIMATION_START_ROW`. The animation row index is `ANIMATION_START_ROW + EXPRESSION_COL[id]`.

Placeholder sheets are generated with `ensure_placeholder_sheet`; paths are listed in `registry.yaml`.
