# Character sprite sheets

All characters (Leo, Eve, …) share the same grid layout in `open_tts/sprite.py`.

| Row | Content |
|-----|---------|
| 0 | Vowels + rest: `a` `e` `i` `o` `u` `pause` (cols 0–5) |
| 1 | Consonant visemes: `mbp` `fv` `th` `l` `sz` `sh` (cols 0–5) |
| 2 | Expression cues: `surprise` (col 0), `laugh` (col 1) |
| 3+ | Two-frame animation strips per expression column |

`pause` is the closed-rest mouth on row 0. `mbp` on row 1 is the closed speech shape — they are not aliased.

Phoneme timing and viseme ids come from `open_tts/visemes.py`; video frames pick the cell at time `t` via `[t0, t1)` on the line’s `phones` track.
