# Feature request: extra consonant visemes + phoneme-timed mouth mapping

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/11

## Summary

Row 0 is full (`A E I O U pause`). Add a second viseme row of six extra cells shared by every character, and drive mouths from phonemes + timestamps instead of cycling spelling vowels.

Expressions (#10) stay on their own row. Line cues still override visemes.

## Locked extra visemes (`CONSONANT_ROW = 1`; shift expression row down or document the new number in one place)

| col | id | ARPAbet in |
|---|---|---|
| 0 | `mbp` | P B M EM |
| 1 | `fv` | F V |
| 2 | `th` | TH DH |
| 3 | `l` | L EL |
| 4 | `sz` | S Z T D N |
| 5 | `sh` | SH ZH CH JH |

Diphthongs are two cells in time (`AY` = `a` then `i`), not a new id. `pause` is rest; `mbp` is the closed speech shape. Do not alias them.

## Out of scope

Qt wizard (#9). Extra expressions (#10). Remaining interview YAML (#3). Full MFA / ML lip-sync. Changing Grok voice ids.

## Acceptance

- [ ] Shared `CONSONANT_VISEME_COL` for `mbp fv th l sz sh`; Leo and Eve resolve to the same cells.
- [ ] `CharacterSheet` exposes those ids; placeholder generator includes the row.
- [ ] G2P + table: `"map"` contains an `mbp` interval; `"vault"` contains `fv` then `o`; `"beat"` maps to `i`.
- [ ] Video uses the phone track at time `t`, not letter cycling.
- [ ] `--skip-tts` still works if a sidecar alignment (or G2P + duration weights) is present.
- [ ] No API keys in git. `tts_play.py` untouched.
