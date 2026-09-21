# Feature request: script-first interview renderer

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/1

## Summary

Make a new interview a data problem, not a code fork: pick characters from a shared sprite-sheet layout, supply a YAML script, render audio + video + captions via `python -m open_tts render`.

## Problems addressed

1. **Replication** — remove per-interview `interview.py` / `build_video.py` forks; dialogue lives in YAML.
2. **Caption drift** — WAV/PCM concat with timeline derived from the merged file, not pre-summed MP3 estimates.
3. **Characters** — shared grid for visemes (`a/e/i/o/u/pause`) and cues (`surprise`, `laugh`) on every sheet.

## Out of scope

- Replacing Grok TTS / API credentials (environment only).
- Audiotour JSON (`tts_play.py`) — unchanged separate path.

## Acceptance mapping

| Criterion | Implementation |
|-----------|----------------|
| Character ids + script file | `interviews/*.yaml`, `characters/registry.yaml` |
| Shared sheet layout | `open_tts/sprite.py` |
| Cues + visemes | `CharacterSheet`, `open_tts/video.py` |
| Caption sync >60s | `open_tts/audio.py`, `tests/test_audio_timeline.py` |
| Leo/Eve wording preserved | `interviews/partner-smart-catalogue.yaml` |
