# Feature request: interview project folders + explorer

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/14

## Summary

One folder = one interview. All assets for that video live there. A Qt folder explorer lists projects so an old show can be reopened and edited (#13 runtime) without hunting `interview3/`, NAS loops, and `interviews/output/<slug>/`.

## Locked layout

```
projects/<slug>/
  interview.yaml
  project.json
  characters/            # optional overrides
  sentences/
  timings.json
  interview.srt
  full_interview.wav
  full_interview.mp3
  interview.mp4
  _work/                 # gitignored scratch
```

Render reads and writes inside that folder. Global `characters/registry.yaml` remains the library. Legacy `interviewN/` stays until #3 YAML exists; do not auto-delete.

CLI (headless, no Qt):

```
python -m open_tts project new vault-technical --host leo --guest eve
python -m open_tts project list
python -m open_tts render projects/vault-technical/interview.yaml
python -m open_tts studio --edit projects/vault-technical
```

## Out of scope

Character image LLM (#9 flow A). Extra viseme rows (#11). Implementing leftover dialogue dumps (#3) beyond import-if-YAML-exists. Moving NAS talking-head loops.

## Acceptance

- [ ] New interview creates a project folder with `interview.yaml` + `project.json`.
- [ ] Render input/output paths are that folder.
- [ ] Re-opening the folder finds YAML + timings + existing sentence MP3s; `--skip-tts` reuse still works.
- [ ] Studio explorer lists projects and Open launches the #13 editor on that folder.
- [ ] `python -m open_tts project list` works headless.
- [ ] Partner YAML can be imported into `projects/partner-smart-catalogue/` without changing wording.
- [ ] No new per-show `build_video.py`. `tts_play.py` / audiotour JSON unchanged.
