# Character sprite sheets

Every character uses the same **6×N** grid (`open_tts/sprite.py`). There are no per-character layout files.

| Row | Purpose | Columns (left → right) |
|-----|---------|-------------------------|
| 0 | Vowel visemes | `a`, `e`, `i`, `o`, `u`, `pause` |
| 1 | Consonant visemes | `mbp`, `fv`, `th`, `l`, `sz`, `sh` |
| 2 | Expressions | `surprise`, `laugh`, `smile`, `concern`, `think`, `listen` (`attentive` alias) |
| 3+ | Animation strips | Two rows per expression column (placeholder art today) |

`CharacterSheet` methods (`viseme`, `laugh`, `smile`, …) resolve to the same `(col, row)` on Leo, Eve, and any other sheet. Missing sheets are created via `ensure_placeholder_sheet`.

Viseme grids live in `characters/visemes/` and are **shared**. A model (Leo, Eve, …) selects a set unless you bake a new one from a still. Interview stage slots are **left** and **right** (one, the other, or both).

Original Leo cells are **full-screen monologue** close-ups. Original Eve cells are **left/right half-screen** interview shots (person on one side, set around them). `open_tts/framing.py` derives both from each cell: tight head-and-shoulders for solo, medium half-frame for split. Toggle with `split: true|false` on the line, or leave it off to use `layout.dual_start_turns` / `dual_end_turns`. In split, the silent character plays the **attentive** animation (`listen` cells).

To swap a character mid-show, set `left:` / `right:` on that line (inherits until the next override). `swap: true` flips the two sides from that line on. Studio: **Left** / **Right** columns, or **Swap sides here**.
