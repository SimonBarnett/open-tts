---
name: harvest-open-tts
description: >
  Harvest open-tts playbooks into this repo. Use when you learn a studio, render,
  voice, framing, or project procedure, or the user says harvest skills, harvest
  open-tts, promote a playbook, or /harvest-open-tts.
---

# Harvest open-tts

CAST IRON: if you learn something new while driving this tool, write it into
**this repo**. Do not leave the playbook only in `~/.grok/skills`.

Owner skill for day-to-day use: `.grok/skills/open-tts-drive/SKILL.md`.
Copy that file to `~/.grok/skills/open-tts-drive/SKILL.md` after edits.

## When

- New studio UI (Models, Interview columns, Review).
- Voice catalog / `GET /v1/tts/voices` changes.
- Framing, viseme grids, left/right/full compose.
- Project folder / render flags / Windows launch quirks.
- Simon says harvest skills.

## Write

1. Edit `.grok/skills/open-tts-drive/SKILL.md` (ASCII). Triggers stay in the
   frontmatter `description`.
2. Append a short dated section to `docs/skill-harvest-log.md`.
3. `Copy-Item` the drive skill to `~/.grok/skills/open-tts-drive/SKILL.md`.
4. Commit those files. Push `origin/main` only when Simon asked (this harvest
   counts) or you are not a PR worker.

## Do not

- Commit `.env`, keys, `.studio-prefs.json`, `projects/**/_work/`, or generated
  audio/video.
- Invent voice ids or sheet layouts.
- Duplicate this playbook into `agentic_build`; point at open-tts-drive.
