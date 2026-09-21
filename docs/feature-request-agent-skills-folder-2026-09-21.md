# Feature request: agent skills folder (`.grok/skills`)

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/141

## Summary

Add a **repo-local skills tree** so Grok Bot, `grok.exe`, and Cursor agents can drive **open-tts** without re-deriving CLI layout, paths, and guardrails from scattered README sections.

Fleet git workers already copy `agentic_build` skills onto `--rules`; this FR adds **product skills in this repository** that any agent should load when `--cwd` is `open-tts`.

## Gap vs current tree

- `README.md` is human-oriented; no machine-readable playbooks.
- No `.grok/skills/` (or equivalent) under the repo root.
- Agents must guess when to use `python -m open_tts render`, `python -m open_tts.studio` (wizard vs `--edit`), `python -m open_tts project …`, vs legacy `tts_play.py` / `interviewN/`.

## Locked layout

```
.grok/skills/
  open-tts-drive/     SKILL.md   # primary: render, studio, projects, tests
  (optional split only if drive skill exceeds ~200 lines)
```

Each skill is a directory with `SKILL.md` and YAML frontmatter (`name`, `description`) matching the **agentic_build** convention so `Install-BobFleet` / `--rules` discovery works unchanged.

## Locked content (open-tts-drive)

The primary skill must document, with copy-paste commands:

| Surface | Entry |
|---|---|
| Render interview | `python -m open_tts render <yaml>` (`--skip-tts`, `--no-video`) |
| Caption drift check | `python -m open_tts check …` |
| Interview projects | `python -m open_tts project new/list/import …` |
| Studio wizard (#9) | `python -m open_tts.studio` (no args) |
| Studio player (#13) | `python -m open_tts.studio --edit <yaml-or-output-dir>` |
| Project explorer | `python -m open_tts studio` (subcommand on `open_tts` CLI) |
| Audiotour JSON | `python tts_play.py <*-audiotour.json>` — **separate path**; do not mux into interview renderer |
| Characters | `characters/registry.yaml`, sheet layout pointers to `characters/README.md` |
| Headless CI | `python -m unittest discover -s tests -v` |
| Dependencies | `requirements.txt`, `ffmpeg` on PATH for video |

**Guardrails** (must appear in the skill):

- Never commit `XAI_API_KEY`, passwords, or live `.env`.
- Never push `main` or merge PRs when acting as a build worker.
- Prefer YAML scripts under `interviews/` over editing legacy `interviewN/` trees for new wording.
- Qt GUI steps may be skipped in CI; say so explicitly.

**UNKNOWN (worker may park follow-up FR, not guess):**

- Whether to also ship `.cursor/skills/` mirrors for Cursor-only hosts (default: **no** unless Simon asks; `.grok/skills` is the canonical path for this fleet).

## Out of scope

- New render features, new studio UI, or viseme/G2P changes.
- Wrapping every script in new Python APIs; skills are **documentation + triggers**, not a second CLI.
- Publishing skills to a global registry outside this repo.

## Acceptance

- [ ] `.grok/skills/open-tts-drive/SKILL.md` exists with valid frontmatter and the locked surfaces above.
- [ ] Root `README.md` has a short **Agents** section pointing to `.grok/skills/` and naming `open-tts-drive`.
- [ ] Skill `description` mentions triggers such as: open-tts, render interview, studio edit, audiotour, `python -m open_tts`.
- [ ] No secrets, no `password=` / `XAI_API_KEY=` assignments in committed files.
- [ ] `python -m unittest discover -s tests -v` still passes on the PR branch (skills-only change must not break tests).
- [ ] Open a PR; never push `main`. Never merge. Do not write **ready for human UAT**.

## Delivery note

Park only until `bob-build-dispatch` / `bob job` is asked. A separate `docs/build-and-test-plan-agent-skills-folder-2026-09-21.md` is written at dispatch time.
