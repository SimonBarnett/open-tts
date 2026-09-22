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

One folder = one show. Layout: `interview.yaml`, `project.json`, `sentences/`, `characters/`, `assets/`, `_work/`.

```powershell
python -m open_tts project new vault-technical --host leo --guest eve --title "Vault technical"
python -m open_tts project list
python -m open_tts project import interviews/partner-smart-catalogue.yaml
python -m open_tts project import interviews/partner-smart-catalogue.yaml --slug my-slug
```

`ensure_project_in_folder(path)` opens an existing `interview.yaml` or seeds that full tree in an empty folder. Host/guest default to last selected left/right (else leo/eve).

## Studio (#9 wizard vs #13 player)

```powershell
python -m open_tts.studio
```

**Models** — last selected character reloads on the next launch (`.studio-prefs.json` `last_model`). **Back** returns to the list to pick another or **New model**. **Generate** and **Keep** write `characters/heroes/<id>.png` per model (leo and eve each keep their own face). Selecting a model loads that file; Interview left/right show the same thumbs. Prefs `last_heroes` is a map by character id.

**Toolbar — Open / Create folder** (top of the window, always visible) opens a folder dialog. Empty folder: create the full project tree (two seed lines, last leo/eve). Existing `interview.yaml`: open that show and switch to Interview. **New…** on the Interview row still makes `projects/<slug>/` from a title.

**Review** needs `timings.json`. Missing mixdown must not crash (duration 0; Play silent until wav/mp4). Keep the player on `QApplication._review_window` so it is not GC'd. **Back to editor** returns to the tabs.

Viseme set preview is a 6x3 grid (vowels, consonants, expressions). Bake cover-fits the hero into each cell. Solo video frames cover-fit the output (not a postage stamp in the centre).

**Edit player** (needs timings):

```powershell
python -m open_tts.studio --edit interviews/partner-smart-catalogue.yaml
python -m open_tts.studio --edit interviews/output/partner-smart-catalogue
python -m open_tts studio --edit interviews/partner-smart-catalogue.yaml
```

Prefs (gitignored `.studio-prefs.json`): `last_model`, `last_host`, `last_guest`, `last_project`. Override path with `OPEN_TTS_PREFS_PATH` in tests.

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
