# Feature request: viseme mapping pipeline

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/12

## Summary

Replace `viseme_sequence_for_text` (spelling vowels cycled at 6 Hz) with:

```
text → phones → viseme ids → [t0, t1) → frame cell
      G2P         P2V table      aligner        lookup
```

This FR is the algorithm; #11 is the extra cells those algorithms must target. Until #11 lands extra cells, map `mbp/fv/th/l/sz/sh` → `pause` (or nearest vowel) so this FR can merge first.

## Locked algorithms

1. **G2P** — CMUdict ARPAbet; small `g2p_en` fallback for OOV; strip stress; deterministic.
2. **P2V** — one table in `open_tts/visemes.py`. Diphthongs split in time. Jeffers / Disney / Bozkurt stay out.
3. **Alignment v1** — TTS `with_timestamps` if present; else weighted slice of sentence duration. MFA is v2 (out of this issue).
4. **Coarticulation** — last 30–50 ms of phone `i` may show `v_{i+1}`. No Cohen–Massaro.

## Out of scope

Painting extra sheet row (#11). Expression vocabulary (#10). Qt wizard (#9). MFA in v1. Neural G2P. Remaining interview YAML (#3).

## Acceptance

- [ ] `open_tts/visemes.py` owns G2P + P2V + interval build; widgets and `video.py` only look up `v(t)`.
- [ ] `"vault"` → phones including `V`/`AO`; viseme track is not `[a, u]` from spelling.
- [ ] `"beat"` → `IY` → `i`; `"map"` contains an `mbp` (or `pause` stand-in pre-#11) interval.
- [ ] Frame at time `t` uses `[t0, t1)`, not `t * 6 % n`.
- [ ] Line-level cues still win over visemes.
- [ ] Tests do not need ffmpeg or a display.
- [ ] `tts_play.py` untouched. No keys in git.
