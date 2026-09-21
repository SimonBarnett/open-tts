# Character sprite sheets

Every character uses the same **6×N** grid (`open_tts/sprite.py`). There are no per-character layout files.

| Row | Purpose | Columns (left → right) |
|-----|---------|-------------------------|
| 0 | Vowel visemes | `a`, `e`, `i`, `o`, `u`, `pause` |
| 1 | Consonant visemes | `mbp`, `fv`, `th`, `l`, `sz`, `sh` |
| 2 | Expressions | `surprise`, `laugh`, `smile`, `concern`, `think`, `listen` |
| 3+ | Animation strips | Two rows per expression column (placeholder art today) |

`CharacterSheet` methods (`viseme`, `mbp`, `laugh`, `smile`, …) resolve to the same `(col, row)` on Leo, Eve, and any other sheet. Missing sheets are created via `ensure_placeholder_sheet`.

`pause` is the rest mouth on row 0; `mbp` is the closed speech shape on row 1. They are not aliased.
