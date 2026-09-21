---
name: open-tts-drive
description: >
  Drive SimonBarnett/open-tts: render YAML interviews, Qt studio wizard and --edit
  player, project folders, audiotour JSON via tts_play.py, characters registry, and
  headless tests. Use for open-tts, python -m open_tts, studio edit, render interview,
  audiotour.
---

# open-tts drive

Load this skill when `--cwd` is **open-tts** (repo root). Human overview: root `README.md`. This file is the machine playbook for CLI layout and guardrails.

## Dependencies

```powershell
pip install -r requirements.txt
```

- Python 3.10+
- **`ffmpeg`** and **`ffprobe`** on `PATH` for interview video mux (skip in headless CI with `--no-video`).

API access for live TTS reads **`XAI_API_KEY`** from the environment only (see root README). Do not commit keys or `.env`.

## Render interview (YAML script-first)

Primary path for new shows: YAML under `interviews/`, not forked `interviewN/` trees.

```powershell
python -m open_tts render interviews/partner-smart-catalogue.yaml
python -m open_tts render interviews/partner-smart-catalogue.yaml -o interviews/output/custom-dir
python -m open_tts render interviews/partner-smart-catalogue.yaml --skip-tts
python -m open_tts render interviews/partner-smart-catalogue.yaml --no-video
```

| Flag | Effect |
|------|--------|
| `--skip-tts` | Do not call TTS; require existing sentence MP3s |
| `--no-video` | Audio + captions only (no ffmpeg mux) |
| `-o` / `--output` | Output directory (default beside script) |

## Caption drift check

After render, verify SRT/timings vs merged audio:

```powershell
python -m open_tts check path/to/timings.json path/to/full_interview.wav
```

Exit `0` if drift is within budget; `2` if over budget.

## Interview projects

Headless project folders under `projects/`:

```powershell
python -m open_tts project new vault-technical --host leo --guest eve --title "Vault technical"
python -m open_tts project list
python -m open_tts project import interviews/partner-smart-catalogue.yaml
python -m open_tts project import interviews/partner-smart-catalogue.yaml --slug my-slug
```

## Studio (#9 wizard vs #13 player)

**Wizard** (compose / project explorer entry, PySide6 — needs display; skip in CI):

```powershell
python -m open_tts.studio
```

**Edit player** (scrub, edit lines, re-render — PySide6; skip in CI):

```powershell
python -m open_tts.studio --edit interviews/partner-smart-catalogue.yaml
python -m open_tts.studio --edit interviews/output/partner-smart-catalogue
```

**CLI `studio` subcommand** on `open_tts` (project explorer / same edit entry):

```powershell
python -m open_tts studio
python -m open_tts studio --edit interviews/partner-smart-catalogue.yaml
```

Requires prior `render` (timings.json in output dir for `--edit`).

## Audiotour JSON (separate path)

Club Madeira audiotour JSON is **not** the interview YAML renderer. Use:

```powershell
python tts_play.py categories-widget-audiotour.json
```

Root `*-audiotour.json` files are sources; filled copies belong in `processed/` (gitignored).

## Characters

- Registry: `characters/registry.yaml` (character ids, voice ids, sheet paths).
- Sprite layout: `characters/README.md` — 6×N grid, viseme rows, shared `open_tts/sprite.py` conventions.

## Headless CI tests

No live TTS, ffmpeg mux, or on-screen Qt required for default unittest suite:

```powershell
python -m unittest discover -s tests -v
```

## Legacy scripts (avoid for new wording)

| Area | Entry |
|------|--------|
| `interview1/`, `interview2/`, … | Old per-show Python trees |
| `build_video.py`, `merge_interview.py` | Mux / concat helpers |
| `test.py` | One-shot Eve voice smoke test |

Prefer **`interviews/*.yaml`** + `python -m open_tts render` for new interview content.

## Guardrails

- Never commit **`XAI_API_KEY`**, passwords, or live **`.env`**; never put `password=` or key assignments in git.
- As a **build worker**: never push **`main`**; never merge your own PR.
- New interview wording → **`interviews/*.yaml`**, not new forks under legacy **`interviewN/`**.
- Qt studio and ffmpeg video steps are **optional in headless CI** — use `--no-video`, `--skip-tts`, and unittest only when validating docs/skills changes.

## Related docs

- `docs/build-and-test-plan-script-first-interview-renderer.md` — script-first renderer
- Feature / build plans under `docs/` for parked work
