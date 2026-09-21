# open-tts

xAI Grok TTS scripts for Club Madeira audiotours and interview videos.

Source came from `\\walrus\nas\PriorityMobile\open-tts`. Generated audio, video, and processed JSON with embedded base64 are **not** in this repo.

## Secrets

Do not put API keys in source. Scripts read **`XAI_API_KEY`** from the environment.

```powershell
$env:XAI_API_KEY = 'your-key'
```

Or copy `.env.example` to `.env` and export the variable yourself. `.env` is gitignored.

## Requirements

- Python 3.10+
- `pip install -r requirements.txt`
- `ffmpeg` and `ffprobe` on `PATH` (interview merge / video mux)

## Script-first interviews (`open_tts`)

New shows are YAML + character ids (no forked `interviewN.py`):

```powershell
python -m open_tts render interviews/partner-smart-catalogue.yaml
```

See `docs/build-and-test-plan-script-first-interview-renderer.md`. Audiotour JSON (`tts_play.py`) stays on its own path.

## Scripts

| Script | Purpose |
|---|---|
| `python -m open_tts render` | YAML script → audio, SRT, timings, sprite-sheet video |
| `tts_play.py` | Fill audiotour JSON with Grok TTS (`python tts_play.py categories-widget-audiotour.json`) |
| `test.py` | One-shot Eve voice check against `https://api.x.ai/v1/tts` |
| `interview1/interview.py` | Sentence-level interview audio → `interview_audio2/` |
| `interview2/interview1.py` | Technical vault interview → `interview_audio1/` |
| `interview_audio3/interview.py` | White-label partner interview → `interview3/` |
| `interview_audio4/interview.py` | Marketing-door interview → `interview4/` |
| `build_video.py` / `interview3/build_video.py` / `interview4/build_video.py` | Mux talking-head loops + SRT + full audio |
| `merge_interview.py` | Concat MP3 turns |
| `listaudio.py` / `lengths.py` | Duration helpers |

Talking-head loops (`full_*.mp4`, `dual_*.mp4`) and generated `*.mp3` stay on the NAS share; copy them next to the scripts when you need to render.

## Audiotour JSON

Root `*-audiotour.json` files are the **source** tours (`base64` is a placeholder). Regenerated copies with real audio belong in `processed/` (gitignored).
