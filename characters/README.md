# Character sprite sheets

Every character uses the same **6×N** grid (`open_tts/sprite.py`). There are no per-character layout files.

| Row | Purpose | Columns (left → right) |
|-----|---------|-------------------------|
| 0 | Vowel visemes | `a`, `e`, `i`, `o`, `u`, `pause` |
| 1 | Consonant visemes | `mbp`, `fv`, `th`, `l`, `sz`, `sh` |
| 2 | Expressions | `surprise`, `laugh`, `smile`, `concern`, `think`, `listen` |
| 3+ | Animation strips | Two rows per expression column (placeholder art today) |

`CharacterSheet` methods (`viseme`, `laugh`, `smile`, …) resolve to the same `(col, row)` on Leo, Eve, and any other sheet. Missing sheets are created via `ensure_placeholder_sheet`.

Viseme grids live in `characters/visemes/` and are **shared**. A model (Leo, Eve, …) selects a set unless you bake a new one from a still. Interview stage slots are **left** and **right** (one, the other, or both).
