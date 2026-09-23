---
name: open-tts-drive
description: >
  Drive SimonBarnett/open-tts: render YAML interviews, Qt studio wizard and --edit
  player, project folders, audiotour JSON via tts_play.py, characters registry, and
  headless tests. Use for open-tts, python -m open_tts, studio edit, render interview,
  audiotour, viseme, framing, voices.
---

# open-tts drive

Load this skill when `--cwd` is **open-tts** (repo root). Human overview: root `README.md`. This file is the machine playbook for CLI, studio, cast, voices, and framing.

Local checkout on this box: `D:\ai\open-tts`. Remote: `https://github.com/SimonBarnett/open-tts.git`. Harvest playbooks back here (skill `harvest-open-tts`), not only into `~/.grok/skills`.

## Dependencies

```powershell
pip install -r requirements.txt
```

- Python 3.10+
- **`ffmpeg`** and **`ffprobe`** on `PATH` for interview video mux (skip in headless CI with `--no-video`).

API access for live TTS and the voice list reads **`XAI_API_KEY`** from the environment or gitignored `.env` only (see root README). Do not commit keys or `.env`. Do not print the key.

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

Studio Interview **Render** currently shells `python -m open_tts render ... --no-video`. Full picture needs a CLI render without `--no-video` (ffmpeg on PATH).

## Caption drift check

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

## Studio

```powershell
python -m open_tts.studio
```

On Windows, launch via Explorer (not a raw redirected pipe) so Qt can see an audio device:

```powershell
$bat = "$env:TEMP\open-tts-studio.bat"
@"
@echo off
cd /d D:\ai\open-tts
python -m open_tts.studio
"@ | Set-Content -Path $bat -Encoding ascii
explorer.exe $bat
```

Kill a previous `python -m open_tts.studio` before relaunch so Simon is not looking at a stale window.

### Models tab

- Last selected character reloads (`.studio-prefs.json` `last_model`). **People** returns to the list. **New person** starts another.
- **Voice** is a dropdown. Live list: `GET https://api.x.ai/v1/tts/voices` (and `GET /v1/custom-voices` when the key works). Offline fallback: `BUILTIN_TTS_VOICES` in `open_tts/tts.py` (looked up 2026-09-22, 28 built-ins). Display is `Name (voice_id)`; registry stores the id. Default API voice is `eve`.
- Built-in ids (do not invent others): altair, ara, atlas, aurora, carina, castor, celeste, cosmo, eve, helios, helix, iris, kepler, leo, liora, lumen, luna, lux, naksh, orion, perseus, rex, rigel, sal, sirius, ursa, zagan, zenith.
- Still-first: **New face** / **Again** draws a cartoon still (transparent plate). **Move / size** the model on that still (drag + Size slider), then **Approve face** locks `characters/heroes/<id>.png` plus `.placement.json`. Do not generate video until approved.
- Dual characters are **two halves of the screen** (Left | Right). There is no separate "split talking" mode — Screen `split` means half + half.
- If no approved hero exists, faces come from the original grids: `characters/visemes/leo.png`, `characters/visemes/eve.png`. `resolve_hero` prefers heroes/, then those defaults.
- No mouth-sheet grid, Bake, hero still label, or viseme combo. Each phoneme / emote / full / split is its own **VIDEO** clip under `characters/loops/` (see `open_tts/loops.py` `clip_slots`).
- Clip list: left-click previews in **Full / Left / Right** only (stage aspect 736:400). Right-click: **Update this clip** (one slot, I2V from the placed approved face), **Play clip**, **Stop**. Do not autoplay on enter.
- Stage-aspect stills (loop frames) fill Full as-is; Left/Right are the left/right halves of that plate. Portrait stills are composed onto the stage after Placement. See Framing below.

### Interview tab

- Header **Left model** / **Right model** are the default stage pair.
- Toolbar **Create** / **Open** / **Save** (separate buttons): empty folder seeds a full project; existing `interview.yaml` opens that show.
- **New...** still makes `projects/<slug>/` from a title (last leo/eve cast).
- Table columns: Speaker, Text, **Screen** (auto/full/split), **Left**, **Right**, Animation, Notes.
- Screen `auto` uses `layout.dual_start_turns` / `dual_end_turns`. `split: true|false` on a line overrides.
- Left/Right `auto` inherits the previous pair. Set an id to swap a character in from that line on. **Swap sides here** flips the current pair. YAML: `left:`, `right:`, or `swap: true`.
- Animation includes `attentive` (alias of `listen`). In split, the silent character plays attentive, not a frozen pause.

