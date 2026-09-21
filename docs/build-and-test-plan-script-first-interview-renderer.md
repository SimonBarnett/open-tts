# Build and test plan: script-first interview renderer

Issue: https://github.com/SimonBarnett/open-tts/issues/1

## Build

1. `python -m venv .venv` and activate (optional).
2. `pip install -r requirements.txt`
3. Ensure `ffmpeg` and `ffprobe` are on `PATH`.

## Automated tests

```bash
python -m unittest discover -s tests -v
```

Covers:

- SRT timestamp formatting (no `,1000` ms rollover).
- Shared sprite indices for Leo/Eve placeholder sheets.
- >60s synthetic interview merge drift ≤30 ms.

## Manual render (audio + captions)

Requires `XAI_API_KEY` in the environment for TTS (never committed).

```bash
python -m open_tts render interviews/partner-smart-catalogue.yaml --no-video
```

Re-use existing sentence MP3s:

```bash
# Copy interview_audio2/leo/*.mp3 and eve/*.mp3 into
# interviews/output/partner-smart-catalogue/sentences/ with matching names, then:
python -m open_tts render interviews/partner-smart-catalogue.yaml --skip-tts --no-video
python -m open_tts check interviews/output/partner-smart-catalogue/timings.json interviews/output/partner-smart-catalogue/full_interview.wav
```

## Full video (sprite sheets)

```bash
python -m open_tts render interviews/partner-smart-catalogue.yaml --skip-tts
```

Placeholder `characters/leo.png` / `eve.png` are auto-created if missing.

## Regression guard

- Do not modify `tts_play.py` audiotour flow.
- Drift budget: `MAX_SRT_AUDIO_DRIFT_SEC = 0.030` in `open_tts/audio.py`.
