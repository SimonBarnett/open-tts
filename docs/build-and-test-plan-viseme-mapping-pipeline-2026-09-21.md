# Build and test plan: viseme mapping pipeline

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/12
FR: `docs/feature-request-viseme-mapping-pipeline-2026-09-21.md`

## Goals / non-goals

Replace letter cycling with G2P + P2V + intervals. Pre-#11 consonants may map to `pause`. No display, no ffmpeg, no MFA.

## Phases

1. `open_tts/visemes.py` with locked ARPAbet table and tests for vault/beat/map.
2. Timings persist `phones[{phone,viseme,t0,t1}]`.
3. `_frame_for_line` uses interval containment; cues still override.
4. `python -m unittest discover -s tests -v`.

## Definition of done

Issue #12 acceptance green. PR from `work/<job>`. Never push `main`. Never merge.
