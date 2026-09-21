# Character sprite sheets

Every character uses the same **6×N** grid (`open_tts/sprite.py`). There are no per-character layout files.

| Row | Purpose | Columns (left → right) |
|-----|---------|-------------------------|
| 0 | Vowel visemes | `a`, `e`, `i`, `o`, `u`, `pause` |
| 1 | Consonant visemes | `mbp`, `fv`, `th`, `l`, `sz`, `sh` |
| 2 | Expressions | `surprise`, `laugh`, `smile`, `concern`, `think`, `listen` |
| 3+ | Animation strips | Two rows per expression column (placeholder art today) |

`CharacterSheet` methods (`viseme`, `mbp`, `fv`, `laugh`, `smile`, …) resolve to the same `(col, row)` on Leo, Eve, and any other sheet. `pause` is rest; `mbp` is the closed speech shape — they are different cells. Missing or undersized sheets are created or upgraded via `ensure_placeholder_sheet`.
