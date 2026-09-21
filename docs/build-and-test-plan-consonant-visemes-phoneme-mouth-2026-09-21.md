# Build and test plan: extra consonant visemes

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/11
FR: `docs/feature-request-consonant-visemes-phoneme-mouth-2026-09-21.md`

## Goals / non-goals

Add the consonant row and phone-timed lookup. Do not paint final art. Do not implement #9/#10. Tests without ffmpeg or display.

## Phases

1. Constants + placeholder row in `open_tts/sprite.py`.
2. G2P + P2V for `"map"`, `"vault"`, `"beat"`.
3. Persist `phones` on timings; `_frame_for_line` uses `[t0, t1)`.
4. `python -m unittest discover -s tests -v`.

## Definition of done

Issue #11 acceptance green. PR from `work/<job>`. Never push `main`. Never merge.