### Review / edit player

Review needs `timings.json`. Missing mixdown must not crash (`media_duration` 0; Play silent until wav/mp4). Keep the player on `QApplication._review_window` so it is not GC'd. **Back to editor** returns to the tabs.

```powershell
python -m open_tts.studio --edit interviews/partner-smart-catalogue.yaml
python -m open_tts.studio --edit interviews/output/partner-smart-catalogue
```

Prefs (gitignored `.studio-prefs.json`): `last_model`, `last_host`, `last_guest`, `last_project`, `last_heroes`. Override path with `OPEN_TTS_PREFS_PATH` in tests.

## Framing (original artwork)

Look at the original viseme cells before inventing crops:

- **Leo** (`characters/visemes/leo.png`): tight full-screen **monologue** close-up, studio backdrop.
- **Eve** (`characters/visemes/eve.png`): wider **half-screen interview** shot (person on one side, desk/set around them).

`open_tts/framing.py` derives both from each cell: `frame_monologue` (solo / full) and `frame_half` (left/right). Video compose uses those, not a naive cover-fit of the same square into both layouts. Legacy talking-head loops on the NAS (`full_*_talking.mp4`, `dual_*_talking_*_idle.mp4`) are the same idea.

**Placement:** before Approve face / clip gen, studio pan+zoom (`Placement`, `apply_placement`) sizes the model in the initial still. Saved as `characters/heroes/<id>.placement.json`. Dual = left half + right half of one plate — not a separate talking mode.

Sheets are 6 x 9 cells of 128px (`768x1152`). `characters/*.png` and most of `characters/visemes/` are gitignored; keep `leo.png` / `eve.png` via the gitignore exceptions.

## Characters

- Registry: `characters/registry.yaml` (ids, `voice_id`, sheet, optional `viseme_set`, `hero`).
- Sprite contract: `characters/README.md` and `open_tts/sprite.py` (6 columns; `attentive` = `listen`).
- Resolve order for a face: `characters/heroes/<id>.png`, registry `hero`, prefs extra, then default portrait cut from the original viseme grid.

## Audiotour JSON (separate path)

Club Madeira audiotour JSON is **not** the interview YAML renderer:

```powershell
python tts_play.py categories-widget-audiotour.json
```

Root `*-audiotour.json` files are sources; filled copies belong in `processed/` (gitignored).

## Headless CI tests

```powershell
python -m unittest discover -s tests -v
```

No live TTS, ffmpeg mux, or on-screen Qt required for the default suite. `QT_QPA_PLATFORM=offscreen` is set in studio tests. Voice-list tests must not require the network (documented catalog). Do not hit TTS in tests.

## Legacy scripts (avoid for new wording)

| Area | Entry |
|------|--------|
| `interview1/`, `interview2/`, ... | Old per-show Python trees |
| `build_video.py`, `merge_interview.py` | Mux / concat helpers; expect NAS `full_*.mp4` / `dual_*.mp4` |
| `test.py` | One-shot Eve voice smoke test |

Prefer **`interviews/*.yaml`** + `python -m open_tts render` for new interview content.

## Guardrails

- Never commit **`XAI_API_KEY`**, passwords, or live **`.env`**; never put `password=` or key assignments in git.
- As a **build worker**: never push **`main`**; never merge your own PR. (Human / harvest on this box may push when Simon asks.)
- New interview wording -> **`interviews/*.yaml`**, not new forks under legacy `interviewN/`.
- Qt studio and ffmpeg video steps are **optional in headless CI** -- use `--no-video`, `--skip-tts`, and unittest only when validating docs/skills changes.
- Voice ids: look up `GET /v1/tts/voices` or `open_tts/tts.py`; do not invent names.

## Related docs

- `docs/build-and-test-plan-script-first-interview-renderer.md` -- script-first renderer
- `docs/skill-harvest-log.md` -- harvested playbooks
- Feature / build plans under `docs/` for parked work
