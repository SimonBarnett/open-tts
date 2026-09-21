# Build and test plan: expand shared expression set

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/10
FR: `docs/feature-request-expand-expression-set-2026-09-21.md`

## Goals / non-goals

Fill row-1 expression columns. Do not build the Qt wizard. Do not add viseme consonants (#11). Tests without ffmpeg or display.

## Phases

1. Lock `EXPRESSION_COL` ids and columns in `open_tts/sprite.py`.
2. Placeholder generator paints empty cells; Leo/Eve share indices.
3. `open_tts/video.py` honors new cues; unknown cues fail closed.
4. Cue helper tests on partner thank-you / enthusiasm lines.
5. `python -m unittest discover -s tests -v`.

## Definition of done

Issue #10 acceptance green. PR from `work/<job>`. Never push `main`. Never merge.
