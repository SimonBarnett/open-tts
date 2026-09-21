# Build and test plan: agent skills folder

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/141  
FR: `docs/feature-request-agent-skills-folder-2026-09-21.md`

## Goals / non-goals

**Goals**

- Add repo-local `.grok/skills/open-tts-drive/SKILL.md` so fleet agents (`grok.exe --rules`, Cursor git workers) can operate open-tts without re-deriving CLI layout.
- Add a short **Agents** section to root `README.md` pointing at `.grok/skills/`.

**Non-goals**

- No new render/studio features, no API wrappers, no `.cursor/skills` mirror unless Simon asks.
- No live TTS, ffmpeg mux, or on-screen Qt in CI.
- No secrets in git or in skill text (`password=` / `XAI_API_KEY=` assignments).

## Phase order

### Phase 0 — Read tree (no commits)

1. Read `README.md`, `open_tts/__main__.py`, `open_tts/studio/__main__.py`, `characters/README.md`.
2. Confirm unittest entry: `python -m unittest discover -s tests -v`.

**Exit:** You can list every public entry in the table below from the repo, not from memory.

### Phase 1 — Primary skill

Create `.grok/skills/open-tts-drive/SKILL.md` with YAML frontmatter:

```yaml
---
name: open-tts-drive
description: >
  Drive SimonBarnett/open-tts: render YAML interviews, Qt studio wizard and --edit
  player, project folders, audiotour JSON via tts_play.py, characters registry, and
  headless tests. Use for open-tts, python -m open_tts, studio edit, render interview.
---
```

Body must include these **locked surfaces** (copy-paste commands):

| Surface | Command |
|---|---|
| Render | `python -m open_tts render <yaml>`; flags `--skip-tts`, `--no-video` |
| Drift check | `python -m open_tts check <timings.json> <audio>` |
| Projects | `python -m open_tts project new/list/import …` (match actual subcommands in `__main__.py`) |
| Studio wizard (#9) | `python -m open_tts.studio` (no args) |
| Studio player (#13) | `python -m open_tts.studio --edit <yaml-or-output-dir>` |
| Explorer | `python -m open_tts studio` subcommand if present |
| Audiotour | `python tts_play.py <*-audiotour.json>` — **not** the interview renderer |
| Characters | `characters/registry.yaml`, `characters/README.md` sheet layout |
| CI tests | `python -m unittest discover -s tests -v` |
| Deps | `pip install -r requirements.txt`; ffmpeg on PATH for video |

**Guardrails section (required):**

- Keys from environment only; never commit `.env` or key assignments.
- Never push `main` or merge your own PR as a worker.
- New interview wording → `interviews/*.yaml`, not legacy `interviewN/` forks.
- GUI / ffmpeg steps optional in headless CI.

Keep the skill under ~250 lines; split into a second skill only if necessary.

**Exit:** File exists; `name` and `description` match frontmatter; triggers in description include `open-tts` and `python -m open_tts`.

### Phase 2 — README Agents pointer

Add **Agents** section to `README.md` (after Requirements or before Scripts):

- One paragraph: product skills live under `.grok/skills/`; start with `open-tts-drive`.
- Link to `.grok/skills/open-tts-drive/SKILL.md`.

**Exit:** README renders sensible markdown links on GitHub.

### Phase 3 — Verify

```powershell
python -m unittest discover -s tests -v
```

No new test files required unless you add a tiny test that `.grok/skills/open-tts-drive/SKILL.md` exists and contains `name: open-tts-drive` (optional; prefer zero code if unittest already green).

**Exit:** unittest green; `git status` clean except intended files.

## Definition of done

- Issue #141 acceptance boxes in the FR doc are all checked in the PR description.
- PR from `work/<job-id>` (or `work/<uuid>` per fleet convention).
- Never push `main`. Never merge. Do not write **ready for human UAT**.

## Kickoff goal (for Start-BobBuild)

Implement GitHub issue #141: add `.grok/skills/open-tts-drive/SKILL.md` and README **Agents** section per `docs/feature-request-agent-skills-folder-2026-09-21.md` and `docs/build-and-test-plan-agent-skills-folder-2026-09-21.md`. Open a PR. Never push main. Never merge.
